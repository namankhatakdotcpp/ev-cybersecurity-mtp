#!/usr/bin/env python3
"""
Extends D039/D043's time-ordered holdout check to the two combined feature sets
(behaviour+gaze, behaviour+gaze+EEG) - flagged as the remaining gap in D043's
remarks. Same two structural findings already established apply here, not
re-derived: (1) `rag_contaminated` is a date proxy (D039) - tested both with and
without it; (2) EEG collection stopped 2026-07-08 (D043) - the EEG-inclusive
combined set can only be time-split within EEG's own collection sub-window, not
against the full dataset's timeline.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from train_baselines import FEATURE_TABLE, BEHAV_COLS, GAZE_COLS, EEG_COLS, make_label, RANDOM_STATE
from check_time_confound import parse_date

try:
    from xgboost import XGBClassifier
    HAVE_XGB = True
except ImportError:
    HAVE_XGB = False


def models():
    d = {
        "LogisticRegression": lambda: LogisticRegression(max_iter=1000, class_weight="balanced"),
        "RandomForest": lambda: RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE),
    }
    if HAVE_XGB:
        d["XGBoost"] = lambda: XGBClassifier(n_estimators=200, max_depth=4, eval_metric="logloss", random_state=RANDOM_STATE)
    return d


def eval_split(X, y, train_mask, test_mask, ctor, label):
    Xtr, Xte = X[train_mask], X[test_mask]
    ytr, yte = y[train_mask], y[test_mask]
    if ytr.nunique() < 2 or yte.nunique() < 2:
        print(f"  [{label}] SKIPPED - single class (train pos={ytr.sum()}/{len(ytr)}, test pos={yte.sum()}/{len(yte)})")
        return None
    imp = SimpleImputer(strategy="median")
    Xtr_i = imp.fit_transform(Xtr); Xte_i = imp.transform(Xte)
    sc = StandardScaler()
    Xtr_s = sc.fit_transform(Xtr_i); Xte_s = sc.transform(Xte_i)
    m = ctor(); m.fit(Xtr_s, ytr)
    pred = m.predict(Xte_s); proba = m.predict_proba(Xte_s)[:, 1]
    bal_acc = balanced_accuracy_score(yte, pred)
    auc = roc_auc_score(yte, proba)
    print(f"  [{label}] n_train={len(Xtr)} n_test={len(Xte)} train_risky={ytr.mean():.3f} "
          f"test_risky={yte.mean():.3f}: balanced_acc={bal_acc:.4f}, AUROC={auc:.4f}")
    return bal_acc, auc


def to_numeric_frame(sub, cols):
    X = sub[cols].apply(pd.to_numeric, errors="coerce")
    for c in ("ai_help_used", "rag_contaminated"):
        if c in X.columns:
            X[c] = X[c].astype(float)
    return X


def main():
    df = pd.read_csv(FEATURE_TABLE)
    df["gaze_missing"] = df["gaze_missing"].astype(bool)
    df["eeg_missing"] = df["eeg_missing"].astype(bool)
    df["session_date"] = df["session_dir"].apply(parse_date)
    y_all = make_label(df)

    # ---- Combined set 1: behaviour+gaze, global chronological boundary (same as
    # D039/D043's 75/25 cutoff over all 126 participants). ------------------------
    print(f"{'='*78}\nbehaviour+gaze (global time-ordered split, same boundary as D039/D043)\n{'='*78}")
    sub1 = df[~df["gaze_missing"]].copy()
    y1 = make_label(sub1)
    p_dates_all = df.groupby("participant_id")["session_date"].first().sort_values()
    cutoff_all = int(len(p_dates_all) * 0.75)
    train_p_all = set(p_dates_all.index[:cutoff_all])
    test_p_all = set(p_dates_all.index[cutoff_all:])
    train_mask1 = sub1["participant_id"].isin(train_p_all)
    test_mask1 = sub1["participant_id"].isin(test_p_all)
    print(f"  n_rows={len(sub1)}, train participants={sub1.loc[train_mask1,'participant_id'].nunique()}, "
          f"test participants={sub1.loc[test_mask1,'participant_id'].nunique()}")

    for cols, label in [
        (BEHAV_COLS + GAZE_COLS, "WITH rag_contaminated"),
        ([c for c in BEHAV_COLS if c != "rag_contaminated"] + GAZE_COLS, "WITHOUT rag_contaminated"),
    ]:
        X1 = to_numeric_frame(sub1, cols)
        print(f" -- {label} --")
        for name, ctor in models().items():
            eval_split(X1, y1, train_mask1, test_mask1, ctor, f"{name}, behaviour+gaze, {label}")

    # ---- Combined set 2: behaviour+gaze+EEG, time-split WITHIN EEG's own
    # collection sub-window only (D043's structural finding - EEG collection stopped
    # 2026-07-08, so a global-timeline split is impossible here). ------------------
    print(f"\n{'='*78}\nbehaviour+gaze+EEG (time-ordered split WITHIN EEG's own collection window)\n{'='*78}")
    sub2 = df[(~df["gaze_missing"]) & (~df["eeg_missing"])].copy()
    y2 = make_label(sub2)
    p_dates_eeg = sub2.groupby("participant_id")["session_date"].first().sort_values()
    n2 = len(p_dates_eeg)
    cutoff2 = int(n2 * 0.75)
    train_p2 = set(p_dates_eeg.index[:cutoff2])
    test_p2 = set(p_dates_eeg.index[cutoff2:])
    train_mask2 = sub2["participant_id"].isin(train_p2)
    test_mask2 = sub2["participant_id"].isin(test_p2)
    print(f"  n_rows={len(sub2)} (both gaze and EEG present), {n2} participants, "
          f"train={len(train_p2)} (up to {p_dates_eeg.iloc[cutoff2-1].date()}), "
          f"test={len(test_p2)} (from {p_dates_eeg.iloc[cutoff2].date()})")

    for cols, label in [
        (BEHAV_COLS + GAZE_COLS + EEG_COLS, "WITH rag_contaminated"),
        ([c for c in BEHAV_COLS if c != "rag_contaminated"] + GAZE_COLS + EEG_COLS, "WITHOUT rag_contaminated"),
    ]:
        X2 = to_numeric_frame(sub2, cols)
        print(f" -- {label} --")
        for name, ctor in models().items():
            eval_split(X2, y2, train_mask2, test_mask2, ctor, f"{name}, behaviour+gaze+EEG, {label}")

    # Reference: random-split (D037 protocol) numbers for both, for direct comparison
    print(f"\n{'='*78}\nReference: random participant-level split (D037 protocol), same subsets\n{'='*78}")
    from sklearn.model_selection import GroupKFold
    gkf = GroupKFold(n_splits=5)
    for sub, y, cols_list, name_prefix in [
        (sub1, y1, [(BEHAV_COLS + GAZE_COLS, "WITH rag_contaminated"),
                    ([c for c in BEHAV_COLS if c != "rag_contaminated"] + GAZE_COLS, "WITHOUT rag_contaminated")],
         "behaviour+gaze"),
        (sub2, y2, [(BEHAV_COLS + GAZE_COLS + EEG_COLS, "WITH rag_contaminated"),
                    ([c for c in BEHAV_COLS if c != "rag_contaminated"] + GAZE_COLS + EEG_COLS, "WITHOUT rag_contaminated")],
         "behaviour+gaze+EEG"),
    ]:
        groups = sub["participant_id"]
        for cols, label in cols_list:
            X = to_numeric_frame(sub, cols)
            bal_accs, aucs = [], []
            for train_idx, test_idx in gkf.split(X, y, groups):
                Xtr, Xte = X.iloc[train_idx], X.iloc[test_idx]
                ytr, yte = y.iloc[train_idx], y.iloc[test_idx]
                if ytr.nunique() < 2 or yte.nunique() < 2:
                    continue
                imp = SimpleImputer(strategy="median")
                Xtr_i = imp.fit_transform(Xtr); Xte_i = imp.transform(Xte)
                sc = StandardScaler()
                Xtr_s = sc.fit_transform(Xtr_i); Xte_s = sc.transform(Xte_i)
                m = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE)
                m.fit(Xtr_s, ytr)
                pred = m.predict(Xte_s); proba = m.predict_proba(Xte_s)[:, 1]
                bal_accs.append(balanced_accuracy_score(yte, pred))
                aucs.append(roc_auc_score(yte, proba))
            if bal_accs:
                print(f"  [RandomForest, {name_prefix}, {label}] random-split: "
                      f"balanced_acc={np.mean(bal_accs):.4f}, AUROC={np.mean(aucs):.4f}")


if __name__ == "__main__":
    main()
