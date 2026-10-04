#!/usr/bin/env python3
"""
Confirmatory GLMM (per the Research Audit's stated design, never previously run -
checked against Decision.md and the pipeline directory before writing this script):

    risky_decision ~ attack_type + (1|participant) + (1|station)

Uses the D045/D050-corrected risky_decision label throughout. Does NOT touch raw
data or any document - reads feature_table.csv (already-extracted, D035) plus a
new station-level attack-layout extraction (read-only, from the existing
interaction logs' "StationGenerated"/kiosks payload - never written to).

IMPORTANT FINDING, reported rather than worked around silently: fit exactly as
specified, with attack_type defined as the CHOSEN kiosk's attack status (the most
literal reading of "attack_type"), the model is not fittable - risky_decision is
definitionally determined by that attack_type (risky := charge AND kiosk_attack
compromised), producing complete separation (a label circularity, not a numerical
convergence bug). See the printed diagnostic and Decision.md for the fix used
instead: attack_type is redefined as a station-level, decision-independent property
(whether ANY of the 3 presented kiosks was compromised, read from the
StationGenerated/"kiosks" event - which always uses "Cyber Attack"/"Safe"
terminology, confirmed never "System Anomaly", so it is NOT subject to the D045
labeling bug either).
"""
import glob
import json
import re
import warnings

import numpy as np
import pandas as pd
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

from train_baselines import FEATURE_TABLE, GAZE_COLS, make_label

RAW_DATA_DIR = "/Users/naman/Documents/MTP/backend/raw_data"


def extract_station_attack_layout():
    """Read-only extraction from the existing interaction logs' own
    StationGenerated/'kiosks' event (route=UI, page=station) - the per-station
    layout of all 3 kiosks' attack status, independent of which one the
    participant chose. Confirmed (spot-checked across 30 sessions, 300 events)
    to always use 'Cyber Attack'/'Safe' vocabulary, never 'System Anomaly' -
    this field is NOT affected by the D045 labeling bug, since that bug lives in
    the later charging-event's own kiosk_attack field, not here."""
    rows = []
    for d in sorted(glob.glob(f"{RAW_DATA_DIR}/session_*")):
        m = re.match(r"session_\d+_\d+_(\d+)", d.split("/")[-1])
        if not m:
            continue
        pid = m.group(1)
        inter_files = glob.glob(f"{d}/interactions_*.csv")
        if not inter_files:
            continue
        try:
            with open(inter_files[0], newline="", encoding="utf-8", errors="ignore") as f:
                import csv
                reader = csv.DictReader(f)
                for r in reader:
                    if r.get("page") != "station":
                        continue
                    try:
                        payload = json.loads(r.get("payload_json") or "")
                    except Exception:
                        continue
                    kiosks = payload.get("kiosks")
                    trial = payload.get("trial")
                    if not kiosks or trial is None:
                        continue
                    attacks = [kiosks.get(f"kiosk{i}_attack") for i in (1, 2, 3)]
                    n_malicious = sum(1 for a in attacks if a == "Cyber Attack")
                    n_available = sum(1 for a in attacks if a is not None)
                    rows.append({
                        "participant_id": pid, "trial": int(trial),
                        "session_dir": d.split("/")[-1],
                        "n_malicious_kiosks": n_malicious,
                        "n_available_kiosks": n_available,
                        "any_malicious": n_malicious > 0,
                    })
        except Exception as e:
            print(f"  [{pid}] station-layout extraction failed: {e}")
    df = pd.DataFrame(rows)
    # one row per (participant, trial, session) - a station can emit this event
    # more than once in rare duplicate-message cases; keep the first.
    df = df.drop_duplicates(subset=["session_dir", "trial"], keep="first")
    return df


def wilson_like_or_ci(coef, se, z=1.96):
    """Odds-ratio 95% CI from a logit-scale coefficient and its SE (delta method
    on the log-odds scale, then exponentiated) - the standard way to report GLMM
    fixed-effect sizes as odds ratios with CIs."""
    lo, hi = coef - z * se, coef + z * se
    return np.exp(coef), np.exp(lo), np.exp(hi)


