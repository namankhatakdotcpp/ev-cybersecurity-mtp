"""Gate 6 extra analyses (configs/gate6_extra.yaml), each exploratory:

  python -m backend.pipeline.gate6.extra s5       # (a) skip vs charge relative to exposure (D073)
  python -m backend.pipeline.gate6.extra grid     # (b) post-hoc ridge C-grid sensitivity (D074)
  python -m backend.pipeline.gate6.extra eeg      # (c) EEG detrended on trial_index, matched set (D075)
"""
import copy
import glob
import json
import sys

import numpy as np
import pandas as pd
import yaml
from joblib import Parallel, delayed
from scipy.stats import spearmanr

from ..gate2 import benchmark as bm
from ..gate2.build_t1_table import build_table
from ..gate2.config import REPO_ROOT
from ..gate2.matched import build_matched, load_gate4
from ..gate2.registry import register
from ..gate2.run_gate3 import _perm_auc, holm_provisional, lrt_generic, run_cv

NJ = 8                       # fewer workers than Gate 3: the SLM consistency pass is running on the same machine


def load_x():
    x = yaml.safe_load(open(REPO_ROOT / "configs" / "gate6_extra.yaml", encoding="utf-8"))
    return x


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return o


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return float(p), float(max(0, c - h)), float(min(1, c + h))


def prior_p(cfg, pattern, key):
    f = sorted(glob.glob(str(cfg["paths_resolved"]["results_dir"] / pattern / "summary.json")))[-1]
    d = json.load(open(f))["metrics"]
    for k in key:
        d = d[k]
    return float(d)


def cv_block(T, models, cfg, cols_gaze, nperm, pseed, contrast, learner="ridge", with_lrt=None):
    log1p = cfg["features"]["log1p_counts"]
    cb = cfg["claim_b"]
    y, pid = T["y"].to_numpy(float), T["participant_id"].to_numpy()
    runs, chosen = run_cv(T, models, learner, cfg, n_jobs=NJ)
    pt, ci, draws = bm.evaluate(y, pid, runs, cb["bootstrap_resamples"], cb["bootstrap_seed"], cfg["g3"]["calibration"]["n_bins"])
    out = dict(n_rows=len(T), n_participants=int(T.participant_id.nunique()), n_events=int(T.y.sum()),
               auroc={m: dict(point=pt[m]["auroc"], ci=ci[m]["auroc"], brier=pt[m]["brier"]) for m in models},
               chosen=pd.DataFrame(chosen).assign(hp=lambda d: d["C"].astype(str)).groupby(["model", "hp"]).size().unstack(fill_value=0).to_dict("index") if learner == "ridge" else None)
    a, b = contrast
    out["delta_auroc"] = bm.paired(draws, a, b, "auroc")
    out["delta_brier"] = bm.paired(draws, a, b, "brier")
    if nperm:
        perm = np.array(Parallel(n_jobs=NJ)(delayed(_perm_auc)(i, T, {"G": models[a]}, learner, cfg, cols_gaze, pseed) for i in range(nperm)))
        obs = pt[a]["auroc"]
        out["permutation"] = dict(B=nperm, observed=obs, p=float((1 + np.sum(perm >= obs)) / (1 + nperm)), perm_auc_mean=float(perm.mean()), perm_auc_q95=float(np.quantile(perm, 0.95)))
    if with_lrt:
        out["lrt"] = lrt_generic(T, models[with_lrt[0]], models[with_lrt[1]], log1p)
    return out, runs, draws, pt, ci


