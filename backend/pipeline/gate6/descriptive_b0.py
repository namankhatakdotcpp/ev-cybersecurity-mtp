"""Reduced Gate 6: descriptive coefficients and error analysis for the exposure-only reference B0 (configs/gate6_descriptive.yaml, D072).
Exploratory and descriptive: no hypothesis test, no new model comparison, no SHAP or permutation importance.

  python -m backend.pipeline.gate6.descriptive_b0      # writes results/_tables/gate6_*.csv and results/gate6_tables.md
"""
import glob
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml
from sklearn.metrics import roc_auc_score

from ..gate2 import cv
from ..gate2 import mixed_logit as ml
from ..gate2.benchmark import load_gate3
from ..gate2.build_t1_table import build_table
from ..gate2.config import REPO_ROOT

COLS = ["n_available", "incident_mode", "period_jun", "period_jul_aug"]


def load():
    g6 = yaml.safe_load(open(REPO_ROOT / "configs" / "gate6_descriptive.yaml", encoding="utf-8"))
    cfg = load_gate3()
    T_all = build_table(cfg)
    T = T_all[T_all.eligible_primary].reset_index(drop=True)
    T["n_attacked"] = T["n_attacked"].astype(int)
    return g6, cfg, T


def fit_ridge(T, C):
    tr = cv.Transformer(COLS, []).fit(T)
    f = ml.fit_logit(T["y"].to_numpy(float), tr.transform(T), T["offset"].to_numpy(float), l2=1.0 / C, unpenalized=[0])
    return tr, f


def ridge_coefs(T, C):
    tr, f = fit_ridge(T, C)
    beta = np.asarray(f.coef, float)
    # back to raw units for n_available (z-scored in the model); binary columns are unscaled
    raw = beta[1:].copy()
    raw[0] = raw[0] / tr.sd[0]
    return dict(zip(COLS, raw)), float(beta[0] - (beta[1] * tr.mu[0] / tr.sd[0]))


def glm_fit(T, free_exposure=False):
    X = T[COLS].astype(float).copy()
    if free_exposure:
        X["logit_p_exp"] = T["offset"]
    X = sm.add_constant(X)
    off = None if free_exposure else T["offset"].to_numpy(float)
    return sm.GLM(T["y"].to_numpy(float), X, family=sm.families.Binomial(), offset=off).fit(cov_type="cluster", cov_kwds={"groups": T["participant_id"].to_numpy()})


def boot_idx(pid, B, seed):
    rng = np.random.default_rng(seed)
    uniq, inv = np.unique(pid, return_inverse=True)
    counts = np.stack([np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq)) for _ in range(B)])
    return counts[:, inv]            # B x n row multiplicities


def coefficients(T, g6):
    C, scores = cv.select_C(T, COLS, [], g6["C_grid"] if "C_grid" in g6 else [0.01, 0.1, 1.0, 10.0], 3, 5000)
    B, seed = g6["bootstrap"]["resamples"], g6["bootstrap"]["seed"]
    rows = []
    ridge, icpt = ridge_coefs(T, C)
    g = glm_fit(T)
    names = ["const"] + COLS
    gf = glm_fit(T, free_exposure=True)
    # participant bootstrap of both fits
    W = boot_idx(T["participant_id"].to_numpy(), B, seed)
    rng = np.random.default_rng(seed + 1)
    pids = T["participant_id"].to_numpy()
    uniq = np.unique(pids)
    by = {p: np.where(pids == p)[0] for p in uniq}
    r_draw, g_draw = [], []
    for b in range(B):
        pick = rng.integers(0, len(uniq), len(uniq))
        ix = np.concatenate([by[uniq[i]] for i in pick])
        Tb = T.iloc[ix].reset_index(drop=True)
        try:
            rc, ri = ridge_coefs(Tb, C)
            r_draw.append([ri] + [rc[c] for c in COLS])
        except Exception:
            pass
        try:
            gb = glm_fit(Tb)
            g_draw.append(gb.params.to_numpy())
        except Exception:
            pass
    r_draw, g_draw = np.array(r_draw), np.array(g_draw)
    for j, nm in enumerate(names):
        rl, rh = np.percentile(r_draw[:, j], [2.5, 97.5])
        gl, gh = np.percentile(g_draw[:, j], [2.5, 97.5])
        rows.append(dict(term=nm, ridge_C=C, ridge_coef=(icpt if j == 0 else ridge[nm]), ridge_lo=rl, ridge_hi=rh,
                         glm_coef=float(g.params.iloc[j]), glm_se_cluster=float(g.bse.iloc[j]), glm_lo=gl, glm_hi=gh,
                         glm_odds_ratio=float(np.exp(g.params.iloc[j])), glm_or_lo=float(np.exp(gl)), glm_or_hi=float(np.exp(gh))))
    free = dict(logit_p_exp_slope=float(gf.params["logit_p_exp"]), slope_se=float(gf.bse["logit_p_exp"]),
                lo=float(gf.params["logit_p_exp"] - 1.96 * gf.bse["logit_p_exp"]), hi=float(gf.params["logit_p_exp"] + 1.96 * gf.bse["logit_p_exp"]))
    return pd.DataFrame(rows), free, dict(C=C, inner_scores=[float(s) for s in scores], bootstrap_ok=dict(ridge=len(r_draw), glm=len(g_draw)))


