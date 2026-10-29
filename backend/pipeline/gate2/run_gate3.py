"""Gate 3: the pre-specified model grid (Protocol v1 sections 4-7) on B0, B, G, B+G, plus S1, S2 and the exploratory
S8, with registry rows for every run. The master table is generated separately by master_table.py from the registry.

  python -m backend.pipeline.gate2.run_gate3 grid        # ridge / RF / HGB x {B0, B, G, BG}, S8
  python -m backend.pipeline.gate2.run_gate3 secondary   # S1 and S2 (ridge): LRT, CV, permutation, provisional Holm
"""
import json
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from . import benchmark as bm
from . import mixed_logit as ml
from .build_t1_table import build_table
from .cv import Transformer, permute_gaze_blocks
from .early_window import build_early_features
from .registry import register

N_JOBS = 24
LOG1P = None


def _models(cfg, names=("B0", "B", "G", "BG")):
    return {n: bm.set_columns(cfg, n) for n in names}


def _stack(results, models):
    return {m: dict(oof=np.array([r[m]["oof"] for r in results]), pa=np.array([r[m]["pa"] for r in results]),
                    pb=np.array([r[m]["pb"] for r in results])) for m in models}


def run_cv(df, models, learner, cfg, with_const=False, n_jobs=N_JOBS):
    R = len(cfg["claim_b"]["repeat_seeds"])
    res = Parallel(n_jobs=n_jobs)(delayed(bm.run_repeat)(df, models, learner, cfg, r, cfg["features"]["log1p_counts"], with_const) for r in range(R))
    names = list(models) + (["CONST"] if with_const else [])
    return _stack(res, names), [c for r in res for m in models for c in r[m]["chosen"]]


def _perm_auc(i, df, models, learner, cfg, gaze_cols, seed):
    rng = np.random.default_rng(seed + 10_000 + i)
    dp, _, _ = permute_gaze_blocks(df, gaze_cols, ["incident_mode", "period"], rng)
    R = len(cfg["claim_b"]["repeat_seeds"])
    res = [bm.run_repeat(dp, models, learner, cfg, r, cfg["features"]["log1p_counts"]) for r in range(R)]
    P = np.array([r["G" if "G" in models else list(models)[0]]["oof"] for r in res])
    return float(bm.metrics_for(dp["y"].to_numpy(float), P)[0][0])


def lrt_generic(T, cols_red, cols_full, log1p):
    y, g, off = T["y"].to_numpy(float), T["participant_id"].to_numpy(), T["offset"].to_numpy(float)
    Xr = Transformer(cols_red, log1p).fit(T).transform(T)
    Xf = Transformer(cols_full, log1p).fit(T).transform(T)
    red, full = ml.fit_mixed_logit(y, Xr, g, off), ml.fit_mixed_logit(y, Xf, g, off)
    out = ml.likelihood_ratio_test(full.loglik, red.loglik, Xf.shape[1] - Xr.shape[1])
    out.update(sigma_red=red.sigma, sigma_full=full.sigma, sigma_at_lower_bound=bool(full.at_sigma_lower_bound))
    return out


def holm_provisional(pvals, family_size):
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    out, prev = {}, 0.0
    for rank, (k, p) in enumerate(items):
        adj = min(1.0, max(prev, (family_size - rank) * p))
        out[k] = dict(p=p, holm_adjusted_upper_bound=adj)
        prev = adj
    return out


