"""Gate 5 scoring exactly as fixed in docs/protocol/GATE5_scoring_spec.md (committed before any accuracy reply was scored).
Parsing is score_slm.parse_reply (the rule frozen in configs/gate5_prompts.yaml). A failed reply counts as wrong on every kiosk it covers.
Per-row predictions are written to results/_slm/predictions/ (local, scenario ids only)."""
import json
import re
from collections import defaultdict

import numpy as np
import pandas as pd

from .build_scenarios import VISIBLE
from .score_slm import MODELS, SLM_DIR, agreement, load_truth, parse_reply, pilot_summary, prop, read_replies, timing, wilson

N_BOOT = 2000
BOOT_SEED = 20261030
DEGENERATE = 0.95
LABEL_RE = re.compile(r"deep\s?fake", re.I)
WIDE_RE = re.compile(r"fake|scam|phish", re.I)
SUBSETS = {"all": None, "excl_label": "lab", "excl_wide": "wide"}
REFS = ["always SAFE", "always UNSAFE", "deepfake-image rule", "discount-badge rule", "random (expected)"]


def _wil(k, n):
    lo, hi = wilson(k, n)
    return dict(k=float(k), n=int(n), p=(k / n if n else float("nan")), lo=lo, hi=hi)


# ---------------------------------------------------------------------------------------------------
# inputs: V2 image-description flags
# ---------------------------------------------------------------------------------------------------
def load_flags():
    from .build_scenarios import load_cfg
    d = load_cfg()["paths_resolved"]["out_dir"]
    flags = {}
    for line in open(d / "scenarios_inputs.jsonl", encoding="utf-8"):
        i = json.loads(line)
        per = {}
        for ln in i["text_V2"].split("\n"):
            m = re.match(r"Kiosk (\d+):(.*)", ln)
            if m:
                per[int(m.group(1))] = (bool(LABEL_RE.search(m.group(2))), bool(WIDE_RE.search(m.group(2))))
        flags[i["scenario_id"]] = dict(kiosk=per, lab=any(v[0] for v in per.values()), wide=any(v[1] for v in per.values()))
    return flags


# ---------------------------------------------------------------------------------------------------
# frames (one row per kiosk judgement / per recommendation)
# ---------------------------------------------------------------------------------------------------
def detection_frame(model, step, truth=None, flags=None):
    truth, flags = truth or load_truth(), flags or load_flags()
    rows = []
    for r in read_replies(step, model):
        if r["task"] != "detection":
            continue
        t = truth[r["scenario_id"]]
        km = {k["id"]: k for k in t["kiosks"]}
        parsed, fail = parse_reply(r["reply"], "detection", r["available"])
        for kid in r["available"]:
            k = km[kid]
            f = flags[r["scenario_id"]]["kiosk"].get(kid, (False, False))
            rows.append(dict(model=model, step=step, seed=r["seed"], variant=r["variant"], scenario_id=r["scenario_id"], stratum=t["stratum"], kiosk=kid,
                             visible_class=k["visible_class"], hidden_mode=k["hidden_mode"], attacked=int(k["attacked"]), image_type=k["image_type"], badge=int(bool(k["badge"])),
                             lab=int(f[0]), wide=int(f[1]), pred=(parsed[kid] if parsed else "FAIL"), fail=fail or ""))
    return pd.DataFrame(rows)


def recommendation_frame(model, step, truth=None, flags=None):
    truth, flags = truth or load_truth(), flags or load_flags()
    rows = []
    for r in read_replies(step, model):
        if r["task"] != "recommendation":
            continue
        t = truth[r["scenario_id"]]
        km = {k["id"]: k for k in t["kiosks"]}
        parsed, fail = parse_reply(r["reply"], "recommendation", r["available"])
        if fail:
            out, choice = "FAIL", ""
        elif parsed == "SKIP":
            out, choice = "skip", "SKIP"
        else:
            out, choice = ("attacked" if km[parsed]["attacked"] else "safe"), str(parsed)
        n_av = len(r["available"])
        rows.append(dict(model=model, step=step, seed=r["seed"], variant=r["variant"], scenario_id=r["scenario_id"], stratum=t["stratum"], outcome=out, choice=choice,
                         fail=fail or "", random_safe=len(t["safe_available"]) / n_av, lab=int(flags[r["scenario_id"]]["lab"]), wide=int(flags[r["scenario_id"]]["wide"])))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------
# detection metrics
# ---------------------------------------------------------------------------------------------------
def model_p(df):
    """Probability of UNSAFE; a failed reply counts as the wrong answer on that kiosk."""
    a = df["attacked"].to_numpy()
    return np.where(df["pred"] == "UNSAFE", 1.0, np.where(df["pred"] == "SAFE", 0.0, 1.0 - a))


