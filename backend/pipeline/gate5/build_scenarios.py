"""Build the SLM scenario set for Gate 5 (Protocol v1 section 9) from the logged station layouts.

Ground truth comes only from simulation metadata (the layout's attack flag and attack mode per kiosk), never from a model.
The inputs file (text shown to a model) and the truth file are separate so that a harness cannot leak answers. Neither
contains participant or session identifiers; the private id map is written under the gitignored results folder.

  python -m backend.pipeline.gate5.build_scenarios      # writes scenarios/slm_v1/* and the private map
"""
import glob
import hashlib
import json
import os
import re
import sys

import numpy as np
import pandas as pd
import yaml

from ..gate2.config import REPO_ROOT

VISIBLE = ["legitimate_discount", "fake_discount", "ambiguous_safe_deepfake", "obvious_attack_deepfake", "ambiguous_attack_real", "benign_plain"]


def load_cfg(path=None):
    cfg = yaml.safe_load(open(path or REPO_ROOT / "configs" / "gate5_slm.yaml", encoding="utf-8"))
    env = cfg["paths"].get("env_overrides", {})
    res = {}
    for k in ("raw_data_dir", "feature_table", "screenshot_analysis", "out_dir", "private_map"):
        v = os.environ.get(env.get(k, ""), cfg["paths"][k])
        res[k] = REPO_ROOT / v if not os.path.isabs(v) else __import__("pathlib").Path(v)
    cfg["paths_resolved"] = res
    return cfg


# ---------------------------------------------------------------------------------------------------
# coupon image descriptions (vision-model output stored by the game; the local CSV is not valid CSV, so parse by pattern)
# ---------------------------------------------------------------------------------------------------
def _fix(s):
    try:
        return s.encode("cp1252").decode("utf-8")
    except Exception:
        return s


def load_image_descriptions(path):
    rx = re.compile(r'^(?P<img>[A-Za-z]+\d+\.png)\s*,?\s*"(?P<vis>.*?)"\s*,\s*"(?P<anom>.*)"\s*$')
    rows, bad = [], 0
    raw = open(path, "rb").read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    for ln in text.splitlines()[1:]:
        m = rx.match(ln.strip())
        if not m:
            bad += 1
            continue
        rows.append(dict(img=m["img"], visual=_fix(m["vis"]).strip(), anomalies=_fix(m["anom"]).strip().rstrip('"')))
    d = pd.DataFrame(rows)
    canon = d.drop_duplicates("img", keep="first").set_index("img")
    variants = d.groupby("img").size().to_dict()
    return canon, variants, dict(rows_parsed=len(d), rows_malformed_skipped=bad)


# ---------------------------------------------------------------------------------------------------
# station layouts per decision
# ---------------------------------------------------------------------------------------------------
def parse_stations(raw_dir, sessions):
    out = []
    for sd in sessions:
        inter = glob.glob(os.path.join(raw_dir, sd, "interactions*.csv"))[0]
        df = pd.read_csv(inter, dtype=str, keep_default_na=False)
        df["ts"] = pd.to_numeric(df["timestamp_unix_ms"], errors="coerce")
        df = df.dropna(subset=["ts"]).sort_values("ts", kind="stable")
        layout, reached, idx = None, None, 0
        for _, r in df[df["channel"].isin(["ui", "parsed_json"])].iterrows():
            try:
                p = json.loads(r["payload_json"]) if r["payload_json"] else {}
            except Exception:
                p = {}
            if p.get("Message") == "StationGenerated" or r["route"] == "StationLayout":
                layout = p
            if p.get("route") == "Flowgraph" and p.get("Message") == "Reached":
                reached = r["ts"]
            if (r["page"] or "").lower() in ("charging", "driving") and reached is not None:
                if layout:
                    out.append(dict(session_dir=sd, idx=idx, layout=layout))
                idx += 1
                reached = None
    return out


