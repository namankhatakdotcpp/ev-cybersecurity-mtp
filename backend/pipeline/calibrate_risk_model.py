#!/usr/bin/env python3
"""
Risk-model calibration (D057). The deployed model (D055,
backend/pipeline/model/risk_model.joblib) is fit on ALL 1057 gaze-available
rows with no held-out split - fine for a deployment fit, but it means its
raw predict_proba() output has never been checked for whether "0.7" actually
means "70% of the time this was really risky." That check, not another
performance number, is what this script does.

Method, participant-level throughout (mandatory, no exceptions):
  1. Same 5-fold GroupKFold as D045/D050 (RANDOM_STATE=42), same feature set
     as the deployed model (behaviour, no rag_contaminated, + gaze) -
     produces pooled out-of-fold (OOF) raw probabilities for all 1057 rows.
     This is the honest "held-out participants" data this task asked for -
     every probability here came from a model that never saw that
     participant during training.
  2. Raw calibration curve + Brier score on those OOF probabilities.
  3. Two calibrators were tried and compared, not just one assumed:
     isotonic regression (sklearn's usual default for this) and Platt/sigmoid
     scaling (a 1-feature logistic regression on the raw probability). Both
     evaluated with a SECOND, nested 5-fold split over the OOF pairs
     themselves (fit on 4/5, score on the held-out 1/5, rotate), so neither
     is evaluated on the pairs it was fit on. Isotonic wins on Brier score
     but produces a severely compressed distribution (most calibrated
     probabilities fall within a narrow band) - a known isotonic pathology
     at this sample size (a monotonic step function has too few real "steps"
     to support with ~1000 points and a modest-AUROC model). That
     distribution cannot support meaningful low/medium/high thresholds - a
     "high" cutoff in the usual sense would almost never fire. Platt
     scaling's slightly worse Brier score buys a smooth, well-spread,
     actually usable probability range - chosen as the deployed calibrator
     for that practical reason, reported explicitly rather than silently
     picking whichever had the lower Brier number.
  4. New risk thresholds are picked on the Platt-CALIBRATED scale, where a
     probability is supposed to mean what it says - not percentile-derived
     from an uncalibrated, in-sample distribution (D055's original
     thresholds, which this script replaces). Picked AFTER inspecting the
     printed distribution, not hardcoded in advance.
"""
import json
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from train_baselines import FEATURE_TABLE, BEHAV_COLS, GAZE_COLS, make_label, RANDOM_STATE

MODEL_PATH = "/Users/naman/Documents/MTP/backend/pipeline/model/risk_model.joblib"
METADATA_PATH = "/Users/naman/Documents/MTP/backend/pipeline/model/risk_model_metadata.json"
FEATURE_COLS = [c for c in BEHAV_COLS if c != "rag_contaminated"] + GAZE_COLS
N_FOLDS = 5

# Chosen after inspecting both calibrators' nested-CV distributions (see
# Decision.md D057): isotonic compresses 99% of mass below ~0.48 and is
# unusable for a "high" cutoff; Platt spreads roughly 0.19 (p10) to 0.50+
# (p90), so these round numbers correspond to real, checkable deciles.
FINAL_THRESHOLD_LOW = 0.25
FINAL_THRESHOLD_HIGH = 0.50


def fit_predict_fold(X_train, y_train, X_test):
    imputer = SimpleImputer(strategy="median")
    Xtr = imputer.fit_transform(X_train)
    Xte = imputer.transform(X_test)
    scaler = StandardScaler()
    Xtr = scaler.fit_transform(Xtr)
    Xte = scaler.transform(Xte)
    model = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE)
    model.fit(Xtr, y_train)
    proba = model.predict_proba(Xte)
    classes = list(model.classes_)
    return proba[:, classes.index(1)]


def pooled_oof_probabilities(X, y, groups, n_folds=N_FOLDS):
    gkf = GroupKFold(n_splits=n_folds)
    oof_proba = np.full(len(y), np.nan)
    for train_idx, test_idx in gkf.split(X, y, groups):
        y_train = y.iloc[train_idx]
        if y_train.nunique() < 2:
            continue
        oof_proba[test_idx] = fit_predict_fold(X.iloc[train_idx], y_train, X.iloc[test_idx])
    valid = ~np.isnan(oof_proba)
    return oof_proba, valid


def nested_isotonic(raw_proba, y_arr, groups, n_folds=N_FOLDS):
    gkf = GroupKFold(n_splits=n_folds)
    calibrated = np.full(len(y_arr), np.nan)
    for train_idx, test_idx in gkf.split(raw_proba.reshape(-1, 1), y_arr, groups):
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(raw_proba[train_idx], y_arr[train_idx])
        calibrated[test_idx] = iso.predict(raw_proba[test_idx])
    return calibrated


def nested_platt(raw_proba, y_arr, groups, n_folds=N_FOLDS):
    gkf = GroupKFold(n_splits=n_folds)
    calibrated = np.full(len(y_arr), np.nan)
    for train_idx, test_idx in gkf.split(raw_proba.reshape(-1, 1), y_arr, groups):
        lr = LogisticRegression()
        lr.fit(raw_proba[train_idx].reshape(-1, 1), y_arr[train_idx])
        calibrated[test_idx] = lr.predict_proba(raw_proba[test_idx].reshape(-1, 1))[:, 1]
    return calibrated


def describe(label, arr):
    pcts = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99]
    vals = np.percentile(arr, pcts)
    print(f"{label} percentiles: " + ", ".join(f"p{p}={v:.4f}" for p, v in zip(pcts, vals)))
    print(f"{label} range: [{arr.min():.4f}, {arr.max():.4f}]")


