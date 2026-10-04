#!/usr/bin/env python3
"""
Task 2 (D049+): ONE final, consolidated ablation table under the D045-corrected
label, every feature set x every applicable protocol, every cell with a 95% CI.

CI method: participant-level bootstrap (2000 resamples), not Wilson - Wilson is a
binomial-proportion interval (used elsewhere in this project for compliance RATES,
a simple success/failure count) and doesn't apply to AUROC/balanced-accuracy, which
are rank- and aggregate-based metrics. Bootstrap is the standard, correct choice for
these and is what "whichever you already used elsewhere, be consistent" sensibly
maps to here - the compliance-rate work's actual principle (don't report a point
estimate without an uncertainty interval) carries over; the specific formula can't.

Resampling is done over PARTICIPANTS, not rows, in every case - respects the
mandatory participant-level-independence rule even inside the CI computation itself
(resampling rows would treat within-participant correlation as independent evidence
and understate the interval).

Protocols:
  - "random" (D037 protocol): 5-fold participant-level GroupKFold, out-of-fold
    predictions pooled across all 5 folds, then bootstrap-resampled by participant.
  - "time" : single fixed chronological train/test split - global 75/25 boundary
    for feature sets without EEG, EEG's-own-window 75/25 boundary for sets that
    include EEG (D043's established reason: EEG collection stopped 2026-07-08, so
    no global boundary can place EEG-qualified participants on both sides).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from train_baselines import FEATURE_TABLE, BEHAV_COLS, GAZE_COLS, EEG_COLS, make_label, RANDOM_STATE
from check_time_confound import parse_date

N_BOOTSTRAP = 2000
RNG = np.random.default_rng(RANDOM_STATE)


def fit_predict(X_train, y_train, X_test):
    imputer = SimpleImputer(strategy="median")
    Xtr = imputer.fit_transform(X_train)
    Xte = imputer.transform(X_test)
    scaler = StandardScaler()
    Xtr = scaler.fit_transform(Xtr)
    Xte = scaler.transform(Xte)
    m = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE)
    m.fit(Xtr, y_train)
    pred = m.predict(Xte)
    proba = m.predict_proba(Xte)[:, 1]
    return pred, proba


def bootstrap_ci(participant_ids, y_true, y_pred, y_proba, n_boot=N_BOOTSTRAP):
    """Bootstrap by resampling the unique participant IDs (with replacement), then
    taking all rows belonging to each resampled participant - preserves
    within-participant row grouping in every resample. Indexed by pid up front
    (not re-filtered per resample) to keep 2000 iterations fast."""
    pid_arr = np.asarray(participant_ids)
    y_arr = np.asarray(y_true)
    pred_arr = np.asarray(y_pred)
    proba_arr = np.asarray(y_proba)
    unique_pids = np.unique(pid_arr)
    n_p = len(unique_pids)
    idx_by_pid = {pid: np.where(pid_arr == pid)[0] for pid in unique_pids}

    bal_accs, aucs = [], []
    for _ in range(n_boot):
        sample_pids = RNG.choice(unique_pids, size=n_p, replace=True)
        row_idx = np.concatenate([idx_by_pid[pid] for pid in sample_pids])
        y_s = y_arr[row_idx]
        if len(np.unique(y_s)) < 2:
            continue
        bal_accs.append(balanced_accuracy_score(y_s, pred_arr[row_idx]))
        try:
            aucs.append(roc_auc_score(y_s, proba_arr[row_idx]))
        except ValueError:
            pass
    bal_lo, bal_hi = (np.percentile(bal_accs, 2.5), np.percentile(bal_accs, 97.5)) if bal_accs else (None, None)
    auc_lo, auc_hi = (np.percentile(aucs, 2.5), np.percentile(aucs, 97.5)) if aucs else (None, None)
    return bal_lo, bal_hi, auc_lo, auc_hi, len(bal_accs)


def eval_random_split(sub, y, cols):
    X = sub[cols].apply(pd.to_numeric, errors="coerce")
    for c in ("ai_help_used", "rag_contaminated"):
        if c in X.columns:
            X[c] = X[c].astype(float)
    groups = sub["participant_id"]
    gkf = GroupKFold(n_splits=5)
    oof_pid, oof_y, oof_pred, oof_proba = [], [], [], []
    for train_idx, test_idx in gkf.split(X, y, groups):
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        if y_train.nunique() < 2 or y_test.nunique() < 2:
            continue
        pred, proba = fit_predict(X.iloc[train_idx], y_train, X.iloc[test_idx])
        oof_pid.extend(groups.iloc[test_idx].tolist())
        oof_y.extend(y_test.tolist())
        oof_pred.extend(pred.tolist())
        oof_proba.extend(proba.tolist())
    bal_acc = balanced_accuracy_score(oof_y, oof_pred)
    auc = roc_auc_score(oof_y, oof_proba)
    bal_lo, bal_hi, auc_lo, auc_hi, n_boot_ok = bootstrap_ci(oof_pid, oof_y, oof_pred, oof_proba)
    return {
        "protocol": "random (5-fold GroupKFold, OOF-pooled)", "n_rows": len(oof_y),
        "n_participants": len(set(oof_pid)), "balanced_acc": round(bal_acc, 4),
        "balanced_acc_ci": (round(bal_lo, 4), round(bal_hi, 4)) if bal_lo is not None else None,
        "auroc": round(auc, 4),
        "auroc_ci": (round(auc_lo, 4), round(auc_hi, 4)) if auc_lo is not None else None,
    }


def eval_time_split(sub, y, cols, train_mask, test_mask, cutoff_desc):
    X = sub[cols].apply(pd.to_numeric, errors="coerce")
    for c in ("ai_help_used", "rag_contaminated"):
        if c in X.columns:
            X[c] = X[c].astype(float)
    y_train, y_test = y[train_mask], y[test_mask]
    if y_train.nunique() < 2 or y_test.nunique() < 2:
        return {"protocol": f"time-ordered ({cutoff_desc})", "n_rows": int(test_mask.sum()),
                "n_participants": sub.loc[test_mask, "participant_id"].nunique(),
                "balanced_acc": None, "balanced_acc_ci": None, "auroc": None, "auroc_ci": None,
                "note": "single class in train or test"}
    pred, proba = fit_predict(X[train_mask], y_train, X[test_mask])
    bal_acc = balanced_accuracy_score(y_test, pred)
    auc = roc_auc_score(y_test, proba)
    test_pids = sub.loc[test_mask, "participant_id"]
    bal_lo, bal_hi, auc_lo, auc_hi, n_boot_ok = bootstrap_ci(test_pids, y_test, pred, proba)
    return {
        "protocol": f"time-ordered ({cutoff_desc})", "n_rows": int(test_mask.sum()),
        "n_participants": sub.loc[test_mask, "participant_id"].nunique(),
        "balanced_acc": round(bal_acc, 4),
        "balanced_acc_ci": (round(bal_lo, 4), round(bal_hi, 4)) if bal_lo is not None else None,
        "auroc": round(auc, 4),
        "auroc_ci": (round(auc_lo, 4), round(auc_hi, 4)) if auc_lo is not None else None,
        "n_boot_valid": n_boot_ok,
    }


def main():
    df = pd.read_csv(FEATURE_TABLE)
    df["gaze_missing"] = df["gaze_missing"].astype(bool)
    df["eeg_missing"] = df["eeg_missing"].astype(bool)
    df["session_date"] = df["session_dir"].apply(parse_date)
    df["risky"] = make_label(df)

    overall_rate = df["risky"].mean()
    print(f"Overall risky-decision base rate (corrected label): {overall_rate:.4f} "
          f"({df['risky'].sum()}/{len(df)}) [was 0.1906 under the old buggy label]\n")

    no_contam_behav = [c for c in BEHAV_COLS if c != "rag_contaminated"]

    feature_sets = [
        ("behaviour-only", BEHAV_COLS, None, False),
        ("behaviour-only (no rag_contaminated)", no_contam_behav, None, False),
        ("gaze-only", GAZE_COLS, "gaze_missing", False),
        ("EEG-only", EEG_COLS, "eeg_missing", True),
        ("behaviour+gaze", BEHAV_COLS + GAZE_COLS, "gaze_missing", False),
        ("behaviour+gaze (no rag_contaminated)", no_contam_behav + GAZE_COLS, "gaze_missing", False),
        ("behaviour+gaze+EEG", BEHAV_COLS + GAZE_COLS + EEG_COLS, "both", True),
        ("behaviour+gaze+EEG (no rag_contaminated)", no_contam_behav + GAZE_COLS + EEG_COLS, "both", True),
    ]

    # Global time-ordered cutoff (for sets without EEG)
    p_dates_all = df.groupby("participant_id")["session_date"].first().sort_values()
    cutoff_all = int(len(p_dates_all) * 0.75)
    train_p_all = set(p_dates_all.index[:cutoff_all])
    test_p_all = set(p_dates_all.index[cutoff_all:])

    rows_out = []
    for name, cols, missing_col, is_eeg_set in feature_sets:
        if missing_col == "both":
            sub = df[(~df["gaze_missing"]) & (~df["eeg_missing"])].copy()
        elif missing_col:
            sub = df[~df[missing_col]].copy()
        else:
            sub = df.copy()
        y = sub["risky"]

        print(f"{'='*90}\n{name}  (n_rows={len(sub)}, n_participants={sub['participant_id'].nunique()})\n{'='*90}")

        r_random = eval_random_split(sub, y, cols)
        r_random["feature_set"] = name
        print(f"  RANDOM split: balanced_acc={r_random['balanced_acc']} CI={r_random['balanced_acc_ci']}, "
              f"AUROC={r_random['auroc']} CI={r_random['auroc_ci']}")
        rows_out.append(r_random)

        if is_eeg_set:
            p_dates_eeg = sub.groupby("participant_id")["session_date"].first().sort_values()
            cutoff_eeg = int(len(p_dates_eeg) * 0.75)
            train_p = set(p_dates_eeg.index[:cutoff_eeg])
            test_p = set(p_dates_eeg.index[cutoff_eeg:])
            desc = "within EEG's own window, 75/25"
        else:
            train_p, test_p = train_p_all, test_p_all
            desc = "global 75/25"
        train_mask = sub["participant_id"].isin(train_p)
        test_mask = sub["participant_id"].isin(test_p)

        r_time = eval_time_split(sub, y, cols, train_mask, test_mask, desc)
        r_time["feature_set"] = name
        print(f"  TIME split ({desc}): balanced_acc={r_time['balanced_acc']} CI={r_time['balanced_acc_ci']}, "
              f"AUROC={r_time['auroc']} CI={r_time['auroc_ci']} (n_test_participants={r_time['n_participants']})")
        rows_out.append(r_time)
        print()

    out = pd.DataFrame(rows_out)
    out.to_csv("/Users/naman/Documents/MTP/backend/pipeline/final_ablation_table.csv", index=False)
    print("\nWrote final_ablation_table.csv")


if __name__ == "__main__":
    main()
