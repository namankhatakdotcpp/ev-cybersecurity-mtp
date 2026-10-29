"""Gate 4: S6 (EEG, exploratory) on the matched set plus the selection-bias report.

  python -m backend.pipeline.gate2.run_gate4 selection   # selection-bias report (generated Markdown + registry row)
  python -m backend.pipeline.gate2.run_gate4 s6          # B0 / B / BG / BGE on identical rows, ridge primary, trees exploratory
"""
import glob
import json
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from . import benchmark as bm
from .matched import build_matched, load_gate4, set_columns4
from .registry import register
from .run_gate3 import N_JOBS, _perm_auc, holm_provisional, lrt_generic, run_cv
from .selection_bias import run as sb_run, to_markdown


def _gate3_p(cfg, name):
    f = sorted(glob.glob(str(cfg["paths_resolved"]["results_dir"] / f"g3_secondary_{name}_*" / "summary.json")))[-1]
    return json.load(open(f))["metrics"]["lrt"]["p"]


def stage_selection(cfg, T_all, primary, matched, table_path):
    out = sb_run(cfg, T_all, primary, matched)
    md = to_markdown(out)
    results = cfg["paths_resolved"]["results_dir"]
    eid, run = register(cfg, "g4_selection_bias", "descriptive comparison (no model)", cfg["g4"]["matched_set"]["expected"], "none", dict(config="configs/gate4_eeg.yaml"),
                        out, table_path, notes="Gate 4 selection-bias report")
    (results / "selection_bias_gate4.md").write_text(md, encoding="utf-8")
    print(eid)
    print(md)


def stage_s6(cfg, matched, table_path):
    log1p = cfg["features"]["log1p_counts"]
    eeg = cfg["g4"]["matched_set"]["eeg_features"]
    sets = ["B0", "B", "BG", "BGE"]
    models = {s: set_columns4(cfg, s) for s in sets}
    y, pid = matched["y"].to_numpy(float), matched["participant_id"].to_numpy()
    B, seed = cfg["claim_b"]["bootstrap_resamples"], cfg["claim_b"]["bootstrap_seed"]
    s6 = cfg["g4"]["s6"]
    all_out, ids = {}, {}
    for learner in [s6["learners"]["primary"]] + s6["learners"]["exploratory"]:
        runs, chosen = run_cv(matched, models, learner, cfg, with_const=(learner == "ridge"))
        pt, ci, draws = bm.evaluate(y, pid, runs, B, seed, cfg["g3"]["calibration"]["n_bins"])
        pairs = [tuple(s6["primary_contrast"])] + [tuple(p) for p in s6["other_contrasts"]]
        comp = {f"{a}_minus_{b}": {met: bm.paired(draws, a, b, met) for met in ("auroc", "brier")} for a, b in pairs}
        ch = pd.DataFrame(chosen)
        hp_cols = [c for c in ch.columns if c not in ("repeat", "fold", "model")]
        ch["hp"] = ch[hp_cols].astype(str).agg(", ".join, axis=1)
        metrics = dict(learner=learner, n_rows=len(matched), n_participants=int(matched.participant_id.nunique()), n_events=int(matched.y.sum()),
                       point=pt, ci=ci, paired=comp, chosen_hyperparameters=ch.groupby(["model", "hp"]).size().unstack(fill_value=0).to_dict("index"))
        extra = {}
        if learner == "ridge":
            lrt = lrt_generic(matched, models["BG"], models["BGE"], log1p)
            lrt["note"] = "descriptive only: 17 df on 70 events"
            nperm = s6["permutation"]["B"]
            perm = np.array(Parallel(n_jobs=N_JOBS)(delayed(_perm_auc)(i, matched, {"G": models["BGE"]}, "ridge", cfg, eeg, s6["permutation"]["seed"]) for i in range(nperm)))
            obs = pt["BGE"]["auroc"]
            from .cv import permute_gaze_blocks
            _, moved, fixed = permute_gaze_blocks(matched, eeg, ["incident_mode", "period"], np.random.default_rng(0))
            extra = dict(lrt_BGE_vs_BG=lrt, permutation=dict(B=nperm, observed_auc_BGE=obs, p=float((1 + np.sum(perm >= obs)) / (1 + nperm)),
                                                             perm_auc_mean=float(perm.mean()), perm_auc_q95=float(np.quantile(perm, 0.95)),
                                                             participants_permuted=int(moved), participants_left_in_place=int(fixed)))
            p_s1, p_s2 = _gate3_p(cfg, "S1"), _gate3_p(cfg, "S2")
            extra["holm_provisional"] = holm_provisional({"S1": p_s1, "S2": p_s2, "S6": lrt["p"]}, len(s6["holm_family"]))
            extra["holm_note"] = "family {S1,S2,S5,S6}; S5 pending, so these are upper bounds at family size 4; S6 enters with its descriptive LRT p-value"
        metrics.update(extra)
        eid, run = register(cfg, f"g4_s6_{learner}", "5x20 repeated participant-grouped nested CV on the matched EEG set", cfg["claim_b"]["repeat_seeds"], learner,
                            dict(config="configs/gate4_eeg.yaml", grid=bm.hp_grid(learner, cfg["g3"])), metrics, table_path,
                            notes="S6 (exploratory): B0, B, BG, BGE on identical rows" + ("" if learner == "ridge" else " (exploratory learner)"))
        art = run / "artifacts"
        art.mkdir()
        for m, d in runs.items():
            np.save(art / f"oof_{m}.npy", d["oof"])
        ids[learner] = eid
        all_out[learner] = dict(point={m: {k: v for k, v in p.items() if k != "reliability"} for m, p in pt.items()}, paired=comp, **extra)
        print(learner, eid, flush=True)
    print(json.dumps(all_out["ridge"], indent=1, default=float))
    return all_out


def main(step):
    cfg = load_gate4()
    outdir = cfg["paths_resolved"]["results_dir"] / "_tables"
    outdir.mkdir(parents=True, exist_ok=True)
    T_all, primary, matched = build_matched(cfg)
    path = outdir / "analysis_table_matched_eeg.csv"
    matched.to_csv(path, index=False)
    if step == "selection":
        stage_selection(cfg, T_all, primary, matched, path)
    elif step == "s6":
        stage_s6(cfg, matched, path)


if __name__ == "__main__":
    main(sys.argv[1])
