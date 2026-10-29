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


if __name__ == "__main__":
    print(build())
