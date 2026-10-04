#!/usr/bin/env python3
"""
Phase 4B (D034+): MLP on fused features. Per the phase gate in the brief, this
proceeds only as a real, run check against Phase A's best baseline - not skipped
on the assumption it would lose, and not kept regardless of outcome if it loses.
"""
from sklearn.neural_network import MLPClassifier
import pandas as pd

from train_baselines import (
    FEATURE_TABLE, BEHAV_COLS, GAZE_COLS, EEG_COLS, prep_xy, eval_model, RANDOM_STATE
)

df = pd.read_csv(FEATURE_TABLE)
df["gaze_missing"] = df["gaze_missing"].astype(bool)
df["eeg_missing"] = df["eeg_missing"].astype(bool)

PHASE_A_BEST_BALANCED_ACC = 0.5991  # behaviour-only XGBoost, post-D045 label fix, phase4a_ablation_results.csv
PHASE_A_BEST_AUROC = 0.6854

print("Phase A best (to beat): behaviour-only XGBoost, balanced_acc=0.5991, AUROC=0.6854 (post-D045 label fix)\n")

for set_name, cols, missing_flags in [
    ("behaviour+gaze (fused, n=1057)", BEHAV_COLS + GAZE_COLS, ("gaze_missing",)),
    ("behaviour+gaze+EEG (fused, EEG-qualified subset, n=308)", BEHAV_COLS + GAZE_COLS + EEG_COLS,
     ("gaze_missing", "eeg_missing")),
]:
    X, y, groups, sub = prep_xy(df, cols, require_non_missing_cols=missing_flags)
    print(f"-- {set_name} --")
    r = eval_model("MLP (64,32 relu, early_stopping)",
                    lambda: MLPClassifier(hidden_layer_sizes=(64, 32), activation="relu",
                                           early_stopping=True, max_iter=500, random_state=RANDOM_STATE),
                    X, y, groups)
    if r:
        beat = r["balanced_accuracy"] > PHASE_A_BEST_BALANCED_ACC and r["auroc"] > PHASE_A_BEST_AUROC
        print(f"   Beats Phase A baseline on BOTH metrics? {beat}\n")
    else:
        print("   No result produced.\n")