# ---------------------------------------------------------------------------------------------------
def stage_grid(cfg, T_all, table_path):
    T = T_all[T_all.eligible_primary].reset_index(drop=True)
    y, pid = T["y"].to_numpy(float), T["participant_id"].to_numpy()
    B, seed = cfg["claim_b"]["bootstrap_resamples"], cfg["claim_b"]["bootstrap_seed"]
    all_draws, summaries, ids = {}, {}, {}
    for learner in ("ridge", "rf", "hgb"):
        models = _models(cfg)
        runs, chosen = run_cv(T, models, learner, cfg, with_const=(learner == "ridge"))
        pt, ci, draws = bm.evaluate(y, pid, runs, B, seed, cfg["g3"]["calibration"]["n_bins"])
        all_draws[learner] = draws
        pairs = {"BG_minus_B": ("BG", "B"), "G_minus_B0": ("G", "B0"), "B_minus_B0": ("B", "B0"), "BG_minus_B0": ("BG", "B0")}
        comp = {k: {met: bm.paired(draws, a, b, met) for met in ("auroc", "brier")} for k, (a, b) in pairs.items()}
        ch = pd.DataFrame(chosen)
        hp_cols = [c for c in ch.columns if c not in ("repeat", "fold", "model")]
        ch["hp"] = ch[hp_cols].astype(str).agg(", ".join, axis=1) if hp_cols else ""
        chosen_counts = ch.groupby(["model", "hp"]).size().unstack(fill_value=0).to_dict("index")
        metrics = dict(n_rows=len(T), n_participants=int(T.participant_id.nunique()), n_events=int(T.y.sum()), point=pt, ci=ci,
                       paired=comp, chosen_hyperparameters=chosen_counts, learner=learner)
        eid, run = register(cfg, f"g3_grid_{learner}", "5x20 repeated participant-grouped nested CV; operating points from inner validation predictions",
                            cfg["claim_b"]["repeat_seeds"], learner, dict(grid=bm.hp_grid(learner, cfg["g3"]), config=cfg["g3"]["_path"]), metrics,
                            table_path, notes="Gate 3 model grid on B0, B, G, BG (T1 primary set)")
        art = run / "artifacts"
        art.mkdir()
        for m, d in runs.items():
            np.save(art / f"oof_{m}.npy", d["oof"])
        ids[learner] = eid
        summaries[learner] = dict(point={m: {k: v for k, v in p.items() if k != "reliability"} for m, p in pt.items()}, comp=comp)
        print(learner, eid, flush=True)
    # exploratory S8: tree models vs ridge, paired bootstrap, Benjamini-Hochberg across the 8 comparisons
    rows = []
    for other in ("rf", "hgb"):
        for s in ("B0", "B", "G", "BG"):
            d = all_draws[other][s]["auroc"] - all_draws["ridge"][s]["auroc"]
            p = float(min(1.0, 2 * min(np.mean(d <= 0), np.mean(d >= 0))))
            rows.append(dict(comparison=f"{other}_minus_ridge", set=s, delta_auroc=float(np.mean(d)), ci=[float(np.quantile(d, .025)), float(np.quantile(d, .975))], p_boot=p))
    ps = np.array([r["p_boot"] for r in rows])
    order = np.argsort(ps)
    m = len(ps)
    bh = np.empty(m)
    run_min = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        run_min = min(run_min, ps[i] * m / (rank + 1))
        bh[i] = run_min
    for r, q in zip(rows, bh):
        r["fdr_bh"] = float(q)
    # challenger criterion (Protocol section 5, item 5): did any pre-specified model beat B0 with CI above 0?
    beat = any(summaries[l]["comp"][k]["auroc"]["ci"][0] > 0 for l in summaries for k in ("G_minus_B0", "B_minus_B0", "BG_minus_B0"))
    eid, run = register(cfg, "g3_exploratory_S8", "paired bootstrap of the grid runs (same participant resamples)", cfg["claim_b"]["bootstrap_seed"],
                        "rf and hgb vs ridge", dict(family="Benjamini-Hochberg over 8 comparisons"),
                        dict(comparisons=rows, any_prespecified_model_beats_B0_with_ci_above_zero=bool(beat),
                             challenger_boosting="not run: no pre-specified model beat B0" if not beat else "criterion met; to be proposed separately"),
                        table_path, notes="Exploratory S8")
    print("S8", eid, "challenger criterion met:", beat)
    return summaries