def ref_p(df, name):
    n = len(df)
    return {"always SAFE": np.zeros(n), "always UNSAFE": np.ones(n), "deepfake-image rule": (df["image_type"] == "deepfake").to_numpy().astype(float),
            "discount-badge rule": df["badge"].to_numpy().astype(float), "random (expected)": np.full(n, 0.5)}[name]


def scenario_counts(df, p):
    a = df["attacked"].to_numpy().astype(float)
    g = pd.DataFrame(dict(sid=df["scenario_id"].to_numpy(), tp=a * p, fn=a * (1 - p), fp=(1 - a) * p, tn=(1 - a) * (1 - p))).groupby("sid").sum().sort_index()
    return g.to_numpy()


def bal_acc(tot):
    tot = np.atleast_2d(tot)
    return (tot[:, 0] / (tot[:, 0] + tot[:, 1]) + tot[:, 3] / (tot[:, 3] + tot[:, 2])) / 2


def rates(df, p):
    a = df["attacked"].to_numpy().astype(float)
    na, ns = a.sum(), (1 - a).sum()
    fs = (a * (1 - p)).sum()
    fw = ((1 - a) * p).sum()
    return dict(false_safe=_wil(fs, na), false_warning=_wil(fw, ns))


def class_errors(df, p):
    out = {}
    for c in VISIBLE:
        m = (df["visible_class"] == c).to_numpy()
        if not m.any():
            continue
        a = df["attacked"].to_numpy()[m]
        err = np.where(a == 1, 1 - p[m], p[m]).sum()
        out[c] = dict(kind="false_safe" if a[0] == 1 else "false_warning", **_wil(err, int(m.sum())))
    return out


def mode_recall(df, p):
    out = {}
    for md in ("reduced", "blocked"):
        m = ((df["hidden_mode"] == md) & (df["attacked"] == 1)).to_numpy()
        if m.any():
            out[md] = _wil(p[m].sum(), int(m.sum()))
    return out


def degenerate_det(df):
    v = df[df["pred"] != "FAIL"]
    if not len(v):
        return dict(flag=True, share_unsafe=float("nan"), n_valid=0)
    s = float((v["pred"] == "UNSAFE").mean())
    return dict(flag=bool(s >= DEGENERATE or s <= 1 - DEGENERATE), share_unsafe=s, n_valid=int(len(v)))


def detection_block(df):
    """df: one model, one variant, one seed, one subset."""
    p = model_p(df)
    refp = {n: ref_p(df, n) for n in REFS}
    M = scenario_counts(df, p)
    R = {n: scenario_counts(df, refp[n]) for n in REFS}
    point_ref = {n: float(bal_acc(R[n].sum(0))[0]) for n in REFS}
    best = max(point_ref, key=point_ref.get)
    S = M.shape[0]
    rng = np.random.default_rng(BOOT_SEED)
    w = rng.multinomial(S, np.full(S, 1.0 / S), size=N_BOOT)
    diff = bal_acc(w @ M) - bal_acc(w @ R[best])
    lo, hi = np.percentile(diff, [2.5, 97.5])
    pv = min(1.0, 2 * min(((diff <= 0).sum() + 1) / (N_BOOT + 1), ((diff >= 0).sum() + 1) / (N_BOOT + 1)))
    bal_m = float(bal_acc(M.sum(0))[0])
    return dict(n_kiosks=int(len(df)), n_scenarios=int(S), failed_replies=prop(int((df.groupby("scenario_id")["fail"].first() != "").sum()), int(S)),
                degenerate=degenerate_det(df), **rates(df, p), balanced_accuracy=bal_m, best_reference=best, best_reference_balanced_accuracy=point_ref[best],
                diff_vs_best=dict(point=bal_m - point_ref[best], lo=float(lo), hi=float(hi), p_boot=float(pv)),
                by_visible_class=class_errors(df, p), recall_by_hidden_mode=mode_recall(df, p),
                references={n: dict(**rates(df, refp[n]), balanced_accuracy=point_ref[n], by_visible_class=class_errors(df, refp[n])) for n in REFS})


def holm(pvals):
    keys = sorted(pvals, key=pvals.get)
    m = len(keys)
    out, run = {}, 0.0
    for i, k in enumerate(keys):
        run = max(run, min(1.0, (m - i) * pvals[k]))
        out[k] = run
    return out


# ---------------------------------------------------------------------------------------------------
# recommendation metrics
# ---------------------------------------------------------------------------------------------------
def degenerate_rec(df):
    v = df[df["outcome"] != "FAIL"]
    if not len(v):
        return dict(flag=True, top_share=float("nan"), n_valid=0)
    top = float(v["choice"].value_counts(normalize=True).iloc[0])
    return dict(flag=bool(top >= DEGENERATE), top_share=top, top_choice=str(v["choice"].value_counts().index[0]), n_valid=int(len(v)))


