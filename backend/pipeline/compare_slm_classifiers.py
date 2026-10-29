#!/usr/bin/env python3
"""
SLM-vs-ML risk-classification comparison (D058).

This is new scope, not part of the originally proposed pipeline (the mid-sem
report's Step 12 uses an SLM ONLY to phrase an already-made risk decision -
see warning_system.py/risk_model.py - never to make the decision itself).
Nothing here changes that production design. This script asks a separate
question the user raised afterwards: if several SLMs were ASKED to classify
risk directly from the same features (zero-shot, no fine-tuning - none exists
anywhere in this project), how would they compare to the actual deployed ML
model on the same held-out rows?

Methodology, kept directly comparable to D050/D057 (same feature set, same
label, same participant-level discipline - no exceptions):
  - FEATURE_COLS = deployed model's exact columns (behaviour minus
    rag_contaminated, + the 6 AOI-free gaze features).
  - risky label = make_label() from train_baselines.py (D045-corrected:
    decision=="charge" & kiosk_attack in {"Cyber Attack","System Anomaly"}).
  - A single GroupKFold(5) fold (fold index 0, participant-level, the same
    deterministic split train_baselines.py/calibrate_risk_model.py use) is
    held out. The ML "baseline" row here is a FRESH RandomForest trained on
    the other 4 folds and scored on this fold alone - not the 5-fold-averaged
    D050 number - so the ML and SLM rows are scored on the IDENTICAL test
    rows. D050's own 5-fold-averaged numbers remain the project's standing
    citable baseline; this script's ML row is a same-fold comparison point,
    not a replacement for it.
  - Each SLM (run locally via Ollama - no API quota, no fine-tuning) is
    prompted zero-shot, once per test row, with the raw feature values and
    asked for a single 0/1 classification. No few-shot examples, no chain of
    thought requested - deliberately the simplest possible prompt, so a
    result is not an artifact of prompt engineering.
  - SLM outputs are parsed for a single 0/1 digit. Anything that does not
    parse is counted as a parse failure and EXCLUDED from that model's
    accuracy (not silently scored as wrong or right) - the failure rate is
    reported per model, not hidden.
  - AUROC is reported for the ML model only. A single zero-shot 0/1 answer
    from an LLM is not a calibrated probability, and no second quantity is
    requested from it to fake one - reporting an AUROC computed from a
    0/1 "probability" would overstate what was actually measured.

Run: /usr/bin/python3 compare_slm_classifiers.py [--n-rows N] [--save]
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from train_baselines import FEATURE_TABLE, PIPELINE_DIR, BEHAV_COLS, GAZE_COLS, make_label, RANDOM_STATE

FEATURE_COLS = [c for c in BEHAV_COLS if c != "rag_contaminated"] + GAZE_COLS
N_FOLDS = 5
OLLAMA_URL = "http://localhost:11434/api/generate"
MODELS = ["mistral:7b-instruct", "llama3.1:8b", "phi3:3.8b", "gemma2:9b", "qwen2.5:7b"]
RESULTS_PATH = os.path.join(PIPELINE_DIR, "model", "slm_comparison_results.json")

PROMPT_TEMPLATE = """You are a binary risk classifier for a VR EV-charging cybersecurity study. Given these session features, predict whether the driver charged at a COMPROMISED (risky) kiosk.

Features:
window_duration_s={window_duration_s}
ai_help_used={ai_help_used}
gaze_n_fixations={gaze_n_fixations}
gaze_n_clusters={gaze_n_clusters}
gaze_n_transitions={gaze_n_transitions}
gaze_transitions_per_fixation={gaze_transitions_per_fixation}
gaze_dispersion={gaze_dispersion}
gaze_entropy_bits={gaze_entropy_bits}