def strata_masks(T, g6):
    out = []
    for v in sorted(T["n_attacked"].unique()):
        out.append(("n_attacked", str(v), (T["n_attacked"] == v).to_numpy()))
    for v in sorted(T["n_available"].unique()):
        out.append(("n_available", str(v), (T["n_available"] == v).to_numpy()))
    for (a, n), g in T.groupby(["n_attacked", "n_available"]):
        out.append(("exposure_cell", f"{a} of {n} attacked", ((T["n_attacked"] == a) & (T["n_available"] == n)).to_numpy()))
    for lo, hi in g6["strata"]["trial_index_bins"]:
        out.append(("trial_index", f"{lo}-{hi}", T["trial_index"].between(lo, hi).to_numpy()))
    for v in g6["strata"]["period"]:
        out.append(("collection_period", v, (T["period"] == v).to_numpy()))
    for v in g6["strata"]["incident_mode"]:
        out.append(("incident_mode", str(v), (T["incident_mode"] == v).to_numpy()))
    out.append(("all", "primary set", np.ones(len(T), bool)))
    return out


def error_table(T, g6, oof):
    y = T["y"].to_numpy(float)
    p_b0 = oof.mean(0)
    p_exp = T["p_exp"].to_numpy(float)
    W = boot_idx(T["participant_id"].to_numpy(), g6["bootstrap"]["resamples"], g6["bootstrap"]["seed"] + 2)
    mev = g6["min_events_for_stratum_auroc"]
    rows = []
    for fam, lab, m in strata_masks(T, g6):
        Wm = W * m[None, :]
        den = Wm.sum(1)
        ok = den > 0
        obs_b = (Wm @ y)[ok] / den[ok]
        pred_b = (Wm @ p_b0)[ok] / den[ok]
        pe_b = (Wm @ p_exp)[ok] / den[ok]
        d_pred = obs_b - pred_b
        d_exp = obs_b - pe_b
        n, ev = int(m.sum()), int(y[m].sum())
        auc = [roc_auc_score(y[m], oof[r][m]) for r in range(oof.shape[0])] if (ev >= mev and n - ev >= mev) else None
        brier = float(np.mean((p_b0[m] - y[m]) ** 2))
        brier_exp = float(np.mean((p_exp[m] - y[m]) ** 2))
        rows.append(dict(family=fam, stratum=lab, rows=n, participants=int(T.loc[m, "participant_id"].nunique()), events=ev, observed=float(y[m].mean()), mean_B0_pred=float(p_b0[m].mean()),
                         mean_exposure=float(p_exp[m].mean()), obs_minus_B0=float((y[m] - p_b0[m]).mean()), obs_minus_B0_lo=float(np.percentile(d_pred, 2.5)), obs_minus_B0_hi=float(np.percentile(d_pred, 97.5)),
                         obs_minus_exposure=float((y[m] - p_exp[m]).mean()), obs_minus_exposure_lo=float(np.percentile(d_exp, 2.5)), obs_minus_exposure_hi=float(np.percentile(d_exp, 97.5)),
                         brier_B0=brier, brier_exposure_only=brier_exp, auroc_B0=(float(np.mean(auc)) if auc else np.nan)))
    return pd.DataFrame(rows)