def recommendation_block(df):
    out = dict(degenerate=degenerate_rec(df), failed_replies=prop(int((df["fail"] != "").sum()), len(df)))
    for st in ("mixed", "benign", "all_attacked"):
        d = df[df["stratum"] == st]
        n = len(d)
        c = d["outcome"].value_counts()
        blk = dict(n=int(n), safe=_wil(c.get("safe", 0), n), attacked=_wil(c.get("attacked", 0), n), skip=_wil(c.get("skip", 0), n), failed=_wil(c.get("FAIL", 0), n))
        if st == "mixed" and n:
            rr = float(d["random_safe"].mean())
            blk["random_choice_safe_rate"] = rr
            blk["safe_choice_interval_above_random"] = bool(blk["safe"]["lo"] > rr)
            blk["safe_choice_interval_below_random"] = bool(blk["safe"]["hi"] < rr)
        out[st] = blk
    return out


def subset(df, kind):
    col = SUBSETS[kind]
    return df if col is None else df[df[col] == 0]


# ---------------------------------------------------------------------------------------------------
# a model
# ---------------------------------------------------------------------------------------------------
def score_model(model, truth=None, flags=None):
    truth, flags = truth or load_truth(), flags or load_flags()
    out = dict(model=model, detection={}, recommendation={}, consistency={})
    PRED = SLM_DIR / "predictions"
    PRED.mkdir(exist_ok=True)
    det = {s: detection_frame(model, s, truth, flags) for s in ("accuracy", "consistency")}
    rec = {s: recommendation_frame(model, s, truth, flags) for s in ("accuracy", "consistency")}
    pd.concat([d for d in det.values() if len(d)]).to_csv(PRED / (model.replace(":", "_") + "_detection.csv"), index=False)
    pd.concat([d for d in rec.values() if len(d)]).to_csv(PRED / (model.replace(":", "_") + "_recommendation.csv"), index=False)
    for v in ("V1", "V2"):
        for sk in (["all"] if v == "V1" else list(SUBSETS)):
            d = det["accuracy"]
            d = d[d["variant"] == v] if len(d) else d
            if len(d):
                out["detection"][f"{v}|{sk}"] = detection_block(subset(d, sk))
            r = rec["accuracy"]
            r = r[r["variant"] == v] if len(r) else r
            if len(r):
                out["recommendation"][f"{v}|{sk}"] = recommendation_block(subset(r, sk))
    # consistency pass: per-seed errors and degenerate flags, and cross-seed agreement
    cons_raw = read_replies("consistency", model)
    for v in ("V1", "V2"):
        d, r = det["consistency"], rec["consistency"]
        per = []
        if len(d):
            for s, g in d[d["variant"] == v].groupby("seed"):
                rt = rates(g, model_p(g))
                per.append(dict(seed=int(s), false_safe=rt["false_safe"]["p"], false_warning=rt["false_warning"]["p"], degenerate=degenerate_det(g)["flag"], failed=float((g["fail"] != "").mean())))
        perr = []
        if len(r):
            for s, g in r[r["variant"] == v].groupby("seed"):
                mx = g[g["stratum"] == "mixed"]
                perr.append(dict(seed=int(s), mixed_safe_choice=float((mx["outcome"] == "safe").mean()) if len(mx) else float("nan"), degenerate=degenerate_rec(g)["flag"]))
        out["consistency"][v] = dict(detection_per_seed=per, recommendation_per_seed=perr,
                                     agreement={t: agreement([x for x in cons_raw if x["variant"] == v and x["task"] == t], t, truth) for t in ("detection", "recommendation") if any(x["variant"] == v and x["task"] == t for x in cons_raw)})
    acc = read_replies("accuracy", model)
    out["timing_accuracy_pass"] = timing(acc) if acc else None
    out["timing_consistency_pass"] = timing(cons_raw) if cons_raw else None
    mp = SLM_DIR / "accuracy" / "_meta.json"
    out["vram_and_runtime"] = json.loads(mp.read_text()).get(model) if mp.exists() else None
    out["first_call_load_ms"] = acc[0].get("load_ms") if acc else None
    out["pilot"] = pilot_summary().get(model)
    return out


def score_all(models=None):
    res = {m: score_model(m) for m in (models or MODELS)}
    fam = {}
    for m, r in res.items():
        for key in ("V1|all", "V2|excl_label"):
            if key in r["detection"]:
                fam[(m, key)] = r["detection"][key]["diff_vs_best"]["p_boot"]
    adj = holm(fam)
    for (m, key), a in adj.items():
        b = res[m]["detection"][key]
        b["diff_vs_best"]["p_holm"] = a
        b["better_than_best_reference"] = bool(a < 0.05 and b["diff_vs_best"]["lo"] > 0)
    return res, dict(holm_family_size=len(fam))