# ---------------------------------------------------------------------------------------------------
# (a) S5
# ---------------------------------------------------------------------------------------------------
def stage_s5(cfg, x):
    s5 = x["s5"]
    T_all = build_table(cfg)
    gaze = cfg["features"]["gaze"]
    design = cfg["features"]["design"]
    A = T_all[T_all["decision"].isin(["charge", "skip"])].copy()
    A["skip"] = (A["decision"] == "skip").astype(float)
    A["benign"] = (A["n_attacked"] == 0).astype(int)
    A["all_attacked"] = (A["n_attacked"] == A["n_available"]).astype(int)
    A["offset"] = 0.0
    # descriptive skip rate by exposure cell (all 1,123 visits)
    desc = []
    for (a, n), g in A.groupby(["n_attacked", "n_available"]):
        k = int(g["skip"].sum())
        p, lo, hi = wilson(k, len(g))
        desc.append(dict(n_attacked=int(a), n_available=int(n), visits=len(g), participants=int(g.participant_id.nunique()), skips=k, skip_rate=p, lo=lo, hi=hi,
                         meaning="skip is over-cautious (nothing attacked)" if a == 0 else ("skip is protective (everything attacked)" if a == n else "mixed station")))
    for lab, m in (("benign", A.benign == 1), ("all_attacked", A.all_attacked == 1), ("mixed", (A.benign == 0) & (A.all_attacked == 0))):
        k, n = int(A.loc[m, "skip"].sum()), int(m.sum())
        p, lo, hi = wilson(k, n)
        desc.append(dict(n_attacked=None, n_available=None, visits=n, participants=int(A.loc[m, "participant_id"].nunique()), skips=k, skip_rate=p, lo=lo, hi=hi, meaning=f"station type: {lab}"))
    res = {}
    for name, mask, expo in (("main_informative", A["informative"], s5["exposure_block"]), ("extension_all_stations", A["informative"] | ~A["informative"], s5["extension_exposure_block"])):
        T = A[mask & ~A["gaze_missing"]].copy()
        T["y"] = T["skip"]
        T = T.dropna(subset=["log_window_duration_s", "ai_help_used", "trial_index"] + gaze).reset_index(drop=True)
        base = list(expo) + list(design)
        models = {m: base + list(ex) for m, ex in s5["sets"].items()}
        block, runs, draws, pt, ci = cv_block(T, models, cfg, gaze, s5["permutation"]["B"], s5["permutation"]["seed"] + (0 if name == "main_informative" else 1), s5["contrast"], with_lrt=("B", "BG"))
        block["delta_BG_minus_B0"] = bm.paired(draws, "BG", "B0", "auroc")
        block["delta_B_minus_B0"] = bm.paired(draws, "B", "B0", "auroc")
        block["skip_rate"] = float(T["skip"].mean())
        res[name] = block
        print(name, json.dumps(clean(block), default=float)[:600], flush=True)
    p = {"S1": prior_p(cfg, "g3_secondary_S1_*", ["lrt", "p"]), "S2": prior_p(cfg, "g3_secondary_S2_*", ["lrt", "p"]),
         "S6": prior_p(cfg, "g4_s6_ridge_*", ["lrt_BGE_vs_BG", "p"]), "S5": res["main_informative"]["lrt"]["p"]}
    holm = holm_provisional(p, 4)
    out = dict(descriptive_skip_by_exposure=desc, results=res, holm=holm,
               holm_note="family {S1,S2,S5,S6}, complete at size 4; S6 enters with its descriptive-only LRT (17 df on 70 events); the extension (all stations) is exploratory and outside the family")
    tp = cfg["paths_resolved"]["results_dir"] / "_tables" / "analysis_table_s5.csv"
    A.to_csv(tp, index=False)
    eid, run = register(cfg, "g6_s5_skip_vs_charge", "5x20 repeated participant-grouped nested CV; skip=1", cfg["claim_b"]["repeat_seeds"], "ridge logistic (no offset)",
                        dict(config="configs/gate6_extra.yaml"), clean(out), tp, notes="S5 (exploratory) skip vs charge relative to exposure; D073")
    print(eid)
    (cfg["paths_resolved"]["results_dir"] / "gate6_s5.json").write_text(json.dumps(clean(out), indent=1))
    return out


# ---------------------------------------------------------------------------------------------------
# (b) ridge grid sensitivity
# ---------------------------------------------------------------------------------------------------
def stage_grid(cfg, x):
    g = x["ridge_grid_sensitivity"]
    cfg2 = copy.deepcopy(cfg)
    cfg2["g3"]["learners"]["ridge"]["C_grid"] = g["C_grid"]
    T_all = build_table(cfg)
    T = T_all[T_all.eligible_primary].reset_index(drop=True)
    models = {s: bm.set_columns(cfg2, s) for s in g["sets"]}
    block, runs, draws, pt, ci = cv_block(T, models, cfg2, cfg["features"]["gaze"], 0, 0, ("BG", "B"))
    block["delta_BG_minus_B0"] = bm.paired(draws, "BG", "B0", "auroc")
    block["delta_B_minus_B0"] = bm.paired(draws, "B", "B0", "auroc")
    block["C_grid"] = g["C_grid"]
    orig = sorted(glob.glob(str(cfg["paths_resolved"]["results_dir"] / "g3_grid_ridge_*" / "summary.json")))[-1]
    om = json.load(open(orig))["metrics"]
    block["original_grid"] = dict(auroc={m: om["point"][m]["auroc"] for m in ("B0", "B", "BG")}, delta_BG_minus_B=om["paired"]["BG_minus_B"]["auroc"], run=orig.replace("\\", "/").split("/")[-2])
    tp = cfg["paths_resolved"]["results_dir"] / "_tables" / "analysis_table_t1.csv"
    eid, run = register(cfg2, "g6_ridge_grid_sensitivity", "post-hoc sensitivity, deviation from protocol v1: 5x20 nested CV, extended ridge C grid", cfg["claim_b"]["repeat_seeds"], "ridge logistic with offset",
                        dict(config="configs/gate6_extra.yaml", grid=g["C_grid"]), clean(block), tp, notes="post-hoc sensitivity, deviation from protocol v1; D074")
    print(eid)
    print(json.dumps(clean(block), indent=1, default=float))
    (cfg["paths_resolved"]["results_dir"] / "gate6_grid.json").write_text(json.dumps(clean(block), indent=1))
    return block