Respond with ONLY a single digit: 1 if this was a risky (charged at a compromised kiosk) decision, 0 if not. No explanation, no other text."""


def load_fold0():
    df = pd.read_csv(FEATURE_TABLE)
    df["gaze_missing"] = df["gaze_missing"].astype(bool)
    sub = df[~df["gaze_missing"]].copy()
    y_all = make_label(sub)
    X_all = sub[FEATURE_COLS].apply(pd.to_numeric, errors="coerce")
    X_all["ai_help_used"] = X_all["ai_help_used"].astype(float)
    groups = sub["participant_id"].reset_index(drop=True)
    X_all = X_all.reset_index(drop=True)
    y_all = y_all.reset_index(drop=True)

    gkf = GroupKFold(n_splits=N_FOLDS)
    splits = list(gkf.split(X_all, y_all, groups))
    train_idx, test_idx = splits[0]  # fold 0 - deterministic given GroupKFold + row order
    return X_all, y_all, groups, train_idx, test_idx


def ml_baseline(X_all, y_all, train_idx, test_idx):
    X_train, X_test = X_all.iloc[train_idx], X_all.iloc[test_idx]
    y_train, y_test = y_all.iloc[train_idx], y_all.iloc[test_idx]

    imputer = SimpleImputer(strategy="median")
    Xtr = imputer.fit_transform(X_train)
    Xte = imputer.transform(X_test)
    scaler = StandardScaler()
    Xtr = scaler.fit_transform(Xtr)
    Xte = scaler.transform(Xte)

    model = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE)
    model.fit(Xtr, y_train)
    pred = model.predict(Xte)
    classes = list(model.classes_)
    proba = model.predict_proba(Xte)[:, classes.index(1)]

    dc = DummyClassifier(strategy="most_frequent")
    dc.fit(np.zeros((len(y_train), 1)), y_train)
    maj_pred = dc.predict(np.zeros((len(y_test), 1)))

    return {
        "model": "RandomForest (same test fold, fresh fit on other 4 folds)",
        "n_test_rows": len(y_test),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_test, pred)), 4),
        "f1": round(float(f1_score(y_test, pred, zero_division=0)), 4),
        "auroc": round(float(roc_auc_score(y_test, proba)), 4),
        "parse_failure_rate": 0.0,
    }, {
        "model": "Majority-class baseline (same test fold)",
        "n_test_rows": len(y_test),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_test, maj_pred)), 4),
        "f1": round(float(f1_score(y_test, maj_pred, zero_division=0)), 4),
        "auroc": None,
        "parse_failure_rate": 0.0,
    }


def call_ollama(model_name, prompt, timeout=90):
    payload = json.dumps({
        "model": model_name, "prompt": prompt, "stream": False, "options": {"temperature": 0},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        return body.get("response", "")


def parse_binary(response):
    stripped = response.strip()
    m = re.search(r"[01]", stripped)
    if m:
        return int(m.group(0))
    return None


def evaluate_slm(model_name, X_test, y_test, verbose=True):
    preds, failures = [], 0
    t0 = time.time()
    for i, (_, row) in enumerate(X_test.iterrows()):
        prompt = PROMPT_TEMPLATE.format(**row.to_dict())
        try:
            raw = call_ollama(model_name, prompt)
            parsed = parse_binary(raw)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"    [{model_name}] row {i}: call failed ({e}) - counted as parse failure")
            parsed = None
        if parsed is None:
            failures += 1
        preds.append(parsed)
        if verbose and (i + 1) % 25 == 0:
            elapsed = time.time() - t0
            print(f"    [{model_name}] {i+1}/{len(X_test)} rows, {elapsed:.0f}s elapsed")

    elapsed = time.time() - t0
    valid_idx = [i for i, p in enumerate(preds) if p is not None]
    if not valid_idx:
        return {
            "model": model_name, "n_test_rows": len(y_test), "balanced_accuracy": None, "f1": None,
            "auroc": None, "parse_failure_rate": 1.0, "wall_time_s": round(elapsed, 1),
        }
    y_valid = y_test.iloc[valid_idx].to_numpy()
    pred_valid = np.array([preds[i] for i in valid_idx])
    return {
        "model": model_name,
        "n_test_rows": len(y_test),
        "n_scored": len(valid_idx),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_valid, pred_valid)), 4),
        "f1": round(float(f1_score(y_valid, pred_valid, zero_division=0)), 4),
        "auroc": None,
        "parse_failure_rate": round(1 - len(valid_idx) / len(preds), 4),
        "wall_time_s": round(elapsed, 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-rows", type=int, default=None,
                         help="cap the held-out fold to this many rows (for a quicker run) - "
                              "sampled deterministically (random_state=42), not cherry-picked")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    X_all, y_all, groups, train_idx, test_idx = load_fold0()
    X_test, y_test = X_all.iloc[test_idx].reset_index(drop=True), y_all.iloc[test_idx].reset_index(drop=True)
    n_participants_test = groups.iloc[test_idx].nunique()

    if args.n_rows and args.n_rows < len(X_test):
        rng = np.random.RandomState(RANDOM_STATE)
        sel = np.sort(rng.choice(len(X_test), size=args.n_rows, replace=False))
        X_test, y_test = X_test.iloc[sel].reset_index(drop=True), y_test.iloc[sel].reset_index(drop=True)

    print(f"Held-out fold 0: {len(X_test)} test rows, {n_participants_test} participants, "
          f"risky_rate={y_test.mean():.3f}\n")

    results = []
    # ML/majority baselines are fit on the fold-0 training rows and scored on exactly
    # X_test/y_test (post-subsampling if --n-rows was used) - the same rows every SLM sees.
    rf_result, maj_result = ml_baseline(
        pd.concat([X_all.iloc[train_idx], X_test]).reset_index(drop=True),
        pd.concat([y_all.iloc[train_idx], y_test]).reset_index(drop=True),
        np.arange(len(train_idx)),
        np.arange(len(train_idx), len(train_idx) + len(X_test)),
    )
    results.append(rf_result)
    results.append(maj_result)
    print(f"ML baseline (same rows): balanced_acc={rf_result['balanced_accuracy']}, "
          f"F1={rf_result['f1']}, AUROC={rf_result['auroc']}")
    print(f"Majority baseline (same rows): balanced_acc={maj_result['balanced_accuracy']}, "
          f"F1={maj_result['f1']}\n")

    for model_name in MODELS:
        print(f"-- Evaluating {model_name} on {len(X_test)} rows --")
        r = evaluate_slm(model_name, X_test, y_test)
        results.append(r)
        print(f"  [{model_name}] balanced_acc={r['balanced_accuracy']}, F1={r['f1']}, "
              f"parse_failure_rate={r['parse_failure_rate']}, wall_time_s={r['wall_time_s']}\n")

    print(f"\n{'='*90}\nSummary table\n{'='*90}")
    print(f"{'Model':<55}{'BalAcc':>8}{'F1':>8}{'AUROC':>8}{'FailRate':>10}")
    for r in results:
        auroc_str = f"{r['auroc']:.4f}" if r.get("auroc") is not None else "n/a"
        bal_str = f"{r['balanced_accuracy']:.4f}" if r.get("balanced_accuracy") is not None else "n/a"
        f1_str = f"{r['f1']:.4f}" if r.get("f1") is not None else "n/a"
        print(f"{r['model']:<55}{bal_str:>8}{f1_str:>8}{auroc_str:>8}{r['parse_failure_rate']:>10.4f}")

    if args.save:
        with open(RESULTS_PATH, "w") as f:
            json.dump({
                "held_out_fold": 0, "n_test_rows": len(X_test), "n_participants_test": n_participants_test,
                "risky_rate": round(float(y_test.mean()), 4), "results": results,
            }, f, indent=2)
        print(f"\nSaved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
