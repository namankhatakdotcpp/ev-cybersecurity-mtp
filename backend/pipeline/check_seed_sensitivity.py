#!/usr/bin/env python3
"""
Seed-sensitivity check on D045's headline result: behaviour+gaze+EEG (without
rag_contaminated), time-split within EEG's own collection window (train=42/test=14
participants, n=308 rows) - RandomForest reported balanced_acc=0.651, AUROC=0.695
at random_state=42. That's a single train/test partition and a single model seed
on a small test set (n=87 rows, 14 participants) - worth knowing how much the
number moves under different model seeds before treating it as a stable estimate.

Checked: RandomForest and XGBoost (both have seed-dependent bootstrap/feature
sampling) across 30 seeds each, same fixed time-ordered train/test split throughout
(the split itself is NOT re-randomized - only the model's internal randomness is).
LogisticRegression (lbfgs solver) is deterministic given the data and is run once
as a reference, not swept.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from train_baselines import FEATURE_TABLE, BEHAV_COLS, GAZE_COLS, EEG_COLS, make_label
from check_time_confound import parse_date

try:
    from xgboost import XGBClassifier
    HAVE_XGB = True
except ImportError:
    HAVE_XGB = False

N_SEEDS = 30
COLS_NO_CONTAM = [c for c in BEHAV_COLS if c != "rag_contaminated"] + GAZE_COLS + EEG_COLS


def main():
    df = pd.read_csv(FEATURE_TABLE)
    df["gaze_missing"] = df["gaze_missing"].astype(bool)
    df["eeg_missing"] = df["eeg_missing"].astype(bool)
    df["session_date"] = df["session_dir"].apply(parse_date)

    sub = df[(~df["gaze_missing"]) & (~df["eeg_missing"])].copy()
    y = make_label(sub)
    p_dates = sub.groupby("participant_id")["session_date"].first().sort_values()
    n = len(p_dates)
    cutoff = int(n * 0.75)
    train_p = set(p_dates.index[:cutoff])
    test_p = set(p_dates.index[cutoff:])
    train_mask = sub["participant_id"].isin(train_p)
    test_mask = sub["participant_id"].isin(test_p)

    print(f"Fixed time-ordered split (same as D045): {len(train_p)} train participants "
          f"(up to {p_dates.iloc[cutoff-1].date()}), {len(test_p)} test participants "
          f"(from {p_dates.iloc[cutoff].date()})")
    print(f"n_train={train_mask.sum()}, n_test={test_mask.sum()}, "
          f"train_risky={y[train_mask].mean():.3f}, test_risky={y[test_mask].mean():.3f}\n")

    X = sub[COLS_NO_CONTAM].apply(pd.to_numeric, errors="coerce")
    X_train, X_test = X[train_mask], X[test_mask]
    y_train, y_test = y[train_mask], y[test_mask]

    # Imputation/scaling are deterministic (median/mean), fit on train only - not
    # re-randomized per seed, so this isolates model-seed sensitivity specifically.
    imputer = SimpleImputer(strategy="median")
    X_train_i = imputer.fit_transform(X_train)
    X_test_i = imputer.transform(X_test)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train_i)
    X_test_s = scaler.transform(X_test_i)

    # Deterministic reference
    lr = LogisticRegression(max_iter=1000, class_weight="balanced")
    lr.fit(X_train_s, y_train)
    lr_pred = lr.predict(X_test_s)
    lr_proba = lr.predict_proba(X_test_s)[:, 1]
    print(f"LogisticRegression (deterministic, no seed): balanced_acc="
          f"{balanced_accuracy_score(y_test, lr_pred):.4f}, AUROC={roc_auc_score(y_test, lr_proba):.4f}\n")

    for model_name, ctor in [
        ("RandomForest", lambda seed: RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=seed)),
    ] + ([("XGBoost", lambda seed: XGBClassifier(n_estimators=200, max_depth=4, eval_metric="logloss", random_state=seed))] if HAVE_XGB else []):
        bal_accs, aucs = [], []
        seeds = list(range(N_SEEDS)) + [42]  # 42 is D045's originally reported seed
        for seed in seeds:
            m = ctor(seed)
            m.fit(X_train_s, y_train)
            pred = m.predict(X_test_s)
            proba = m.predict_proba(X_test_s)[:, 1]
            bal_accs.append(balanced_accuracy_score(y_test, pred))
            aucs.append(roc_auc_score(y_test, proba))
        seed42_bal_acc, seed42_auc = bal_accs[-1], aucs[-1]
        bal_accs_sweep = np.array(bal_accs[:-1])
        aucs_sweep = np.array(aucs[:-1])
        print(f"{model_name} across seeds 0-{N_SEEDS-1} (plus seed=42 reported separately):")
        print(f"  balanced_acc: mean={bal_accs_sweep.mean():.4f} std={bal_accs_sweep.std():.4f} "
              f"min={bal_accs_sweep.min():.4f} max={bal_accs_sweep.max():.4f}")
        print(f"  AUROC:        mean={aucs_sweep.mean():.4f} std={aucs_sweep.std():.4f} "
              f"min={aucs_sweep.min():.4f} max={aucs_sweep.max():.4f}")
        print(f"  seed=42 (originally reported, D045): balanced_acc={seed42_bal_acc:.4f}, AUROC={seed42_auc:.4f}")
        n_above_chance_auc = (aucs_sweep > 0.5).sum()
        print(f"  seeds with AUROC > 0.5: {n_above_chance_auc}/{N_SEEDS}")
        print()


if __name__ == "__main__":
    main()
