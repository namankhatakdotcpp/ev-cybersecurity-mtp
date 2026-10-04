#!/usr/bin/env python3
"""
Task 1 (D039+): direct test of whether Phase 4's behaviour-only headline result
(balanced_acc=0.632, AUROC=0.712) is partly riding a time trend (collection date /
rag_contaminated as a date proxy) rather than genuine behavioural signal.

Participant-level splits remain mandatory throughout, including for the time-ordered
split - each participant's session happened at one point in time, so a participant
never actually spans the split boundary, but we still group by participant_id in
every CV/split call rather than assuming that.
"""
import re

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from train_baselines import FEATURE_TABLE, BEHAV_COLS, make_label, RANDOM_STATE

try:
    from xgboost import XGBClassifier
    HAVE_XGB = True
except ImportError:
    HAVE_XGB = False


def parse_date(session_dir):
    m = re.match(r"session_(\d{8})_(\d{6})_", session_dir)
    if not m:
        return None
    return pd.to_datetime(m.group(1) + m.group(2), format="%Y%m%d%H%M%S")


def main():
    df = pd.read_csv(FEATURE_TABLE)
    df["gaze_missing"] = df["gaze_missing"].astype(bool)
    df["eeg_missing"] = df["eeg_missing"].astype(bool)
    df["session_date"] = df["session_dir"].apply(parse_date)
    df["risky"] = make_label(df)

    print(f"Loaded {len(df)} rows, {df['participant_id'].nunique()} participants, "
          f"session dates {df['session_date'].min().date()} to {df['session_date'].max().date()}")

    # ---- Step 1: risky-rate drift over collection time -------------------
    print(f"\n{'='*78}\nSTEP 1: risky-decision base rate over the collection window\n{'='*78}")
    per_session = df.groupby("session_dir").agg(
        session_date=("session_date", "first"),
        n_rows=("risky", "size"),
        risky_rate=("risky", "mean"),
    ).sort_values("session_date")
    per_session["collection_order"] = range(len(per_session))
    per_session["week"] = per_session["session_date"].dt.to_period("W").astype(str)

    weekly = per_session.groupby("week").agg(
        n_sessions=("session_date", "size"), n_rows=("n_rows", "sum"),
        risky_rate=("risky_rate", "mean"),
    )
    print("\nWeekly risky-rate (per-session mean, not row-weighted):")
    print(weekly.to_string())

    # row-weighted overall rate per quartile of collection order, for a blunter check
    n = len(per_session)
    per_session["quartile"] = pd.qcut(per_session["collection_order"], 4, labels=["Q1(earliest)", "Q2", "Q3", "Q4(latest)"])
    q_rows = df.merge(per_session[["quartile"]], left_on="session_dir", right_index=True)
    q_summary = q_rows.groupby("quartile").agg(n_rows=("risky", "size"), risky_rate=("risky", "mean"),
                                                 rag_contaminated_rate=("rag_contaminated", "mean"))
    print("\nBy collection-order quartile (row-weighted):")
    print(q_summary.to_string())

    corr = np.corrcoef(per_session["collection_order"], per_session["risky_rate"])[0, 1]
    print(f"\nPearson correlation(collection_order, per-session risky_rate) = {corr:.3f}")

    # ---- Step 2: does date/contamination ALONE predict risky? ------------
    print(f"\n{'='*78}\nSTEP 2: date/contamination-ONLY baseline (no real behavioural features)\n{'='*78}")
    df["days_since_start"] = (df["session_date"] - df["session_date"].min()).dt.days
    date_only_cols = ["days_since_start", "rag_contaminated"]
    X = df[date_only_cols].apply(pd.to_numeric, errors="coerce")
    X["rag_contaminated"] = X["rag_contaminated"].astype(float)
    y = df["risky"]
    groups = df["participant_id"]

    gkf = GroupKFold(n_splits=5)
    results = {}
    for name, ctor in [
        ("LogisticRegression", lambda: LogisticRegression(max_iter=1000, class_weight="balanced")),
        ("RandomForest", lambda: RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE)),
    ]:
        bal_accs, aucs = [], []
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
            m = ctor()
            m.fit(X_train_s, y_train)
            pred = m.predict(X_test_s)
            proba = m.predict_proba(X_test_s)[:, 1]
            bal_accs.append(balanced_accuracy_score(y_test, pred))
            aucs.append(roc_auc_score(y_test, proba))
        results[name] = (np.mean(bal_accs), np.mean(aucs))
        print(f"  [{name}] date+contamination-only: balanced_acc={np.mean(bal_accs):.4f}, AUROC={np.mean(aucs):.4f}")

    date_only_auroc = max(v[1] for v in results.values())

    # ---- Step 3: does behaviour-only survive without rag_contaminated, and
    #              under a time-ordered (not random-participant) split? -------
    print(f"\n{'='*78}\nSTEP 3: behaviour-only re-tested - feature removed, and time-ordered split\n{'='*78}")

    def eval_groupkfold(X, y, groups, ctor, label):
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
            m = ctor()
            m.fit(X_train_s, y_train)
            pred = m.predict(X_test_s)
            proba = m.predict_proba(X_test_s)[:, 1]
            bal_accs.append(balanced_accuracy_score(y_test, pred))
            f1s.append(f1_score(y_test, pred, zero_division=0))
            aucs.append(roc_auc_score(y_test, proba))
        print(f"  [{label}] balanced_acc={np.mean(bal_accs):.4f}, F1={np.mean(f1s):.4f}, AUROC={np.mean(aucs):.4f} "
              f"(folds used={len(bal_accs)})")
        return np.mean(bal_accs), np.mean(aucs)

    # 3a: original behaviour-only (with rag_contaminated) - reproduce for reference
    X_full = df[BEHAV_COLS].apply(pd.to_numeric, errors="coerce")
    X_full["ai_help_used"] = X_full["ai_help_used"].astype(float)
    X_full["rag_contaminated"] = X_full["rag_contaminated"].astype(float)
    eval_groupkfold(X_full, y, groups, lambda: RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE),
                     "3a RandomForest, behaviour-only WITH rag_contaminated (reference, = D037's number)")

    # 3b: behaviour-only WITHOUT rag_contaminated (the suspected date-proxy feature)
    cols_no_contam = [c for c in BEHAV_COLS if c != "rag_contaminated"]
    X_no_contam = df[cols_no_contam].apply(pd.to_numeric, errors="coerce")
    X_no_contam["ai_help_used"] = X_no_contam["ai_help_used"].astype(float)
    eval_groupkfold(X_no_contam, y, groups, lambda: RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE),
                     "3b RandomForest, behaviour-only WITHOUT rag_contaminated")
    if HAVE_XGB:
        eval_groupkfold(X_no_contam, y, groups, lambda: XGBClassifier(n_estimators=200, max_depth=4, eval_metric="logloss", random_state=RANDOM_STATE),
                         "3b XGBoost,       behaviour-only WITHOUT rag_contaminated")

    # 3c: time-ordered split - train on earliest N% of PARTICIPANTS (by their
    # session date), test on the latest, participant-level (no participant split
    # across the boundary, since each participant has exactly one session date).
    print("\n  -- time-ordered split (train=earliest 75% of participants by session date, test=latest 25%) --")
    participant_dates = df.groupby("participant_id")["session_date"].first().sort_values()
    n_part = len(participant_dates)
    cutoff = int(n_part * 0.75)
    train_participants = set(participant_dates.index[:cutoff])
    test_participants = set(participant_dates.index[cutoff:])
    print(f"  train participants: {len(train_participants)} (dates up to {participant_dates.iloc[cutoff-1].date()}), "
          f"test participants: {len(test_participants)} (dates from {participant_dates.iloc[cutoff].date()})")

    train_mask = df["participant_id"].isin(train_participants)
    test_mask = df["participant_id"].isin(test_participants)

    for cols, label in [(BEHAV_COLS, "WITH rag_contaminated"), (cols_no_contam, "WITHOUT rag_contaminated")]:
        Xc = df[cols].apply(pd.to_numeric, errors="coerce")
        if "ai_help_used" in Xc.columns:
            Xc["ai_help_used"] = Xc["ai_help_used"].astype(float)
        if "rag_contaminated" in Xc.columns:
            Xc["rag_contaminated"] = Xc["rag_contaminated"].astype(float)
        X_train, X_test = Xc[train_mask], Xc[test_mask]
        y_train, y_test = y[train_mask], y[test_mask]
        imputer = SimpleImputer(strategy="median")
        X_train_i = imputer.fit_transform(X_train)
        X_test_i = imputer.transform(X_test)
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train_i)
        X_test_s = scaler.transform(X_test_i)
        m = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE)
        m.fit(X_train_s, y_train)
        pred = m.predict(X_test_s)
        proba = m.predict_proba(X_test_s)[:, 1]
        bal_acc = balanced_accuracy_score(y_test, pred)
        auc = roc_auc_score(y_test, proba)
        print(f"  [time-ordered RandomForest, {label}] n_train={len(X_train)} n_test={len(X_test)} "
              f"train_risky_rate={y_train.mean():.3f} test_risky_rate={y_test.mean():.3f}: "
              f"balanced_acc={bal_acc:.4f}, AUROC={auc:.4f}")

    print(f"\n\nDate+contamination-only baseline AUROC was {date_only_auroc:.4f} "
          f"(chance = 0.5; original behaviour-only AUROC was 0.712)")


if __name__ == "__main__":
    main()
