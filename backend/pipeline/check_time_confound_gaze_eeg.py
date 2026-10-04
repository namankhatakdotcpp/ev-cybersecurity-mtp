#!/usr/bin/env python3
"""
Extends D039's time-ordered holdout check to gaze-only and EEG-only (flagged in
D039's own remarks as the natural next check, not done in that pass). Reuses the
EXACT SAME chronological train/test participant split as D039's behaviour-only
check (earliest 75% of participants by session date vs. latest 25%, computed once
over the full 126-participant dataset) - not a re-derived, feature-set-specific
cutoff - so all three modalities are being judged against the same time boundary.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score, f1_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from train_baselines import FEATURE_TABLE, BEHAV_COLS, GAZE_COLS, EEG_COLS, make_label, RANDOM_STATE
from check_time_confound import parse_date

try:
    from xgboost import XGBClassifier
    HAVE_XGB = True
except ImportError:
    HAVE_XGB = False


def eval_random_split(X, y, groups, ctor, label):
    """Same participant-level GroupKFold random-split protocol as D037, for reference."""
    gkf = GroupKFold(n_splits=5)
    bal_accs, aucs, f1s = [], [], []
    for train_idx, test_idx in gkf.split(X, y, groups):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        if y_train.nunique() < 2 or y_test.nunique() < 2:
            continue
        imputer = SimpleImputer(strategy="median")
        Xtr = imputer.fit_transform(X_train); Xte = imputer.transform(X_test)
        sc = StandardScaler()
        Xtr = sc.fit_transform(Xtr); Xte = sc.transform(Xte)
        m = ctor(); m.fit(Xtr, y_train)
        pred = m.predict(Xte)
        proba = m.predict_proba(Xte)[:, 1]
        bal_accs.append(balanced_accuracy_score(y_test, pred))
        aucs.append(roc_auc_score(y_test, proba))
        f1s.append(f1_score(y_test, pred, zero_division=0))
    if not bal_accs:
        print(f"  [{label}] SKIPPED - no fold had both classes in train and test")
        return None
    print(f"  [{label}] random-split (D037 protocol): n={len(X)} participants={groups.nunique()} "
          f"balanced_acc={np.mean(bal_accs):.4f}, F1={np.mean(f1s):.4f}, AUROC={np.mean(aucs):.4f} "
          f"(folds={len(bal_accs)})")
    return np.mean(bal_accs), np.mean(aucs)


def eval_time_split(X, y, train_mask, test_mask, ctor, label):
    X_train, X_test = X[train_mask], X[test_mask]
    y_train, y_test = y[train_mask], y[test_mask]
    if y_train.nunique() < 2 or y_test.nunique() < 2:
        print(f"  [{label}] SKIPPED (time split) - single class in train or test "
              f"(n_train={len(X_train)} pos={y_train.sum()}, n_test={len(X_test)} pos={y_test.sum()})")
        return None
    imputer = SimpleImputer(strategy="median")
    Xtr = imputer.fit_transform(X_train); Xte = imputer.transform(X_test)
    sc = StandardScaler()
    Xtr = sc.fit_transform(Xtr); Xte = sc.transform(Xte)
    m = ctor(); m.fit(Xtr, y_train)
    pred = m.predict(Xte)
    proba = m.predict_proba(Xte)[:, 1]
    bal_acc = balanced_accuracy_score(y_test, pred)
    auc = roc_auc_score(y_test, proba)
    print(f"  [{label}] TIME-ORDERED split: n_train={len(X_train)} n_test={len(X_test)} "
          f"train_risky={y_train.mean():.3f} test_risky={y_test.mean():.3f}: "
          f"balanced_acc={bal_acc:.4f}, AUROC={auc:.4f}")
    return bal_acc, auc


def prep(df, cols, missing_col):
    sub = df[~df[missing_col]].copy() if missing_col else df.copy()
    X = sub[cols].apply(pd.to_numeric, errors="coerce")
    for c in ("ai_help_used", "rag_contaminated"):
        if c in X.columns:
            X[c] = X[c].astype(float)
    y = make_label(sub)
    groups = sub["participant_id"]
    return X, y, groups, sub


def main():
    df = pd.read_csv(FEATURE_TABLE)
    df["gaze_missing"] = df["gaze_missing"].astype(bool)
    df["eeg_missing"] = df["eeg_missing"].astype(bool)
    df["session_date"] = df["session_dir"].apply(parse_date)

    # SAME chronological cutoff as D039's Step 3c, recomputed identically (not a new
    # derivation) over the full 126-participant dataset.
    participant_dates = df.groupby("participant_id")["session_date"].first().sort_values()
    n_part = len(participant_dates)
    cutoff = int(n_part * 0.75)
    train_participants = set(participant_dates.index[:cutoff])
    test_participants = set(participant_dates.index[cutoff:])
    print(f"Chronological split (same as D039): {len(train_participants)} train participants "
          f"(up to {participant_dates.iloc[cutoff-1].date()}), {len(test_participants)} test participants "
          f"(from {participant_dates.iloc[cutoff].date()})")

    for set_name, cols, missing_col in [
        ("gaze-only", GAZE_COLS, "gaze_missing"),
        ("EEG-only", EEG_COLS, "eeg_missing"),
    ]:
        print(f"\n{'='*78}\n{set_name}\n{'='*78}")
        X, y, groups, sub = prep(df, cols, missing_col)
        train_mask = sub["participant_id"].isin(train_participants)
        test_mask = sub["participant_id"].isin(test_participants)
        n_train_p = sub.loc[train_mask, "participant_id"].nunique()
        n_test_p = sub.loc[test_mask, "participant_id"].nunique()
        print(f"  n_rows={len(sub)}, n_participants={groups.nunique()} "
              f"(train side has {n_train_p}, test side has {n_test_p} of this modality's participants)")

        models = {
            "LogisticRegression": lambda: LogisticRegression(max_iter=1000, class_weight="balanced"),
            "RandomForest": lambda: RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE),
        }
        if HAVE_XGB:
            models["XGBoost"] = lambda: XGBClassifier(n_estimators=200, max_depth=4, eval_metric="logloss", random_state=RANDOM_STATE)

        for mname, ctor in models.items():
            eval_random_split(X, y, groups, ctor, f"{mname} ({set_name})")
        print()
        for mname, ctor in models.items():
            eval_time_split(X, y, train_mask, test_mask, ctor, f"{mname} ({set_name})")


if __name__ == "__main__":
    main()