# ---------------------------------------------------------------------------------------------------
# (c) EEG detrended on trial index
# ---------------------------------------------------------------------------------------------------
def stage_eeg(x):
    e = x["eeg_detrend"]
    cfg = load_gate4()
    T_all, primary, matched = build_matched(cfg)
    eeg = cfg["g4"]["matched_set"]["eeg_features"]
    cb = cfg["claim_b"]
    models = {s: list(cfg["features"]["exposure"] + cfg["features"]["design"] + cfg["g4"]["sets"][s]["extra"]) for s in ("B", "BG", "BGE")}
    y, pid = matched["y"].to_numpy(float), matched["participant_id"].to_numpy()
    runs0, _ = run_cv(matched, models, "ridge", cfg, n_jobs=NJ)                                   # as in Gate 4 (reproduces g4 ridge B, BG, BGE)
    cfg_d = copy.deepcopy(cfg)
    cfg_d["g3"]["detrend_on"] = dict(by=e["detrend_on"]["by"], cols=eeg)
    runs1, chosen = run_cv(matched, {"BGE_detrended": models["BGE"]}, "ridge", cfg_d, n_jobs=NJ)
    runs = dict(runs0, **runs1)
    pt, ci, draws = bm.evaluate(y, pid, runs, cb["bootstrap_resamples"], cb["bootstrap_seed"], cfg["g3"]["calibration"]["n_bins"])
    out = dict(n_rows=len(matched), n_participants=int(matched.participant_id.nunique()), n_events=int(matched.y.sum()),
               auroc={m: dict(point=pt[m]["auroc"], ci=ci[m]["auroc"], brier=pt[m]["brier"]) for m in runs},
               primary_BGE_detrended_minus_BG=dict(auroc=bm.paired(draws, "BGE_detrended", "BG", "auroc"), brier=bm.paired(draws, "BGE_detrended", "BG", "brier")),
               descriptive_BGE_detrended_minus_BGE=dict(auroc=bm.paired(draws, "BGE_detrended", "BGE", "auroc")),
               descriptive_BGE_minus_BG=dict(auroc=bm.paired(draws, "BGE", "BG", "auroc")))
    g4 = sorted(glob.glob(str(cfg["paths_resolved"]["results_dir"] / "g4_s6_ridge_*" / "summary.json")))[-1]
    m4 = json.load(open(g4))["metrics"]["point"]
    out["gate4_reproduction"] = {m: dict(now=pt[m]["auroc"], gate4=m4[m]["auroc"]) for m in ("B", "BG", "BGE")}
    nperm = e["permutation"]["B"]
    perm = np.array(Parallel(n_jobs=NJ)(delayed(_perm_auc)(i, matched, {"G": models["BGE"]}, "ridge", cfg_d, eeg, e["permutation"]["seed"]) for i in range(nperm)))
    obs = pt["BGE_detrended"]["auroc"]
    out["permutation_BGE_detrended"] = dict(B=nperm, observed=obs, p=float((1 + np.sum(perm >= obs)) / (1 + nperm)), perm_auc_mean=float(perm.mean()), perm_auc_q95=float(np.quantile(perm, 0.95)))
    drift = []
    for c in eeg:
        r, p = spearmanr(matched[c], matched["trial_index"])
        drift.append(dict(feature=c, spearman_with_trial_index=float(r), p_descriptive=float(p)))
    out["trial_index_drift"] = drift
    out["chosen_C"] = pd.DataFrame(chosen).assign(hp=lambda d: d["C"].astype(str)).groupby(["model", "hp"]).size().unstack(fill_value=0).to_dict("index")
    tp = cfg["paths_resolved"]["results_dir"] / "_tables" / "analysis_table_matched_eeg.csv"
    eid, run = register(cfg, "g6_eeg_detrended", "post-hoc, deviation from protocol v1: 5x20 nested CV on the matched EEG set, EEG detrended on trial_index within the training fold",
                        cb["repeat_seeds"], "ridge logistic with offset", dict(config="configs/gate6_extra.yaml"), clean(out), tp, notes="D075")
    print(eid)
    print(json.dumps(clean(out), indent=1, default=float))
    (cfg["paths_resolved"]["results_dir"] / "gate6_eeg.json").write_text(json.dumps(clean(out), indent=1))
    return out


if __name__ == "__main__":
    x = load_x()
    step = sys.argv[1]
    if step == "eeg":
        stage_eeg(x)
    else:
        cfg = bm.load_gate3()
        (cfg["paths_resolved"]["results_dir"] / "_tables").mkdir(parents=True, exist_ok=True)
        {"s5": stage_s5, "grid": stage_grid}[step](cfg, x)
