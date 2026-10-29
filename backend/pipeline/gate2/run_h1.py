"""Gate 2: run hypothesis H1 of Protocol v1 (B + exposure vs B + G + exposure) exactly as specified.

  python -m backend.pipeline.gate2.run_h1 claim_a      # LRT (primary), permutation, sensitivity analyses
  python -m backend.pipeline.gate2.run_h1 claim_b      # nested grouped CV, bootstrap, permutation

Every analysis writes a registry row and a run folder; nothing existing is overwritten.
"""
import json
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from joblib import Parallel, delayed
from scipy.stats import chi2, norm

from . import cv
from . import mixed_logit as ml
from .build_t1_table import build_table, count_valid_gaze_samples
from .config import load_config
from .registry import register

N_JOBS = 24


def columns(cfg):
    f = cfg["features"]
    red = f["exposure"] + f["design"]
    return dict(B0=red, B=red + f["behaviour"], BG=red + f["behaviour"] + f["gaze"], gaze=f["gaze"], log1p=f["log1p_counts"])


# ---------------------------------------------------------------------------------------------------
# Claim A helpers
# ---------------------------------------------------------------------------------------------------
def design(df, cols, log1p):
    return cv.Transformer(cols, log1p).fit(df).transform(df)


def lrt_fit(T, cols, nodes=21, extra_full=None, extra_red=None):
    """Mixed full vs reduced fit on rows T; returns dict with LRT, sigma, coefficients."""
    y = T["y"].to_numpy(float)
    g = T["participant_id"].to_numpy()
    off = T["offset"].to_numpy(float)
    Xr = design(T, cols["B"], cols["log1p"])
    Xf = design(T, cols["BG"], cols["log1p"])
    if extra_red is not None:
        Xr = np.c_[Xr, extra_red]
    if extra_full is not None:
        Xf = np.c_[Xf, extra_full]
    red = ml.fit_mixed_logit(y, Xr, g, off, n_nodes=nodes)
    full = ml.fit_mixed_logit(y, Xf, g, off, n_nodes=nodes)
    df_ = Xf.shape[1] - Xr.shape[1]
    return red, full, ml.likelihood_ratio_test(full.loglik, red.loglik, df_), Xr, Xf


def summarize_set(T, cols, nodes=21):
    red, full, lrt, Xr, Xf = lrt_fit(T, cols, nodes)
    return dict(n_rows=len(T), n_participants=int(T.participant_id.nunique()), n_events=int(T.y.sum()), df=lrt["df"], lrt_stat=lrt["stat"],
                p=lrt["p"], sigma_red=red.sigma, sigma_full=full.sigma, converged=bool(red.converged and full.converged),
                sigma_at_lower_bound=bool(full.at_sigma_lower_bound), loglik_full=full.loglik, loglik_red=red.loglik)


def _perm_lrt(i, T, cols, seed, ll_red):
    rng = np.random.default_rng(seed + i)
    Tp, moved, fixed = cv.permute_gaze_blocks(T, cols["gaze"], ["incident_mode", "period"], rng)
    Xf = design(Tp, cols["BG"], cols["log1p"])
    full = ml.fit_mixed_logit(Tp["y"].to_numpy(float), Xf, Tp["participant_id"].to_numpy(), Tp["offset"].to_numpy(float))
    return 2 * (full.loglik - ll_red), moved, fixed