def main():
    df = pd.read_csv(FEATURE_TABLE)
    df["gaze_missing"] = df["gaze_missing"].astype(bool)
    sub = df[~df["gaze_missing"]].copy()
    y = make_label(sub)
    X = sub[FEATURE_COLS].apply(pd.to_numeric, errors="coerce")
    if "ai_help_used" in X.columns:
        X["ai_help_used"] = X["ai_help_used"].astype(float)
    groups = sub["participant_id"]

    print(f"n={len(X)} rows, {groups.nunique()} participants, risky_rate={y.mean():.4f}\n")

    raw_proba, valid = pooled_oof_probabilities(X, y, groups)
    raw_v = raw_proba[valid]
    y_v = y[valid].reset_index(drop=True)
    groups_v = groups[valid].reset_index(drop=True)
    y_arr = y_v.to_numpy()

    raw_brier = brier_score_loss(y_arr, raw_v)
    baseline_brier = y_v.mean() * (1 - y_v.mean())  # always predicting the base rate
    print(f"RAW model (held-out, pooled OOF, n={valid.sum()}): Brier = {raw_brier:.4f} "
          f"(always-predict-base-rate baseline: {baseline_brier:.4f})")
    raw_fp, raw_mp = calibration_curve(y_arr, raw_v, n_bins=8, strategy="quantile")
    print("RAW calibration curve: mean_predicted -> observed_frequency")
    for mp, fp in zip(raw_mp, raw_fp):
        print(f"  {mp:.3f} -> {fp:.3f}  (diff={fp - mp:+.3f})")
    describe("RAW", raw_v)

    print(f"\n{'-'*70}\nISOTONIC calibration (nested CV)\n{'-'*70}")
    iso_oof = nested_isotonic(raw_v, y_arr, groups_v)
    iso_brier = brier_score_loss(y_arr, iso_oof)
    print(f"Brier = {iso_brier:.4f} (vs raw {raw_brier:.4f}, improvement {raw_brier - iso_brier:+.4f})")
    describe("ISOTONIC", iso_oof)

    print(f"\n{'-'*70}\nPLATT/sigmoid calibration (nested CV)\n{'-'*70}")
    platt_oof = nested_platt(raw_v, y_arr, groups_v)
    platt_brier = brier_score_loss(y_arr, platt_oof)
    print(f"Brier = {platt_brier:.4f} (vs raw {raw_brier:.4f}, improvement {raw_brier - platt_brier:+.4f})")
    describe("PLATT", platt_oof)
    platt_fp, platt_mp = calibration_curve(y_arr, platt_oof, n_bins=8, strategy="quantile")
    print("PLATT calibration curve: mean_predicted -> observed_frequency")
    for mp, fp in zip(platt_mp, platt_fp):
        print(f"  {mp:.3f} -> {fp:.3f}  (diff={fp - mp:+.3f})")

    print(f"\n{'='*70}\nDecision: deploying PLATT (usable spread), not ISOTONIC (better Brier "
          f"but degenerate distribution for thresholding) - see module docstring.\n{'='*70}")
    low, high = FINAL_THRESHOLD_LOW, FINAL_THRESHOLD_HIGH
    frac_low = float((platt_oof < low).mean())
    frac_high = float((platt_oof >= high).mean())
    frac_warn = float((platt_oof >= low).mean())
    print(f"Thresholds low<{low}, high>={high} on the Platt-calibrated scale (held-out OOF):")
    print(f"  fraction classified 'low' (no warning): {frac_low:.3f}")
    print(f"  fraction classified 'high': {frac_high:.3f}")
    print(f"  fraction that would trigger should_warn (medium+high): {frac_warn:.3f}")
    print("  (this is a real, measured consequence of the model's current discriminative power, "
          "not a bug - a model with AUROC~0.6-0.7 cannot have both a low warning rate AND low "
          "false-negative rate; this is the operating point low/high currently imply, stated "
          "plainly so the team can choose a different tradeoff deliberately if they want one)")

    if "--save" not in sys.argv:
        print("\n(diagnostic-only run - pass --save to persist the calibrator + thresholds)")
        return

    final_calibrator = LogisticRegression()
    final_calibrator.fit(raw_v.reshape(-1, 1), y_arr)

    artifact = joblib.load(MODEL_PATH)
    artifact["calibrator"] = final_calibrator
    joblib.dump(artifact, MODEL_PATH)
    print(f"\nUpdated {MODEL_PATH} with the fitted Platt calibrator.")

    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    metadata["calibration"] = {
        "method": "Platt/sigmoid scaling (LogisticRegression on raw probability), chosen over "
                   "isotonic regression for usable spread - see module docstring",
        "n_calibration_pairs": int(valid.sum()),
        "raw_brier_score_held_out": round(float(raw_brier), 4),
        "isotonic_brier_score_nested_cv": round(float(iso_brier), 4),
        "platt_brier_score_nested_cv": round(float(platt_brier), 4),
        "always_predict_base_rate_brier": round(float(baseline_brier), 4),
        "raw_calibration_curve": [{"mean_predicted": round(float(mp), 4), "observed_frequency": round(float(fp), 4)}
                                   for mp, fp in zip(raw_mp, raw_fp)],
        "platt_calibration_curve_nested_cv": [{"mean_predicted": round(float(mp), 4), "observed_frequency": round(float(fp), 4)}
                                                for mp, fp in zip(platt_mp, platt_fp)],
        "new_thresholds": {"low": low, "high": high},
        "operating_point_at_these_thresholds": {
            "fraction_low": round(frac_low, 4), "fraction_high": round(frac_high, 4),
            "fraction_would_warn": round(frac_warn, 4),
        },
        "note": "predict_risk() now applies this Platt calibrator to the raw RandomForest output - see risk_model.py",
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Updated {METADATA_PATH} with calibration results.")


if __name__ == "__main__":
    main()
