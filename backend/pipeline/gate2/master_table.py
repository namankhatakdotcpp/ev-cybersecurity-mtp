"""Generate the Gate 3 master comparison tables programmatically from the experiment registry (Protocol v1 section 13).
Reads only results/registry.csv and the per-run summary.json files; nothing is copied by hand.

  python -m backend.pipeline.gate2.master_table      ->  results/master_table_gate3.md and .csv
"""
import json

import pandas as pd

from .config import load_config

SETS = ["B0", "B", "G", "BG"]
LEARNERS = [("ridge", "Ridge logistic (offset)"), ("rf", "Random forest"), ("hgb", "HistGradientBoosting")]


def _latest(reg, name):
    rows = reg[reg["experiment_id"].str.match(rf"^{name}_\d{{8}}_")]
    if rows.empty:
        return None
    return rows.sort_values("timestamp").iloc[-1]


def _load(results, row):
    return json.loads((results / row["experiment_id"] / "summary.json").read_text())


def _fmt(pt, ci, k=3):
    return f"{pt:.{k}f} [{ci[0]:.{k}f}, {ci[1]:.{k}f}]"


def build(cfg=None):
    cfg = cfg or load_config()
    results = cfg["paths_resolved"]["results_dir"]
    reg = pd.read_csv(results / "registry.csv", dtype=str)
    md, long_rows, prov = [], [], []

    def block(title, df):
        md.append(f"\n### {title}\n")
        if df.empty:
            md.append("(no runs registered)")
            return
        cols = list(df.columns)
        md.append("| " + " | ".join(cols) + " |")
        md.append("|" + "|".join("---" for _ in cols) + "|")
        for _, r in df.iterrows():
            md.append("| " + " | ".join(str(r[c]) for c in cols) + " |")

    # ---- Table 1 and 2 from the grid runs
    t1, t2a, t2b, t3 = [], [], [], []
    for key, label in LEARNERS:
        row = _latest(reg, f"g3_grid_{key}")
        if row is None:
            continue
        m = _load(results, row)["metrics"]
        prov.append(f"{label}: `{row['experiment_id']}` (code {row['git_commit'][:7]}, dataset {row['dataset_version'][:10]})")
        names = (["CONST"] if "CONST" in m["point"] else []) + SETS
        for s in names:
            p, c = m["point"][s], m["ci"][s]
            if s == "CONST":
                # constant training-fold event rate: AUROC and calibration slope are not meaningful for a constant
                # (the fold-to-fold variation of the training rate even makes AUROC fall below 0.5 by construction)
                t1.append({"Model": "constant event rate (reference)", "Set": "-", "AUROC": "n/a", "PR-AUC": _fmt(p["pr_auc"], c["pr_auc"]),
                           "Brier": _fmt(p["brier"], c["brier"]), "Calibration slope": "n/a", "Calibration-in-the-large": "n/a"})
                continue
            t1.append({"Model": label, "Set": s, "AUROC": _fmt(p["auroc"], c["auroc"]), "PR-AUC": _fmt(p["pr_auc"], c["pr_auc"]),
                       "Brier": _fmt(p["brier"], c["brier"]), "Calibration slope": _fmt(p["calib_slope"], c["calib_slope"], 2),
                       "Calibration-in-the-large": _fmt(p["calib_in_the_large"], c["calib_in_the_large"], 2)})
            for op, tgt in (("A", t2a), ("B", t2b)):
                r = {"Model": label, "Set": s}
                for k, nm_ in (("balanced_accuracy", "Bal. acc."), ("recall", "Recall"), ("specificity", "Specificity"), ("precision", "Precision"),
                               ("f1", "F1"), ("false_safe", "False-safe"), ("false_warning", "False-warning")):
                    r[nm_] = _fmt(p[f"{k}_{op}"], c[f"{k}_{op}"], 2)
                tgt.append(r)
            for met in ("auroc", "pr_auc", "brier", "calib_slope", "calib_in_the_large"):
                long_rows.append(dict(table="grid", model=key, set=s, metric=met, point=p[met], ci_low=c[met][0], ci_high=c[met][1]))
        for k, v in m["paired"].items():
            a = v["auroc"]
            t3.append({"Model": label, "Comparison": k.replace("_minus_", " minus "), "Delta AUROC": _fmt(a["mean"], a["ci"], 3), "Bootstrap p (two-sided)": f"{a['p_boot']:.3f}",
                       "Delta Brier": _fmt(v["brier"]["mean"], v["brier"]["ci"], 4)})
    md.append("# Gate 3 master comparison (generated; do not edit by hand)")
    md.append(f"\nProtocol v1 `{cfg['protocol']['commit'][:7]}` (tag {cfg['protocol']['tag']}), target {cfg['target']['label_version']} "
              f"(charge decisions at informative stations; primary set with gaze). Mean over 20 repeats of 5-fold participant-grouped nested CV; "
              f"CIs are participant-level bootstrap (2,000). Operating points A (maximise balanced accuracy) and B (largest threshold with recall >= 0.80) "
              f"are fixed on the inner validation predictions of each training fold. False-safe = 1 - recall; false-warning = 1 - specificity.")
    md.append("\nRuns used:\n" + "\n".join(f"- {p}" for p in prov))
    block("Table 1. Discrimination and calibration", pd.DataFrame(t1))
    block("Table 2a. Operating point A (maximise balanced accuracy)", pd.DataFrame(t2a))
    block("Table 2b. Operating point B (recall target 0.80)", pd.DataFrame(t2b))
    block("Table 3. Paired differences within each learner", pd.DataFrame(t3))

    # ---- secondary tests
    sec = []
    for nm in ("S1", "S2"):
        row = _latest(reg, f"g3_secondary_{nm}")
        if row is None:
            continue
        s = _load(results, row)["metrics"]
        d = s["delta_auroc"] if nm == "S1" else s["delta_auroc_BGE_minus_BE"]
        sec.append({"Test": nm, "Rows / participants / events": f"{s['n_rows']} / {s['n_participants']} / {s['n_events']}",
                    "LRT chi-square (df 6)": f"{s['lrt']['stat']:.2f}", "LRT p": f"{s['lrt']['p']:.3f}", "Delta AUROC": _fmt(d["mean"], d["ci"], 3),
                    "Permutation p (CV, 200)": f"{s['permutation']['p']:.3f}",
                    "Holm adj. (upper bound, family 4)": f"{s['holm']['holm_adjusted_upper_bound']:.3f}" if s.get("holm") else ""})
        prov.append(f"{nm}: `{row['experiment_id']}`")
    block("Table 4. Secondary tests S1 (G vs exposure baseline) and S2 (early-window H1)", pd.DataFrame(sec))

    row = _latest(reg, "g3_exploratory_S8")
    if row is not None:
        s = _load(results, row)["metrics"]
        t5 = [{"Comparison": c["comparison"].replace("_minus_", " minus "), "Set": c["set"], "Delta AUROC": _fmt(c["delta_auroc"], c["ci"], 3),
               "Bootstrap p": f"{c['p_boot']:.3f}", "FDR (BH)": f"{c['fdr_bh']:.3f}"} for c in s["comparisons"]]
        block("Table 5. Exploratory S8 (tree models vs ridge)", pd.DataFrame(t5))
        md.append(f"\nChallenger boosting model: {s['challenger_boosting']}.")
    text = "\n".join(md) + "\n"
    (results / "master_table_gate3.md").write_text(text, encoding="utf-8")
    pd.DataFrame(long_rows).to_csv(results / "master_table_gate3_long.csv", index=False)
    return text




