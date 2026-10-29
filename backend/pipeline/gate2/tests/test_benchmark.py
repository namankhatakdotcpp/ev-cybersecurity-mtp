import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, f1_score, precision_score, recall_score

from backend.pipeline.gate2 import benchmark as bm
from backend.pipeline.gate2.cv import metrics_for


def _toy(n_p=70, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n_p):
        for _ in range(int(rng.integers(2, 8))):
            x = float(rng.normal())
            off = float(rng.choice([-0.69, 0.0, 0.69]))
            y = int(rng.random() < 1 / (1 + np.exp(-(off + 0.8 * x))))
            rows.append(dict(participant_id=f"p{p:03d}", y=y, offset=off, a=x, b=float(rng.normal()), n_available=float(rng.integers(2, 4)),
                             incident_mode=int(p % 2), period_jun=int(p % 3 == 0), period_jul_aug=int(p % 3 == 1)))
    return pd.DataFrame(rows)


def _cfg():
    return dict(claim_b=dict(repeat_seeds=[1, 2, 3], outer_folds=5, inner_folds=3, inner_seed_offset=77),
                g3=dict(learners=dict(ridge=dict(C_grid=[0.1, 1.0]),
                                       rf=dict(n_estimators=40, max_depth=[3], min_samples_leaf=[5], class_weight=None, seed_offset=100),
                                       hgb=dict(learning_rate=[0.1], max_leaf_nodes=[4], max_iter=20, min_samples_leaf=10, l2_regularization=1.0,
                                                early_stopping=False, seed_offset=200)),
                        operating_points=dict(recall_target=0.8)))


def test_thresholds_are_chosen_from_inner_predictions_only_and_respect_recall_target():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 400)
    p = np.clip(0.4 + 0.25 * y + rng.normal(0, 0.15, 400), 0.01, 0.99)
    ta, tb = bm.choose_thresholds(y, p, 0.8)
    assert (p[y == 1] >= tb).mean() >= 0.8
    higher = np.unique(p[p > tb])
    if len(higher):                                   # tb is the LARGEST threshold that still keeps recall >= 0.8
        assert (p[y == 1] >= higher.min()).mean() < 0.8
    cand = np.unique(p)
    ba = [balanced_accuracy_score(y, p >= t) for t in cand]
    assert abs(balanced_accuracy_score(y, p >= ta) - max(ba)) < 0.02


def test_threshold_metrics_match_sklearn():
    rng = np.random.default_rng(2)
    y = rng.integers(0, 2, 250).astype(float)
    pred = rng.random((1, 250)) > 0.5
    m = bm.threshold_metrics(y, pred, np.ones((1, 250)))
    assert abs(m["balanced_accuracy"][0] - balanced_accuracy_score(y, pred[0])) < 1e-9
    assert abs(m["precision"][0] - precision_score(y, pred[0])) < 1e-9
    assert abs(m["recall"][0] - recall_score(y, pred[0])) < 1e-9
    assert abs(m["f1"][0] - f1_score(y, pred[0])) < 1e-9
    assert abs(m["false_safe"][0] - (1 - recall_score(y, pred[0]))) < 1e-9


def test_calibration_slope_is_one_for_perfectly_calibrated_large_sample():
    rng = np.random.default_rng(3)
    z = rng.normal(0, 1.2, 20000)
    p = 1 / (1 + np.exp(-z))
    y = (rng.random(20000) < p).astype(float)
    slope, citl = bm.calibration(y, p[None, :], np.ones((1, 20000)))
    assert abs(slope[0] - 1) < 0.08 and abs(citl[0]) < 0.08


def test_run_repeat_is_deterministic_for_each_learner_and_returns_complete_predictions():
    df = _toy()
    cfg = _cfg()
    cols = {"B0": ["n_available", "incident_mode"], "G": ["n_available", "incident_mode", "a", "b"]}
    for learner in ("ridge", "rf", "hgb"):
        r1 = bm.run_repeat(df, cols, learner, cfg, 0, [], with_const=True)
        r2 = bm.run_repeat(df, cols, learner, cfg, 0, [], with_const=True)
        for m in ("B0", "G", "CONST"):
            assert np.isfinite(r1[m]["oof"]).all()
            np.testing.assert_array_equal(r1[m]["oof"], r2[m]["oof"])
            np.testing.assert_array_equal(r1[m]["pa"], r2[m]["pa"])


def test_signal_model_beats_baseline_on_a_known_effect():
    df = _toy(120, seed=5)
    cfg = _cfg()
    cols = {"B0": ["n_available"], "G": ["n_available", "a"]}
    runs = {m: dict(oof=np.array([bm.run_repeat(df, cols, "ridge", cfg, r, [])[m]["oof"] for r in range(3)])) for m in cols}
    auc = {m: metrics_for(df["y"].to_numpy(float), runs[m]["oof"])[0][0] for m in cols}
    assert auc["G"] > auc["B0"] + 0.05


def test_bootstrap_evaluate_returns_ci_containing_point_estimate_and_paired_difference():
    df = _toy(80, seed=7)
    cfg = _cfg()
    cols = {"B0": ["n_available"], "G": ["n_available", "a"]}
    res = {r: bm.run_repeat(df, cols, "ridge", cfg, r, []) for r in range(3)}
    runs = {m: dict(oof=np.array([res[r][m]["oof"] for r in range(3)]), pa=np.array([res[r][m]["pa"] for r in range(3)]),
                    pb=np.array([res[r][m]["pb"] for r in range(3)])) for m in cols}
    pt, ci, draws = bm.evaluate(df["y"].to_numpy(float), df["participant_id"].to_numpy(), runs, 200, 9)
    for m in cols:
        assert ci[m]["auroc"][0] <= pt[m]["auroc"] <= ci[m]["auroc"][1]
    d = bm.paired(draws, "G", "B0")
    assert d["ci"][0] < d["ci"][1] and d["mean"] > 0
