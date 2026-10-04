#!/usr/bin/env python3
"""
Persist the one model this project has actually validated as worth deploying:
behaviour+gaze (without rag_contaminated), RandomForest - the configuration
D050 showed survives both a random participant-level split and a time-ordered
holdout (AUROC ~0.64-0.70 across both protocols and the D047/D048 sensitivity
checks), and is NOT reliably beaten by adding EEG (D050's CI-overlap check).

Every prior training script in this directory (train_baselines.py,
check_time_confound*.py, final_ablation_table.py) trains-and-evaluates in
memory and discards the fitted model - none of them ever saved one. This is
the first script in the project that persists a model to disk, because it's
the first time one is needed for something other than measuring performance:
Step 12 of the mid-sem report's pipeline ("AI Warning System") needs an
actual artifact to load at runtime, not a number in a terminal.

IMPORTANT - what this model IS and ISN'T:
  - It is fit on ALL 1057 gaze-available rows (no held-out split) - maximizing
    use of real data for the deployed artifact, standard practice once a
    configuration has already been validated (D050) on held-out data.
  - Its IN-SAMPLE fit statistics (also saved, for sanity-checking only) are
    NOT its real performance - cite D050's held-out numbers
    (balanced_accuracy~0.57-0.65, AUROC~0.62-0.70, 95% CIs in that entry) for
    any claim about how good this model actually is.
  - It has never been evaluated on live, real-time-computed features - only
    on the post-hoc, full-session feature extraction build_feature_table.py
    performs after a session is complete. See warning_system.py's own module
    docstring for why this is a scaffold, not a live-wired system.
"""
import json
from datetime import datetime

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from train_baselines import FEATURE_TABLE, BEHAV_COLS, GAZE_COLS, make_label, RANDOM_STATE

MODEL_DIR = "/Users/naman/Documents/MTP/backend/pipeline/model"
FEATURE_COLS = [c for c in BEHAV_COLS if c != "rag_contaminated"] + GAZE_COLS


def main():
    import os
    os.makedirs(MODEL_DIR, exist_ok=True)

    df = pd.read_csv(FEATURE_TABLE)
    df["gaze_missing"] = df["gaze_missing"].astype(bool)
    sub = df[~df["gaze_missing"]].copy()
    y = make_label(sub)
    X = sub[FEATURE_COLS].apply(pd.to_numeric, errors="coerce")
    if "ai_help_used" in X.columns:
        X["ai_help_used"] = X["ai_help_used"].astype(float)

    print(f"Training on {len(X)} rows, {sub['participant_id'].nunique()} participants, "
          f"{len(FEATURE_COLS)} features: {FEATURE_COLS}")
    print(f"Risky-label rate: {y.mean():.4f}")

    imputer = SimpleImputer(strategy="median")
    X_imputed = imputer.fit_transform(X)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)

    model = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE)
    model.fit(X_scaled, y)

    in_sample_pred = model.predict(X_scaled)
    in_sample_acc = float((in_sample_pred == y).mean())
    print(f"In-sample accuracy (NOT a performance claim - see module docstring): {in_sample_acc:.4f}")

    artifact = {
        "model": model,
        "imputer": imputer,
        "scaler": scaler,
        "feature_cols": FEATURE_COLS,
    }
    joblib.dump(artifact, f"{MODEL_DIR}/risk_model.joblib")

    metadata = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "feature_cols": FEATURE_COLS,
        "feature_set_name": "behaviour+gaze (no rag_contaminated)",
        "n_training_rows": len(X),
        "n_training_participants": int(sub["participant_id"].nunique()),
        "risky_label_rate": round(float(y.mean()), 4),
        "in_sample_accuracy": round(in_sample_acc, 4),
        "held_out_performance_DO_NOT_USE_in_sample_stats_instead": {
            "source": "Decision.md D050 (random-split and time-ordered protocols) and D047/D048 (seed/cutoff sensitivity)",
            "balanced_accuracy_range": [0.57, 0.65],
            "auroc_range": [0.62, 0.70],
            "note": "Point estimates and 95% CIs are in D050's table - do not quote a single number without the CI.",
        },
        "model_type": "RandomForestClassifier(n_estimators=200, class_weight='balanced')",
        "random_state": RANDOM_STATE,
        "sklearn_version": __import__("sklearn").__version__,
        "warning": "Trained on post-hoc, full-session feature extraction (build_feature_table.py). "
                    "NOT validated against live/real-time-computed features - see warning_system.py.",
    }
    with open(f"{MODEL_DIR}/risk_model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved model artifact to {MODEL_DIR}/risk_model.joblib")
    print(f"Saved metadata to {MODEL_DIR}/risk_model_metadata.json")


if __name__ == "__main__":
    main()