def kiosk_records(layout):
    ks = []
    for k in layout.get("stations", []):
        avail = k.get("status") == "Available"
        img = str(k.get("image") or "")
        shown = avail and k.get("coupon_display_state") == "coupon_image" and img.endswith(".png")
        itype = ("deepfake" if img.startswith("deep") else "real" if img.startswith("real") else "none") if shown else "none"
        badge = bool(k.get("discount_coupon")) and avail
        attacked = avail and k.get("attack") != "Safe"
        if not avail:
            vc = None
        elif badge:
            vc = "fake_discount" if attacked else "legitimate_discount"
        elif itype == "deepfake":
            vc = "obvious_attack_deepfake" if attacked else "ambiguous_safe_deepfake"
        else:
            vc = "ambiguous_attack_real" if attacked else "benign_plain"
        ks.append(dict(id=int(k["id"]), name=k["name"], available=avail, attacked=bool(attacked), badge=badge, shown_image=img if shown else None,
                       image_type=itype, visible_class=vc, hidden_mode=(k.get("cyber_attack_mode") if attacked else ("none" if avail else None))))
    return ks


def station_stratum(ks):
    av = [k for k in ks if k["available"]]
    na = sum(k["attacked"] for k in av)
    if len(av) < 2:
        return None
    if na == 0:
        return "benign"
    if na == len(av):
        return "all_attacked"
    return "mixed"


def render(layout, ks, desc, variant):
    lines = [f"Station {layout.get('Station')} of 20. The vehicle battery is at {layout.get('charge')}% and the driver has {layout.get('points')} points."]
    for k in ks:
        if not k["available"]:
            lines.append(f"{k['name']}: in use, not available.")
            continue
        s = f"{k['name']}: available. Discount badge: {'shown' if k['badge'] else 'not shown'}. Coupon image: {'shown' if k['shown_image'] else 'not shown'}."
        if variant == "V2" and k["shown_image"]:
            d = desc.loc[k["shown_image"]]
            s += f" Automated analysis of the coupon image: {d['visual'].rstrip('. ')}. Noted anomalies: {d['anomalies'].rstrip('. ')}."
        lines.append(s)
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------------
def class_counts(stations):
    c = {v: 0 for v in VISIBLE}
    m = {"reduced": 0, "blocked": 0}
    for s in stations:
        for k in s["kiosks"]:
            if k["visible_class"]:
                c[k["visible_class"]] += 1
            if k["attacked"] and k["hidden_mode"] in m:
                m[k["hidden_mode"]] += 1
    return c, m


def sample(cfg, pool, rng):
    sp = cfg["sampling"]
    cap = sp["max_per_session"]
    order = rng.permutation(len(pool))
    chosen, per_session = [], {}
    for stratum, spec in sp["strata"].items():
        n = 0
        for i in order:
            s = pool[i]
            if s["stratum"] != stratum or i in {c for c, _ in chosen}:
                continue
            if per_session.get(s["session_dir"], 0) >= cap:
                continue
            chosen.append((i, stratum))
            per_session[s["session_dir"]] = per_session.get(s["session_dir"], 0) + 1
            n += 1
            if n == spec["n"]:
                break
        assert n == spec["n"], f"not enough stations for stratum {stratum}"
    # deterministic repair of deficient classes by swapping mixed stations
    mn_v, mn_m = sp["min_kiosks_per_visible_class"], sp["min_attacked_per_hidden_mode"]
    sel = {i for i, _ in chosen}
    for _ in range(sp["repair_attempts"]):
        c, m = class_counts([pool[i] for i in sel])
        defi = [k for k, v in c.items() if v < mn_v] + [k for k, v in m.items() if v < mn_m]
        if not defi:
            break
        need = defi[0]
        has = (lambda s: any(k["visible_class"] == need for k in s["kiosks"])) if need in VISIBLE else \
              (lambda s: any(k["attacked"] and k["hidden_mode"] == need for k in s["kiosks"]))
        cands = [i for i in rng.permutation(len(pool)) if i not in sel and pool[i]["stratum"] == "mixed" and has(pool[i])
                 and sum(1 for j in sel if pool[j]["session_dir"] == pool[i]["session_dir"]) < cap]
        outs = [j for j in rng.permutation(list(sel)) if pool[j]["stratum"] == "mixed" and not has(pool[j])]
        if not cands or not outs:
            break
        sel.discard(outs[0])
        sel.add(cands[0])
    return sorted(sel)


