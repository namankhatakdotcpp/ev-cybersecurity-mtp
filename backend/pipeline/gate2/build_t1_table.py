"""Build the Gate 2 analysis table for Protocol v1 (target T1) from the raw interaction logs and the committed
feature table. Paths come from the config (repo-relative, env-overridable); nothing is hardcoded.

One row per station visit (all 1,123 visits keep a row; flags mark eligibility):
  - layout fields (attacked / available kiosks, incident mode, chosen kiosk's attack status) are parsed from the
    logged `StationGenerated` event, i.e. information available before the decision (Protocol section 1);
  - behaviour and gaze features come from the committed `feature_table.csv` (joined by session and event order,
    with an integrity check that decision, kiosk and attack label agree between the two sources).
"""
import glob
import json
import os
import re

import numpy as np
import pandas as pd

from .config import load_config


def _parse_session_events(inter_path):
    """Reached -> first charging/driving event, with the layout logged before it (same event rule as the pipeline)."""
    df = pd.read_csv(inter_path, dtype=str, keep_default_na=False)
    df["ts"] = pd.to_numeric(df["timestamp_unix_ms"], errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values("ts", kind="stable")
    out = []
    layout, reached, trial = None, None, None
    for _, r in df[df["channel"].isin(["ui", "parsed_json"])].iterrows():
        try:
            p = json.loads(r["payload_json"]) if r["payload_json"] else {}
        except Exception:
            p = {}
        if p.get("Message") == "StationGenerated" or r["route"] == "StationLayout":
            layout = p
        if p.get("route") == "Flowgraph" and p.get("Message") == "Reached":
            reached, trial = r["ts"], p.get("Station")
        page = (r["page"] or "").lower()
        if page in ("charging", "driving") and reached is not None:
            st = (layout or {}).get("stations", [])
            avail = [k for k in st if k.get("status") == "Available"]
            chosen = None
            if page == "charging" and p.get("kiosk_used") not in (None, ""):
                chosen = next((k for k in st if str(k.get("id")) == str(p.get("kiosk_used"))), None)
            out.append(dict(
                t_start_ms=reached, t_end_ms=r["ts"], end_page=page, trial_raw=trial,
                kiosk_used=p.get("kiosk_used") if page == "charging" else None,
                logged_attack=p.get("kiosk_attack") if page == "charging" else None,
                n_available=len(avail), n_attacked=int(sum(k.get("attack") != "Safe" for k in avail)),
                layout_incident_mode=(layout or {}).get("incident_mode"),
                chosen_attacked=(None if chosen is None else int(chosen.get("attack") != "Safe"))))
            reached = None
    return out


def _period(date_str, periods):
    for name, (lo, hi) in periods.items():
        if lo <= date_str <= hi:
            return name
    return "other"


def build_table(cfg=None):
    cfg = cfg or load_config()
    raw_dir = cfg["paths_resolved"]["raw_data_dir"]
    ft = pd.read_csv(cfg["paths_resolved"]["feature_table"], dtype={"participant_id": str})
    ft["idx"] = ft.groupby("session_dir").cumcount()
    # participants with more than one session folder (Protocol E2 sensitivity)
    pids = [re.match(r"session_\d+_\d+_(\d+)", d).group(1) for d in os.listdir(raw_dir)
            if os.path.isdir(os.path.join(raw_dir, d)) and re.match(r"session_\d+_\d+_(\d+)", d)]
    dup_pids = {p for p in set(pids) if pids.count(p) > 1}

    rows = []
    for sd in sorted(ft["session_dir"].unique()):
        inter = glob.glob(os.path.join(raw_dir, sd, "interactions*.csv"))[0]
        ev = _parse_session_events(inter)
        for i, e in enumerate(ev):
            e["session_dir"], e["idx"] = sd, i
            rows.append(e)
    ev = pd.DataFrame(rows)
    t = ft.merge(ev, on=["session_dir", "idx"], how="left", validate="one_to_one")

    # integrity: both sources describe the same decision
    assert t["end_page"].notna().all(), "feature-table rows without a raw event"
    assert (ev.groupby("session_dir").size() == ft.groupby("session_dir").size()).all(), "row count mismatch"
    ch = t["decision"] == "charge"
    assert ((t["end_page"] == "charging") == ch).all(), "decision mismatch between sources"
    assert (t.loc[ch, "kiosk_attack"].values == t.loc[ch, "logged_attack"].values).all(), "attack label mismatch"
    assert (t.loc[ch, "kiosk_attack"].isin(["Safe", "Cyber Attack", "System Anomaly"])).all()
    assert ((t.loc[ch, "kiosk_attack"] != "Safe").astype(int).values == t.loc[ch, "chosen_attacked"].astype(int).values).all(), \
        "label disagrees with layout attack flag"

    feats = cfg["features"]
    out = pd.DataFrame({
        "participant_id": t["participant_id"], "session_dir": t["session_dir"], "idx": t["idx"],
        "decision": t["decision"], "trial_index": pd.to_numeric(t["trial"], errors="coerce"),
        "t_start_ms": t["t_start_ms"], "t_end_ms": t["t_end_ms"],
        "n_available": t["n_available"], "n_attacked": t["n_attacked"],
        "incident_mode": t["layout_incident_mode"].astype(int),
        "ai_help_used": t["ai_help_used"].astype(int), "rag_contaminated": t["rag_contaminated"].astype(bool),
        "window_duration_s": t["window_duration_s"], "gaze_missing": t["gaze_missing"].astype(bool),
        "dup_participant": t["participant_id"].isin(dup_pids),
        "y": t["chosen_attacked"],
    })
    out["period"] = [_period(sd[8:16], feats["periods"]) for sd in t["session_dir"]]
    out["period_jun"] = (out["period"] == "jun").astype(int)
    out["period_jul_aug"] = (out["period"] == "jul_aug").astype(int)
    out["p_exp"] = out["n_attacked"] / out["n_available"]
    out["informative"] = (out["n_attacked"] >= 1) & (out["n_attacked"] <= out["n_available"] - 1)
    out["offset"] = np.log(out["p_exp"].clip(1e-9, 1 - 1e-9) / (1 - out["p_exp"].clip(1e-9, 1 - 1e-9)))
    out["log_window_duration_s"] = np.log(out["window_duration_s"].clip(lower=1e-3))
    for g in feats["gaze"]:
        out[g] = t[g].values
    out["eligible_universe"] = (out["decision"] == "charge") & out["informative"]
    out["eligible_primary"] = out["eligible_universe"] & ~out["gaze_missing"]
    return out


def count_valid_gaze_samples(table, raw_dir, session_filter=None):
    """Number of valid gaze samples (status == 2 and stability > 0) inside each decision window; used only for the
    pre-specified S4 sensitivity analysis. Reads each session's gaze CSV once."""
    counts = pd.Series(np.nan, index=table.index)
    for sd, grp in table[table["eligible_primary"]].groupby("session_dir"):
        files = [f for f in glob.glob(os.path.join(raw_dir, sd, "*.csv")) if not os.path.basename(f).startswith("interactions")]
        if not files:
            continue
        g = None
        for f in files:
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                    if "gaze_forward_x" not in fh.readline():
                        continue
                g = pd.read_csv(f, usecols=["relative_to_unix_epoch_timestamp", "status", "stability"])
                break
            except Exception:
                continue
        if g is None:
            continue
        g = g.apply(pd.to_numeric, errors="coerce").dropna()
        ok = g[(g["status"] == 2) & (g["stability"] > 0)]
        ts = np.sort(ok["relative_to_unix_epoch_timestamp"].values / 1e6)
        for ix, r in grp.iterrows():
            counts.loc[ix] = np.searchsorted(ts, r["t_end_ms"], side="right") - np.searchsorted(ts, r["t_start_ms"], side="left")
    return counts


def primary_counts(table):
    u = table[table["eligible_universe"]]
    p = table[table["eligible_primary"]]
    return dict(universe_rows=len(u), universe_participants=u["participant_id"].nunique(), universe_events=int(u["y"].sum()),
                primary_rows=len(p), primary_participants=p["participant_id"].nunique(), primary_events=int(p["y"].sum()))


if __name__ == "__main__":
    cfg = load_config()
    tab = build_table(cfg)
    outdir = cfg["paths_resolved"]["results_dir"] / "_tables"
    outdir.mkdir(parents=True, exist_ok=True)
    tab.to_csv(outdir / "analysis_table_t1.csv", index=False)
    print(json.dumps(primary_counts(tab), indent=1))