def build_gate4(cfg=None):
    """Gate 4 tables (S6, matched EEG set) generated from the registry rows g4_s6_*."""
    cfg = cfg or load_config()
    results = cfg["paths_resolved"]["results_dir"]
    reg = pd.read_csv(results / "registry.csv", dtype=str)
    md = ["# Gate 4 master comparison, S6 matched EEG set (generated; do not edit by hand)"]
    sets = ["B0", "B", "BG", "BGE"]
    names = {"ridge": "Ridge logistic (offset), primary", "rf": "Random forest (exploratory)", "hgb": "HistGradientBoosting (exploratory)"}
    rows, ops, cmp_rows, runs = [], [], [], []
    summ = None
    for key, label in names.items():
        row = _latest(reg, f"g4_s6_{key}")
        if row is None:
            continue
        s = _load(results, row)["metrics"]
        runs.append(f"{label}: `{row['experiment_id']}` (code {row['git_commit'][:7]})")
        if key == "ridge":
            summ = s
        names_ = (["CONST"] if "CONST" in s["point"] else []) + sets
        for st in names_:
            p, c = s["point"][st], s["ci"][st]
            if st == "CONST":
                rows.append({"Model": "constant event rate (reference)", "Set": "-", "AUROC": "n/a", "PR-AUC": _fmt(p["pr_auc"], c["pr_auc"]), "Brier": _fmt(p["brier"], c["brier"]),
                             "Calibration slope": "n/a"})
                continue
            rows.append({"Model": label, "Set": st, "AUROC": _fmt(p["auroc"], c["auroc"]), "PR-AUC": _fmt(p["pr_auc"], c["pr_auc"]), "Brier": _fmt(p["brier"], c["brier"]),
                         "Calibration slope": _fmt(p["calib_slope"], c["calib_slope"], 2)})
            if key == "ridge":
                for op in ("A", "B"):
                    ops.append({"Set": st, "Operating point": op, "Recall": _fmt(p[f"recall_{op}"], c[f"recall_{op}"], 2), "Specificity": _fmt(p[f"specificity_{op}"], c[f"specificity_{op}"], 2),
                                "Precision": _fmt(p[f"precision_{op}"], c[f"precision_{op}"], 2), "False-safe": _fmt(p[f"false_safe_{op}"], c[f"false_safe_{op}"], 2),
                                "False-warning": _fmt(p[f"false_warning_{op}"], c[f"false_warning_{op}"], 2)})
        for k, v in s["paired"].items():
            a = v["auroc"]
            cmp_rows.append({"Model": label, "Comparison": k.replace("_minus_", " minus ") + (" (primary S6 contrast)" if k == "BGE_minus_BG" else ""),
                             "Delta AUROC": _fmt(a["mean"], a["ci"], 3), "Bootstrap p": f"{a['p_boot']:.3f}"})
    if summ is None:
        return "\n".join(md) + "\n(no S6 run registered)\n"
    md.append(f"\nMatched set: {summ['n_rows']} rows, {summ['n_participants']} participants, {summ['n_events']} events; identical rows for every model. 5 x 20 participant-grouped nested CV, "
              f"participant bootstrap CIs (2,000). Exploratory; descriptive power only. Runs: " + "; ".join(runs) + ".")

    def block(title, df):
        md.append(f"\n### {title}\n")
        cols = list(df.columns)
        md.append("| " + " | ".join(cols) + " |")
        md.append("|" + "|".join("---" for _ in cols) + "|")
        for _, r in df.iterrows():
            md.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    block("Table 1. Discrimination and calibration on the matched set", pd.DataFrame(rows))
    block("Table 2. Operating points, ridge", pd.DataFrame(ops))
    block("Table 3. Paired AUROC differences", pd.DataFrame(cmp_rows))
    pm, l, h = summ["permutation"], summ["lrt_BGE_vs_BG"], summ["holm_provisional"]
    md.append("\n### Table 4. Tests of the EEG block (BGE vs BG)\n")
    md.append("| Test | Value |\n|---|---|")
    md.append(f"| Participant-block permutation of the EEG block (CV AUROC of BGE; {pm['B']} permutations) | observed {pm['observed_auc_BGE']:.3f}; permuted mean {pm['perm_auc_mean']:.3f}, 95th percentile {pm['perm_auc_q95']:.3f}; p = {pm['p']:.3f} ({pm['participants_permuted']} participants permuted, {pm['participants_left_in_place']} left in place) |")
    md.append(f"| 17-df likelihood-ratio test (descriptive only; 70 events) | chi-square {l['stat']:.2f}, p = {l['p']:.3f}; random-intercept SD {l['sigma_red']:.2f} without EEG, {l['sigma_full']:.4f} with EEG |")
    md.append("| Provisional Holm upper bounds (family S1, S2, S5, S6) | " + "; ".join(f"{k}: p {v['p']:.3f} -> {v['holm_adjusted_upper_bound']:.3f}" for k, v in h.items()) + " |")
    text = "\n".join(md) + "\n"
    (results / "master_table_gate4.md").write_text(text, encoding="utf-8")
    return text

if __name__ == "__main__":
    print(build())
    print(build_gate4())