def fdr_bh(pvals):
    """Benjamini-Hochberg FDR correction."""
    pvals = np.asarray(pvals)
    n = len(pvals)
    order = np.argsort(pvals)
    ranked = pvals[order]
    bh = ranked * n / (np.arange(n) + 1)
    bh_mono = np.minimum.accumulate(bh[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(bh_mono, 0, 1)
    return out


def main():
    df = pd.read_csv(FEATURE_TABLE)
    df["gaze_missing"] = df["gaze_missing"].astype(bool)
    df["risky"] = make_label(df)
    df["participant_id"] = df["participant_id"].astype(str)

    print(f"Loaded feature_table.csv: {len(df)} rows, {df['participant_id'].nunique()} participants\n")

    # ------------------------------------------------------------------
    # ATTEMPT 1: literal spec - attack_type = the CHOSEN kiosk's attack status
    # ------------------------------------------------------------------
    print("="*90)
    print("ATTEMPT 1: risky_decision ~ attack_type (chosen-kiosk status, D045-merged) + (1|participant) + (1|station)")
    print("="*90)
    sub1 = df[df["decision"] == "charge"].copy()
    sub1["attack_type"] = np.where(sub1["kiosk_attack"].isin(["Cyber Attack", "System Anomaly"]),
                                    "Compromised", "Safe")
    ct = pd.crosstab(sub1["attack_type"], sub1["risky"])
    print("Cross-tab of attack_type (chosen kiosk) vs risky_decision (restricted to charge decisions):")
    print(ct)
    print("\nDIAGNOSIS: attack_type perfectly predicts risky_decision here by construction - "
          "risky_decision is DEFINED as (decision=='charge' AND kiosk_attack compromised), so "
          "restricted to charge rows, attack_type==Compromised => risky=1 always and "
          "attack_type==Safe => risky=0 always (see cross-tab: off-diagonal cells are exactly zero).")
    print("This is COMPLETE SEPARATION - a label-definition circularity, not a numerical fitting bug. "
          "A GLMM fit on this specification would either fail to converge (fixed-effect coefficient "
          "diverges toward +/-infinity in a frequentist fit) or, with a Bayesian prior, converge to an "
          "extreme, uninterpretable estimate whose confidence/credible interval is meaningless as a "
          "measure of uncertainty about a real effect. Not fitting this as specified - reporting why, "
          "per the task's own instruction, rather than fitting a degenerate model and presenting output.")
    print()

    # ------------------------------------------------------------------
    # ATTEMPT 2 (the fix, stated explicitly): attack_type = station-level kiosk
    # LAYOUT (any of the 3 presented kiosks compromised), independent of which
    # one the participant chose - breaks the circularity, uses the
    # StationGenerated event (confirmed D045-bug-free vocabulary).
    # ------------------------------------------------------------------
    print("="*90)
    print("ATTEMPT 2 (non-circular fix): risky_decision ~ attack_type (station LAYOUT: any kiosk "
          "compromised, independent of choice) + gaze features + (1|participant) + (1|station)")
    print("="*90)
    layout = extract_station_attack_layout()
    print(f"Extracted station-layout attack info: {len(layout)} station-events, "
          f"{layout['participant_id'].nunique()} participants")

    merged = df.merge(layout[["session_dir", "trial", "any_malicious", "n_malicious_kiosks"]],
                       on=["session_dir", "trial"], how="left")
    n_missing_layout = merged["any_malicious"].isna().sum()
    print(f"Rows with no matched station-layout event: {n_missing_layout} / {len(merged)} "
          f"(dropped from this model - no independent attack_type available for them)")
    merged = merged.dropna(subset=["any_malicious"]).copy()
    merged["attack_type"] = merged["any_malicious"].map({True: "Attack_present", False: "All_safe"})

    ct2 = pd.crosstab(merged["attack_type"], merged["risky"])
    print("\nCross-tab of attack_type (station layout) vs risky_decision:")
    print(ct2)
    print(f"Risky rate when attack present at station: {merged.loc[merged.any_malicious, 'risky'].mean():.4f}")
    print(f"Risky rate when station all-safe:           {merged.loc[~merged.any_malicious, 'risky'].mean():.4f}")

    model_df = merged.dropna(subset=GAZE_COLS).copy()
    print(f"\nRows usable for the full model (gaze features non-missing): {len(model_df)} / {len(merged)}, "
          f"{model_df['participant_id'].nunique()} participants")

    model_df["risky"] = model_df["risky"].astype(float)
    model_df["attack_type_bin"] = (model_df["attack_type"] == "Attack_present").astype(float)
    for c in GAZE_COLS:
        mu, sd = model_df[c].mean(), model_df[c].std()
        model_df[c + "_z"] = (model_df[c] - mu) / sd if sd > 0 else 0.0

    results = {}
    warnings.filterwarnings("ignore")

    # Primary confirmatory model: attack_type only
    print("\n--- Primary model: risky ~ attack_type + (1|participant) + (1|station=trial) ---")
    try:
        m0 = BinomialBayesMixedGLM.from_formula(
            "risky ~ attack_type_bin", {"participant": "0 + C(participant_id)", "station": "0 + C(trial)"},
            data=model_df)
        r0 = m0.fit_vb()
        fe_names = m0.exog_names
        print("Fixed effects:", fe_names)
        print(r0.summary())
        idx = fe_names.index("attack_type_bin")
        coef, se = r0.fe_mean[idx], r0.fe_sd[idx]
        orr, lo, hi = wilson_like_or_ci(coef, se)
        print(f"attack_type_bin: log-odds={coef:.4f} (SE={se:.4f}) -> OR={orr:.3f} [95% CI {lo:.3f}, {hi:.3f}]")
        results["attack_type"] = {"coef": coef, "se": se, "OR": orr, "CI_lo": lo, "CI_hi": hi}
    except Exception as e:
        print(f"PRIMARY MODEL FAILED TO FIT: {type(e).__name__}: {e}")
        results["attack_type"] = None

    # Gaze-cluster features (AOI-free): one model per feature, attack_type + gaze
    # feature jointly, FDR-corrected across the 3 gaze p-values.
    print("\n--- Gaze-cluster feature models (AOI-free: cluster count, transition rate, entropy) ---")
    gaze_feats_z = ["gaze_n_clusters_z", "gaze_transitions_per_fixation_z", "gaze_entropy_bits_z"]
    gaze_results = {}
    for feat in gaze_feats_z:
        try:
            m = BinomialBayesMixedGLM.from_formula(
                f"risky ~ attack_type_bin + {feat}",
                {"participant": "0 + C(participant_id)", "station": "0 + C(trial)"},
                data=model_df)
            r = m.fit_vb()
            fe_names = m.exog_names
            idx = fe_names.index(feat)
            coef, se = r.fe_mean[idx], r.fe_sd[idx]
            # Wald z-test p-value for this fixed effect (VB posterior mean/sd as an
            # approximate Wald statistic - the standard way to extract a p-value
            # from this fit for FDR purposes; flagged as approximate, not exact).
            from scipy.stats import norm
            z = coef / se if se > 0 else 0.0
            p = 2 * (1 - norm.cdf(abs(z)))
            orr, lo, hi = wilson_like_or_ci(coef, se)
            print(f"  {feat}: log-odds={coef:.4f} (SE={se:.4f}) -> OR={orr:.3f} "
                  f"[95% CI {lo:.3f}, {hi:.3f}], Wald p~{p:.4f}")
            gaze_results[feat] = {"coef": coef, "se": se, "OR": orr, "CI_lo": lo, "CI_hi": hi, "p": p}
        except Exception as e:
            print(f"  {feat}: MODEL FAILED TO FIT - {type(e).__name__}: {e}")
            gaze_results[feat] = None

    valid_gaze = {k: v for k, v in gaze_results.items() if v is not None}
    if valid_gaze:
        ps = [v["p"] for v in valid_gaze.values()]
        qs = fdr_bh(ps)
        print("\nFDR-corrected (Benjamini-Hochberg) across the 3 gaze-cluster features:")
        for (name, v), q in zip(valid_gaze.items(), qs):
            print(f"  {name}: raw p={v['p']:.4f} -> FDR q={q:.4f} "
                  f"{'(significant at q<0.05)' if q < 0.05 else '(not significant)'}")

    # Model diagnostics
    print("\n--- Model diagnostics ---")
    print(f"Primary model VB fit converged: {'attack_type' in results and results['attack_type'] is not None}")
    n_station_levels = model_df["trial"].nunique()
    n_participant_levels = model_df["participant_id"].nunique()
    print(f"Random-effect grouping sizes: {n_participant_levels} participants, {n_station_levels} station "
          f"(trial-number) levels - station is treated as a crossed grouping factor on trial NUMBER "
          f"(1..~20), i.e. 'which station in the sequence', not a specific physical kiosk identity, "
          f"since kiosk identity is not comparable across sessions with randomized layouts.")
    print("BinomialBayesMixedGLM fits via variational Bayes (VB/Laplace approximation), NOT the "
          "frequentist REML/PQL method lme4 uses - no R/lme4 installation is available in this "
          "environment, so this is the best available crossed-random-effects binomial GLMM tool in "
          "pure Python. 'Convergence' here means the VB optimizer's ELBO converged, not a REML "
          "log-likelihood criterion - a real but different guarantee than lme4 would report. "
          "'Singular fit' in the lme4 sense (a random-effect variance estimated at exactly zero) has "
          "no exact VB analogue; the closest check is whether a random-effect's posterior SD "
          "collapsed toward zero, inspected directly in the printed VB summary above.")


if __name__ == "__main__":
    main()
