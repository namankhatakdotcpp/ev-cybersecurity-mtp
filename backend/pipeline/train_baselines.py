#!/usr/bin/env python3
"""
Phase 4A (D034+): classical baselines (logistic regression, random forest, XGBoost-
if-available) on the Phase 2 feature table, with mandatory participant-level splits
and a modality ablation (behaviour-only / gaze-only / EEG-only / combined).

Label: decision == "charge" vs "skip" is NOT the risk label by itself - charging at
a compromised kiosk is the risky outcome this pipeline cares about (the standing
research question is about risky decisions, not charge/skip per se). risky = 1 iff
decision=="charge" AND kiosk_attack is "Cyber Attack" OR "System Anomaly" - the
game backend logs the SAME underlying compromised-kiosk mechanic under one of two
terminologies depending on the session's `incident_mode` config flag (confirmed by
reading receive_ui.py's `_generate_station_layout`/`_get_incident_mode`: the attack
probabilities, deepfake_attack_probability/real_attack_probability, are identical
either way - only the label string differs). An earlier version of this function
matched "Cyber Attack" only, which silently mislabeled every "System Anomaly"
session's real attack-kiosk charges as safe - see Decision.md D045 for the full
diagnosis (56/138 sessions, 176 rows, 15.7% of the dataset, all with risky_rate
computed as exactly 0.0 under the old bug, zero exceptions). Fixed here, not
worked around by excluding those sessions, since the underlying events are real and
usable once correctly labeled. This label comes only from game-log fields already
in the table (kiosk_attack, decision) - never gaze/EEG, per the standing rule
unchanged since the original pipeline brief.

Per-phase gate (Phase 4 brief): MLP proceeds only if it beats this baseline on
held-out participants; this script only runs Phase A.
"""
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.dummy import DummyClassifier

try:
    from xgboost import XGBClassifier
    HAVE_XGB = True
except ImportError:
    HAVE_XGB = False

# Directory holding feature_table.csv and where results are written. Defaults to
# this file's own directory; override with EV_PIPELINE_DIR.
PIPELINE_DIR = os.environ.get("EV_PIPELINE_DIR", os.path.dirname(os.path.abspath(__file__)))
FEATURE_TABLE = os.path.join(PIPELINE_DIR, "feature_table.csv")
N_FOLDS = 5
RANDOM_STATE = 42

GAZE_COLS = ["gaze_n_fixations", "gaze_n_clusters", "gaze_n_transitions",
             "gaze_transitions_per_fixation", "gaze_dispersion", "gaze_entropy_bits"]
EEG_COLS = [c for c in [
    f"eeg_{ch}_{b}_rel" for ch in ("tp9", "af7", "af8", "tp10") for b in ("delta", "theta", "alpha", "beta")
]] + ["eeg_low_motion_fraction"]
BEHAV_COLS = ["window_duration_s", "ai_help_used", "rag_contaminated"]


COMPROMISED_LABELS = ("Cyber Attack", "System Anomaly")


def make_label(df):
    risky = (df["decision"] == "charge") & (df["kiosk_attack"].isin(COMPROMISED_LABELS))
    return risky.astype(int)


def prep_xy(df, cols, require_non_missing_cols=()):
    sub = df.copy()
    for c in require_non_missing_cols:
        sub = sub[~sub[c]]
    X = sub[cols].apply(pd.to_numeric, errors="coerce")
    if "ai_help_used" in X.columns:
        X["ai_help_used"] = X["ai_help_used"].astype(float)
    if "rag_contaminated" in X.columns:
        X["rag_contaminated"] = X["rag_contaminated"].astype(float)
    y = make_label(sub)
    groups = sub["participant_id"]
    return X, y, groups, sub