def claim_a(cfg, table_path, T_all):
    cols = columns(cfg)
    T = T_all[T_all.eligible_primary].reset_index(drop=True)
    out = {}
    red, full, lrt, Xr, Xf = lrt_fit(T, cols, cfg["claim_a"]["n_nodes"])
    names = ["intercept"] + cols["BG"]
    se = np.sqrt(np.diag(full.cov_coef))
    coef = pd.DataFrame(dict(term=names, beta=full.coef, se=se, z=full.coef / se, p_wald=2 * norm.sf(np.abs(full.coef / se)),
                             or_per_unit=np.exp(full.coef)))
    out["primary"] = dict(n_rows=len(T), n_participants=int(T.participant_id.nunique()), n_events=int(T.y.sum()), lrt=lrt,
                          sigma_full=full.sigma, sigma_red=red.sigma, icc_latent=float(full.sigma ** 2 / (full.sigma ** 2 + np.pi ** 2 / 3)),
                          sigma_at_lower_bound=bool(full.at_sigma_lower_bound), converged=bool(full.converged and red.converged),
                          loglik_full=full.loglik, loglik_red=red.loglik, coefficients=coef.round(4).to_dict("records"))
    # robustness: node count, ordinary logistic, clustered-robust Wald, statsmodels cross-check
    r41, f41, l41, _, _ = lrt_fit(T, cols, 41)
    out["nodes_41"] = dict(lrt=l41, sigma_full=f41.sigma)
    y, g, off = T.y.to_numpy(float), T.participant_id.to_numpy(), T.offset.to_numpy(float)
    of, orr = ml.fit_logit(y, Xf, off), ml.fit_logit(y, Xr, off)
    lo = ml.likelihood_ratio_test(of.loglik, orr.loglik, 6)
    rob = ml.cluster_robust_cov(y, Xf, off, of, g)
    bg = of.coef[-6:]
    wald = float(bg @ np.linalg.inv(rob[-6:, -6:]) @ bg)
    ref = sm.GLM(y, Xf, family=sm.families.Binomial(), offset=off).fit()
    out["ordinary_logit"] = dict(lrt=lo, robust_wald_stat=wald, robust_wald_p=float(chi2.sf(wald, 6)),
                                 max_abs_coef_diff_vs_statsmodels=float(np.max(np.abs(of.coef - ref.params))))
    # within / between decomposition
    Zg = cv.Transformer(cols["gaze"], cols["log1p"]).fit(T).transform(T)[:, 1:]
    pm = pd.DataFrame(Zg).groupby(T.participant_id.values).transform("mean").to_numpy()
    wi = Zg - pm
    Xr0 = Xr
    m_red = ml.fit_mixed_logit(y, Xr0, g, off)
    m_between = ml.fit_mixed_logit(y, np.c_[Xr0, pm], g, off)
    m_within = ml.fit_mixed_logit(y, np.c_[Xr0, wi], g, off)
    m_both = ml.fit_mixed_logit(y, np.c_[Xr0, wi, pm], g, off)
    out["within_between"] = dict(
        both_vs_reduced_12df=ml.likelihood_ratio_test(m_both.loglik, m_red.loglik, 12),
        within_given_between_6df=ml.likelihood_ratio_test(m_both.loglik, m_between.loglik, 6),
        between_given_within_6df=ml.likelihood_ratio_test(m_both.loglik, m_within.loglik, 6))
    # permutation LRT (participant-block, Protocol section 4)
    B = cfg["claim_b"]["permutation_lrt"]
    res = Parallel(n_jobs=N_JOBS)(delayed(_perm_lrt)(i, T, cols, cfg["claim_b"]["permutation_seed"], red.loglik) for i in range(B))
    stats = np.array([r[0] for r in res])
    moved, fixed = res[0][1], res[0][2]
    out["permutation_lrt"] = dict(B=B, observed_stat=lrt["stat"], p=float((1 + np.sum(stats >= lrt["stat"])) / (1 + B)),
                                  perm_stat_mean=float(stats.mean()), perm_stat_q95=float(np.quantile(stats, 0.95)),
                                  participants_permuted=int(moved), participants_left_in_place=int(fixed))
    # sensitivity analyses
    sens = {}
    sens["E2_drop_duplicate_folder_participants"] = summarize_set(T[~T.dup_participant], cols)
    sens["S3_drop_rag_contaminated_sessions"] = summarize_set(T[~T.rag_contaminated], cols)
    vc = count_valid_gaze_samples(T_all, cfg["paths_resolved"]["raw_data_dir"])
    keep = vc.loc[T_all[T_all.eligible_primary].index] >= cfg["sensitivity"]["min_valid_gaze_samples"]
    S4 = T_all[T_all.eligible_primary][keep.values].reset_index(drop=True)
    sens["S4_at_least_200_valid_gaze_samples"] = summarize_set(S4, cols)
    sens["S4_valid_samples_median_in_window_all_primary"] = float(vc.loc[T_all[T_all.eligible_primary].index].median())
    out["sensitivity"] = sens
    return out, coef


# ---------------------------------------------------------------------------------------------------
# Claim B
# ---------------------------------------------------------------------------------------------------
def _perm_cv(i, T, cols, cfg_b, B_oof):
    rng = np.random.default_rng(cfg_b["permutation_seed"] + 10_000 + i)
    Tp, _, _ = cv.permute_gaze_blocks(T, cols["gaze"], ["incident_mode", "period"], rng)
    oof, _ = cv.cv_predictions(Tp, {"BG": cols["BG"]}, cols["log1p"], cfg_b)
    auc_bg = cv.metrics_for(Tp["y"].to_numpy(float), oof["BG"])[0][0]
    return float(auc_bg)