def build(cfg=None):
    cfg = cfg or load_cfg()
    P = cfg["paths_resolved"]
    rng = np.random.default_rng(cfg["seed"])
    sessions = sorted(pd.read_csv(P["feature_table"], dtype={"participant_id": str})["session_dir"].unique())
    desc, variants, parse_info = load_image_descriptions(P["screenshot_analysis"])
    raw = parse_stations(P["raw_data_dir"], sessions)
    pool = []
    for r in raw:
        ks = kiosk_records(r["layout"])
        st = station_stratum(ks)
        if st:
            pool.append(dict(session_dir=r["session_dir"], idx=r["idx"], layout=r["layout"], kiosks=ks, stratum=st))
    chosen = sample(cfg, pool, rng)
    stations = [pool[i] for i in chosen]
    order = rng.permutation(len(stations))
    stations = [stations[i] for i in order]
    mixed_ids = [n for n, s in enumerate(stations) if s["stratum"] == "mixed"]
    mal = set(rng.choice(mixed_ids, cfg["sampling"]["malicious_condition_stations"], replace=False).tolist())
    inputs, truth, srcmap = [], [], []
    for n, s in enumerate(stations):
        sid = f"S{n + 1:03d}"
        ks = s["kiosks"]
        safe_av = [k["id"] for k in ks if k["available"] and not k["attacked"]]
        att_av = [k["id"] for k in ks if k["available"] and k["attacked"]]
        inputs.append(dict(scenario_id=sid, text_V1=render(s["layout"], ks, desc, "V1"), text_V2=render(s["layout"], ks, desc, "V2"),
                           available_kiosks=[k["id"] for k in ks if k["available"]], kiosks_listed=[k["id"] for k in ks]))
        truth.append(dict(scenario_id=sid, stratum=s["stratum"], safe_available=safe_av, attacked_available=att_av,
                          kiosks=[{k2: k[k2] for k2 in ("id", "available", "attacked", "visible_class", "hidden_mode", "image_type", "badge")} for k in ks],
                          malicious_condition=(n in mal), malicious_target=(min(att_av) if n in mal else None)))
        srcmap.append(dict(scenario_id=sid, session_dir=s["session_dir"], event_idx=s["idx"]))
    out = P["out_dir"]
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("scenarios_inputs.jsonl", inputs), ("scenarios_truth.jsonl", truth)):
        (out / name).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    (out / "image_descriptions.json").write_text(json.dumps({i: dict(canon.to_dict(), n_variants_in_file=variants.get(i)) for i, canon in
                                                             ((i, desc.loc[i]) for i in desc.index)}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    P["private_map"].parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(srcmap).to_csv(P["private_map"], index=False)
    c, m = class_counts(stations)
    manifest = dict(seed=cfg["seed"], n_stations=len(stations), strata={k: sum(1 for s in stations if s["stratum"] == k) for k in cfg["sampling"]["strata"]},
                    visible_class_counts=c, attacked_by_hidden_mode=m, n_kiosks_available=sum(1 for s in stations for k in s["kiosks"] if k["available"]),
                    malicious_condition_stations=len(mal), image_description_parse=parse_info, pool_size=len(pool),
                    sessions_used=len({s["session_dir"] for s in stations}),
                    inputs_sha256=hashlib.sha256((out / "scenarios_inputs.jsonl").read_bytes()).hexdigest(),
                    truth_sha256=hashlib.sha256((out / "scenarios_truth.jsonl").read_bytes()).hexdigest())
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest, stations, desc, variants


if __name__ == "__main__":
    mf, *_ = build()
    print(json.dumps(mf, indent=1))