def eval_model(name, model, X, y, groups):
    n_groups = groups.nunique()
    n_folds = min(N_FOLDS, n_groups)
    if n_folds < 2:
        print(f"  [{name}] SKIPPED - only {n_groups} participant(s) in this subset, need >=2 for a group split")
        return None
    gkf = GroupKFold(n_splits=n_folds)
    bal_accs, f1s, aucs = [], [], []
    for train_idx, test_idx in gkf.split(X, y, groups):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        if y_train.nunique() < 2 or y_test.nunique() < 2:
            continue
        imputer = SimpleImputer(strategy="median")
        X_train_i = imputer.fit_transform(X_train)
        X_test_i = imputer.transform(X_test)
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train_i)
        X_test_s = scaler.transform(X_test_i)

        m = model()
        m.fit(X_train_s, y_train)
        pred = m.predict(X_test_s)
        try:
            proba = m.predict_proba(X_test_s)[:, 1]
            auc = roc_auc_score(y_test, proba)
        except Exception:
            auc = float("nan")
        bal_accs.append(balanced_accuracy_score(y_test, pred))
        f1s.append(f1_score(y_test, pred, zero_division=0))
        aucs.append(auc)

    if not bal_accs:
        print(f"  [{name}] SKIPPED - no fold had both classes in train and test")
        return None
    result = {
        "model": name, "n_rows": len(X), "n_participants": n_groups, "n_folds_used": len(bal_accs),
        "balanced_accuracy": round(float(np.mean(bal_accs)), 4),
        "f1": round(float(np.mean(f1s)), 4),
        "auroc": round(float(np.nanmean(aucs)), 4) if not all(np.isnan(aucs)) else None,
    }
    print(f"  [{name}] n={len(X)} (participants={n_groups}, folds={len(bal_accs)}): "
          f"balanced_acc={result['balanced_accuracy']}, F1={result['f1']}, AUROC={result['auroc']}")
    return result


def majority_baseline(X, y, groups):
    gkf = GroupKFold(n_splits=min(N_FOLDS, groups.nunique()))
    bal_accs = []
    for train_idx, test_idx in gkf.split(X, y, groups):
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        if y_train.nunique() < 1:
            continue
        dc = DummyClassifier(strategy="most_frequent")
        dc.fit(np.zeros((len(y_train), 1)), y_train)
        pred = dc.predict(np.zeros((len(y_test), 1)))
        bal_accs.append(balanced_accuracy_score(y_test, pred))
    return round(float(np.mean(bal_accs)), 4) if bal_accs else None


def run_ablation(df, label_name, feature_sets):
    print(f"\n{'='*78}\n{label_name}\n{'='*78}")
    results = []
    for set_name, cols, missing_flags in feature_sets:
        X, y, groups, sub = prep_xy(df, cols, require_non_missing_cols=missing_flags)
        if len(sub) == 0:
            print(f"\n-- {set_name}: 0 rows available, skipped --")
            continue
        print(f"\n-- {set_name} ({len(cols)} features, n={len(sub)}, participants={groups.nunique()}, "
              f"risky_rate={y.mean():.3f}) --")
        maj = majority_baseline(X, y, groups)
        print(f"  [majority-class baseline] balanced_acc={maj}")
        models = {
            "LogisticRegression": lambda: LogisticRegression(max_iter=1000, class_weight="balanced"),
            "RandomForest": lambda: RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                                             random_state=RANDOM_STATE),
        }
        if HAVE_XGB:
            models["XGBoost"] = lambda: XGBClassifier(n_estimators=200, max_depth=4, use_label_encoder=False,
                                                        eval_metric="logloss", random_state=RANDOM_STATE)
        for mname, mfn in models.items():
            r = eval_model(mname, mfn, X, y, groups)
            if r:
                r["feature_set"] = set_name
                r["majority_baseline_balanced_acc"] = maj
                results.append(r)
    return results


def main():
    df = pd.read_csv(FEATURE_TABLE)
    df["gaze_missing"] = df["gaze_missing"].astype(bool)
    df["eeg_missing"] = df["eeg_missing"].astype(bool)
    print(f"Loaded {len(df)} rows, {df['participant_id'].nunique()} participants")
    print("Risky-label rate overall:", round(make_label(df).mean(), 4))
    if not HAVE_XGB:
        print("NOTE: xgboost not installed in this environment - running LogisticRegression + "
              "RandomForest only, UNVERIFIED for XGBoost specifically this run.")

    feature_sets = [
        ("behaviour-only", BEHAV_COLS, ()),
        ("gaze-only", GAZE_COLS, ("gaze_missing",)),
        ("EEG-only", EEG_COLS, ("eeg_missing",)),
        ("behaviour+gaze", BEHAV_COLS + GAZE_COLS, ("gaze_missing",)),
        ("behaviour+gaze+EEG (EEG-qualified subset)", BEHAV_COLS + GAZE_COLS + EEG_COLS,
         ("gaze_missing", "eeg_missing")),
    ]
    results = run_ablation(df, "Phase 4A: classical baselines, modality ablation", feature_sets)

    out = pd.DataFrame(results)
    out_path = os.path.join(PIPELINE_DIR, "phase4a_ablation_results.csv")
    out.to_csv(out_path, index=False)
    print(f"\n\nWrote ablation results to {out_path}")
    print(out.to_string(index=False) if len(out) else "No results produced.")


if __name__ == "__main__":
    main()
