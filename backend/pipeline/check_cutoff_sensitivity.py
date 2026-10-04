#!/usr/bin/env python3
"""
Split-cutoff sensitivity check on D045/D047's headline result: behaviour+gaze+EEG
(without rag_contaminated), time-ordered split within EEG's own collection window
(2026-04-21 to 2026-07-08, 56 participants). D045 used a single 75/25 cutoff
(42 train / 14 test participants); D047 showed the model-seed isn't the source of
fragility. This checks the OTHER thing a single fixed split can hide: whether the
result holds only for that one particular boundary, or across a range of
chronological cutoffs - participant-level throughout, never splitting a
participant's own rows across train/test.

Model seed is held fixed (RANDOM_STATE=42, D037's convention) so only the cutoff
varies - isolates split sensitivity from the seed sensitivity already checked in
D047.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from train_baselines import FEATURE_TABLE, BEHAV_COLS, GAZE_COLS, EEG_COLS, make_label, RANDOM_STATE
from check_time_confound import parse_date

COLS_NO_CONTAM = [c for c in BEHAV_COLS if c != "rag_contaminated"] + GAZE_COLS + EEG_COLS


def eval_at_cutoff(sub, y, p_dates, cutoff_frac):
    n = len(p_dates)
    cutoff = int(round(n * cutoff_frac))
    if cutoff < 2 or cutoff > n - 2:
        return None  # not enough participants on one side to fit/evaluate meaningfully
    train_p = set(p_dates.index[:cutoff])
    test_p = set(p_dates.index[cutoff:])
    train_mask = sub["participant_id"].isin(train_p)
    test_mask = sub["participant_id"].isin(test_p)

    y_train, y_test = y[train_mask], y[test_mask]
    if y_train.nunique() < 2 or y_test.nunique() < 2:
        return {"cutoff_frac": cutoff_frac, "n_train_p": len(train_p), "n_test_p": len(test_p),
                "n_train": int(train_mask.sum()), "n_test": int(test_mask.sum()),
                "train_risky": float(y_train.mean()) if len(y_train) else None,
                "test_risky": float(y_test.mean()) if len(y_test) else None,
                "balanced_acc": None, "auroc": None, "skipped": "single class in train or test"}

    X = sub[COLS_NO_CONTAM].apply(pd.to_numeric, errors="coerce")
    X_train, X_test = X[train_mask], X[test_mask]

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
    return {
        "cutoff_frac": cutoff_frac, "n_train_p": len(train_p), "n_test_p": len(test_p),
        "n_train": int(train_mask.sum()), "n_test": int(test_mask.sum()),
        "train_risky": round(float(y_train.mean()), 3), "test_risky": round(float(y_test.mean()), 3),
        "balanced_acc": round(balanced_accuracy_score(y_test, pred), 4),
        "auroc": round(roc_auc_score(y_test, proba), 4), "skipped": None,
    }


def main():
    df = pd.read_csv(FEATURE_TABLE)
    df["gaze_missing"] = df["gaze_missing"].astype(bool)
    df["eeg_missing"] = df["eeg_missing"].astype(bool)
    df["session_date"] = df["session_dir"].apply(parse_date)

    sub = df[(~df["gaze_missing"]) & (~df["eeg_missing"])].copy()
    y = make_label(sub)
    p_dates = sub.groupby("participant_id")["session_date"].first().sort_values()
    n = len(p_dates)
    print(f"EEG-qualified-with-gaze subset: {n} participants, "
          f"{p_dates.min().date()} to {p_dates.max().date()}\n")

    results = []
    # Sweep cutoff fraction from 50% to 90% train, in 5-point steps, plus D045's
    # original 75%.
    fracs = sorted(set([round(f, 2) for f in np.arange(0.50, 0.91, 0.05)] + [0.75]))
    for frac in fracs:
        r = eval_at_cutoff(sub, y, p_dates, frac)
        results.append(r)
        if r is None:
            print(f"cutoff={frac:.2f}: SKIPPED - not enough participants on one side")
            continue
        if r["skipped"]:
            print(f"cutoff={frac:.2f}: train_p={r['n_train_p']} test_p={r['n_test_p']} "
                  f"SKIPPED ({r['skipped']})")
            continue
        print(f"cutoff={frac:.2f}: train_p={r['n_train_p']} test_p={r['n_test_p']} "
              f"n_train={r['n_train']} n_test={r['n_test']} "
              f"train_risky={r['train_risky']} test_risky={r['test_risky']} -> "
              f"balanced_acc={r['balanced_acc']}, AUROC={r['auroc']}")

    valid = [r for r in results if r and r.get("auroc") is not None]
    if valid:
        aucs = np.array([r["auroc"] for r in valid])
        bal_accs = np.array([r["balanced_acc"] for r in valid])
        print(f"\nAcross {len(valid)} valid cutoffs: balanced_acc mean={bal_accs.mean():.4f} "
              f"std={bal_accs.std():.4f} min={bal_accs.min():.4f} max={bal_accs.max():.4f}")
        print(f"                                 AUROC        mean={aucs.mean():.4f} "
              f"std={aucs.std():.4f} min={aucs.min():.4f} max={aucs.max():.4f}")
        print(f"Cutoffs with AUROC > 0.5: {(aucs > 0.5).sum()}/{len(valid)}")

    pd.DataFrame(results).to_csv("/Users/naman/Documents/MTP/backend/pipeline/cutoff_sensitivity_results.csv", index=False)


if __name__ == "__main__":
    main()