def main():
    g6, cfg, T = load()
    tdir = REPO_ROOT / "results" / "_tables"
    tdir.mkdir(exist_ok=True)
    f = glob.glob(str(REPO_ROOT / "results" / "g3_grid_ridge_*" / "artifacts" / "oof_B0.npy"))
    assert len(f) == 1, f
    oof = np.load(f[0])
    assert oof.shape[1] == len(T)
    coef, free, meta = coefficients(T, g6)
    err = error_table(T, g6, oof)
    coef.to_csv(tdir / "gate6_b0_coefficients.csv", index=False)
    err.to_csv(tdir / "gate6_b0_error_by_stratum.csv", index=False)
    a = err[err.family == "all"].iloc[0]
    meta.update(free_exposure_slope=free, n_rows=len(T), n_participants=int(T.participant_id.nunique()), n_events=int(T.y.sum()), oof_source=f[0].replace("\\", "/").split("/results/")[-1],
                oof_B0_auroc_mean_over_repeats=a.auroc_B0, bootstrap=g6["bootstrap"])
    (REPO_ROOT / "results" / "gate6_meta.json").write_text(json.dumps(meta, indent=1))
    # markdown tables (generated)
    md = ["# Gate 6 (reduced): B0 descriptive tables (generated; do not edit by hand)", "",
          f"Primary set: {len(T)} rows, {meta['n_participants']} participants, {meta['n_events']} events. B0 = exposure offset + n_available + incident_mode + period dummies. "
          f"Final-fit ridge C = {meta['C']} (same inner rule as Gate 2/3, selected on all rows). Intervals are 2.5th/97.5th percentiles of a participant bootstrap ({g6['bootstrap']['resamples']} resamples); "
          "descriptive only, no test.", "",
          "## Coefficients (log-odds of choosing an attacked kiosk; the exposure offset enters with coefficient 1 by construction)", "",
          "| Term | Ridge coef. [95% CI] | Unpenalised coef. (cluster SE) | Odds ratio [95% CI] |", "|---|---|---|---|"]
    for _, r in coef.iterrows():
        md.append(f"| {r.term} | {r.ridge_coef:+.3f} [{r.ridge_lo:+.3f}, {r.ridge_hi:+.3f}] | {r.glm_coef:+.3f} ({r.glm_se_cluster:.3f}) | {r.glm_odds_ratio:.2f} [{r.glm_or_lo:.2f}, {r.glm_or_hi:.2f}] |")
    md += ["", f"n_available is per extra available kiosk (raw units). Free-slope check: if the logit of the exposure is entered as a covariate instead of an offset, its slope is {free['logit_p_exp_slope']:.2f} "
           f"(cluster 95% CI {free['lo']:.2f} to {free['hi']:.2f}); a slope of 1 means choice follows exposure as the offset assumes, 0 means choice ignores exposure.", "",
           "## Error analysis of the Gate 3 out-of-fold B0 predictions", "",
           "Observed minus B0 prediction and observed minus exposure (the rate expected from a random choice) with participant-bootstrap intervals; Brier score of B0 and of the exposure alone; "
           "within-stratum AUROC only with at least 20 events and 20 non-events.", "",
           "| Family | Stratum | Rows | Participants | Events | Observed | Mean B0 | Mean exposure | Obs - B0 [95% CI] | Obs - exposure [95% CI] | Brier B0 | Brier exposure | AUROC B0 |", "|" + "---|" * 13]
    for _, r in err.iterrows():
        md.append(f"| {r.family} | {r.stratum} | {r.rows} | {r.participants} | {r.events} | {r.observed:.3f} | {r.mean_B0_pred:.3f} | {r.mean_exposure:.3f} | "
                  f"{r.obs_minus_B0:+.3f} [{r.obs_minus_B0_lo:+.3f}, {r.obs_minus_B0_hi:+.3f}] | {r.obs_minus_exposure:+.3f} [{r.obs_minus_exposure_lo:+.3f}, {r.obs_minus_exposure_hi:+.3f}] | "
                  f"{r.brier_B0:.3f} | {r.brier_exposure_only:.3f} | {'n/a' if np.isnan(r.auroc_B0) else f'{r.auroc_B0:.3f}'} |")
    (REPO_ROOT / "results" / "gate6_tables.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("wrote results/gate6_tables.md")


if __name__ == "__main__":
    main()