def stage_secondary(cfg, T_all, table_path):
    log1p = cfg["features"]["log1p_counts"]
    T = T_all[T_all.eligible_primary].reset_index(drop=True)
    B, seed = cfg["claim_b"]["bootstrap_resamples"], cfg["claim_b"]["bootstrap_seed"]
    nperm = cfg["g3"]["permutations"]["cv"]
    pseed = cfg["g3"]["permutations"]["seed"]
    gaze = cfg["features"]["gaze"]
    out = {}
    # ---- S1: G alone vs exposure baseline (ridge)
    models = _models(cfg, ("B0", "G"))
    runs, _ = run_cv(T, models, "ridge", cfg)
    pt, ci, draws = bm.evaluate(T["y"].to_numpy(float), T["participant_id"].to_numpy(), runs, B, seed)
    perm = np.array(Parallel(n_jobs=N_JOBS)(delayed(_perm_auc)(i, T, {"G": models["G"]}, "ridge", cfg, gaze, pseed) for i in range(nperm)))
    obs = pt["G"]["auroc"]
    lrt = lrt_generic(T, models["B0"], models["G"], log1p)
    out["S1"] = dict(n_rows=len(T), n_participants=int(T.participant_id.nunique()), n_events=int(T.y.sum()), lrt=lrt,
                     auroc_G=pt["G"]["auroc"], auroc_G_ci=ci["G"]["auroc"], auroc_B0=pt["B0"]["auroc"], auroc_B0_ci=ci["B0"]["auroc"],
                     delta_auroc=bm.paired(draws, "G", "B0"), permutation=dict(B=nperm, p=float((1 + np.sum(perm >= obs)) / (1 + nperm)),
                                                                           perm_auc_mean=float(perm.mean()), perm_auc_q95=float(np.quantile(perm, .95))))
    # ---- S2: early-window features (ridge)
    E = build_early_features(T_all, cfg["paths_resolved"]["raw_data_dir"], cfg["g3"]["secondary"]["S2"]["window_seconds"],
                             cfg["g3"]["secondary"]["S2"]["min_window_s"])
    idx = T_all.index[T_all.eligible_primary & E["early_ok"]]
    T2 = T_all.loc[idx].copy().reset_index(drop=True)
    for c in gaze:
        T2[c] = E.loc[idx, c].to_numpy()
    T2["ai_help_early"] = E.loc[idx, "ai_help_early"].to_numpy()
    f = cfg["features"]
    base = f["exposure"] + f["design"]
    models2 = {"B0": base, "BE": base + ["ai_help_early", "trial_index"], "BGE": base + ["ai_help_early", "trial_index"] + gaze}
    runs2, _ = run_cv(T2, models2, "ridge", cfg)
    pt2, ci2, draws2 = bm.evaluate(T2["y"].to_numpy(float), T2["participant_id"].to_numpy(), runs2, B, seed)
    perm2 = np.array(Parallel(n_jobs=N_JOBS)(delayed(_perm_auc)(i, T2, {"G": models2["BGE"]}, "ridge", cfg, gaze, pseed + 1) for i in range(nperm)))
    obs2 = pt2["BGE"]["auroc"]
    lrt2 = lrt_generic(T2, models2["BE"], models2["BGE"], log1p)
    out["S2"] = dict(n_rows=len(T2), n_participants=int(T2.participant_id.nunique()), n_events=int(T2.y.sum()), rows_lost_vs_primary=int(len(T) - len(T2)),
                     lrt=lrt2, auroc={m: dict(point=pt2[m]["auroc"], ci=ci2[m]["auroc"]) for m in models2},
                     delta_auroc_BGE_minus_BE=bm.paired(draws2, "BGE", "BE"), permutation=dict(B=nperm, p=float((1 + np.sum(perm2 >= obs2)) / (1 + nperm)),
                                                                                         perm_auc_mean=float(perm2.mean()), perm_auc_q95=float(np.quantile(perm2, .95))),
                     early_window_s=cfg["g3"]["secondary"]["S2"]["window_seconds"])
    out["holm_provisional"] = holm_provisional({"S1": out["S1"]["lrt"]["p"], "S2": out["S2"]["lrt"]["p"]}, len(cfg["g3"]["secondary"]["holm_family"]))
    out["holm_note"] = "family {S1,S2,S5,S6}; S5 and S6 run in later gates, so these are upper bounds at family size 4"
    t2path = table_path.parent / "analysis_table_s2.csv"
    T2.to_csv(t2path, index=False)
    for nm, key in (("S1", "S1"), ("S2", "S2")):
        register(cfg, f"g3_secondary_{nm}", "5x20 repeated participant-grouped nested CV", cfg["claim_b"]["repeat_seeds"], "ridge logistic with offset",
                 dict(config=cfg["g3"]["_path"]), dict(**out[key], holm=out["holm_provisional"].get(nm), holm_note=out["holm_note"]),
                 table_path if nm == "S1" else t2path, notes=cfg["g3"]["secondary"][nm]["description"])
    return out


def main(step):
    cfg = bm.load_gate3()
    outdir = cfg["paths_resolved"]["results_dir"] / "_tables"
    outdir.mkdir(parents=True, exist_ok=True)
    T_all = build_table(cfg)
    table_path = outdir / "analysis_table_t1.csv"
    T_all.to_csv(table_path, index=False)
    if step == "grid":
        print(json.dumps(stage_grid(cfg, T_all, table_path), indent=1, default=float))
    elif step == "secondary":
        print(json.dumps(stage_secondary(cfg, T_all, table_path), indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1])