def claim_b(cfg, T_all):
    cols = columns(cfg)
    cb = cfg["claim_b"]
    T = T_all[T_all.eligible_primary].reset_index(drop=True)
    models = {"B0": cols["B0"], "B": cols["B"], "BG": cols["BG"]}
    oof, chosen = cv.cv_predictions(T, models, cols["log1p"], cb)
    y = T["y"].to_numpy(float)
    point = {m: dict(zip(("auroc", "ap", "brier"), [float(v[0]) for v in cv.metrics_for(y, P)])) for m, P in oof.items()}
    boot = cv.bootstrap(y, T["participant_id"].to_numpy(), oof, cb["bootstrap_resamples"], cb["bootstrap_seed"])
    ci = lambda a: [float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975))]
    res = {}
    for m in models:
        res[m] = dict(point[m], auroc_ci=ci(boot[m]["auroc"]), ap_ci=ci(boot[m]["ap"]), brier_ci=ci(boot[m]["brier"]))
    pairs = {"BG_minus_B": ("BG", "B"), "BG_minus_B0": ("BG", "B0"), "B_minus_B0": ("B", "B0")}
    delta = {}
    for k, (a, b) in pairs.items():
        d = boot[a]["auroc"] - boot[b]["auroc"]
        delta[k] = dict(point=point[a]["auroc"] - point[b]["auroc"], ci=ci(d), bootstrap_se=float(d.std()),
                        prop_boot_leq_0=float(np.mean(d <= 0)))
    # per-repeat spread of the headline difference
    per_rep = [cv.metrics_for(y, oof["BG"][r:r + 1])[0][0] - cv.metrics_for(y, oof["B"][r:r + 1])[0][0] for r in range(oof["B"].shape[0])]
    # participant-block permutation of the gaze block, full nested CV
    B_perm = cb["permutation_cv"]
    perm_auc = np.array(Parallel(n_jobs=N_JOBS)(delayed(_perm_cv)(i, T, cols, cb, oof["B"]) for i in range(B_perm)))
    obs = point["BG"]["auroc"]
    perm = dict(B=B_perm, observed_auc_BG=obs, auc_B=point["B"]["auroc"], p_auc_BG_ge_obs=float((1 + np.sum(perm_auc >= obs)) / (1 + B_perm)),
                perm_auc_BG_mean=float(perm_auc.mean()), perm_auc_BG_q95=float(np.quantile(perm_auc, 0.95)),
                perm_delta_mean=float((perm_auc - point["B"]["auroc"]).mean()))
    chosen_summary = chosen.groupby(["model", "C"]).size().unstack(fill_value=0).to_dict("index")
    return dict(n_rows=len(T), n_participants=int(T.participant_id.nunique()), n_events=int(T.y.sum()), metrics=res, delta_auroc=delta,
                per_repeat_delta_auroc=dict(mean=float(np.mean(per_rep)), sd=float(np.std(per_rep)), min=float(np.min(per_rep)),
                                            max=float(np.max(per_rep))),
                permutation=perm, chosen_C_counts=chosen_summary), oof, chosen


def main(step):
    cfg = load_config()
    outdir = cfg["paths_resolved"]["results_dir"] / "_tables"
    outdir.mkdir(parents=True, exist_ok=True)
    T_all = build_table(cfg)
    table_path = outdir / "analysis_table_t1.csv"
    T_all.to_csv(table_path, index=False)
    if step == "claim_a":
        out, coef = claim_a(cfg, table_path, T_all)
        eid, run = register(cfg, "h1_claim_a", "none (likelihood-ratio test on all primary rows)", cfg["claim_b"]["permutation_seed"],
                            "random-intercept logistic, Gauss-Hermite 21 nodes, offset logit(p_exp)", cfg["claim_a"], out, table_path,
                            notes="Claim A (primary inferential test), sensitivities E2/S3/S4, within/between, permutation LRT")
        coef.to_csv(run / "coefficients_full_model.csv", index=False)
        print(eid)
        print(json.dumps({k: v for k, v in out.items() if k != "primary"}, indent=1, default=float))
        p = dict(out["primary"])
        p.pop("coefficients")
        print(json.dumps(p, indent=1, default=float))
        print(coef.to_string(index=False))
    elif step == "claim_b":
        out, oof, chosen = claim_b(cfg, T_all)
        eid, run = register(cfg, "h1_claim_b", "5x20 repeated participant-grouped nested CV (stratified by participant event-rate tertile)",
                            cfg["claim_b"]["repeat_seeds"], "ridge logistic with offset (C grid, inner 3-fold log-loss)", cfg["claim_b"], out, table_path,
                            notes="Claim B companion estimate: paired delta AUROC B+G minus B, participant bootstrap, participant-block permutation")
        art = run / "artifacts"
        art.mkdir()
        for m, P in oof.items():
            np.save(art / f"oof_{m}.npy", P)
        chosen.to_csv(art / "chosen_C.csv", index=False)
        print(eid)
        print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1])
