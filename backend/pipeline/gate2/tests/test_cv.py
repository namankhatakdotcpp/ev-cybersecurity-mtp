import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from backend.pipeline.gate2 import cv


def _toy(n_p=60, rng=None):
    rng = rng or np.random.default_rng(0)
    rows = []
    for p in range(n_p):
        k = int(rng.integers(1, 8))
        for _ in range(k):
            rows.append(dict(participant_id=f"p{p:03d}", y=int(rng.random() < 0.45), offset=float(rng.normal(0, 0.5)),
                             a=float(rng.normal()), b=float(rng.normal()), c=float(rng.integers(0, 9)), d=float(rng.normal()),
                             incident_mode=int(p % 2), period_jun=int(p % 3 == 0), period_jul_aug=int(p % 3 == 1)))
    return pd.DataFrame(rows)


def test_weighted_metrics_match_sklearn_without_ties():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 300)
    P = rng.random((3, 300))
    auc, ap, br = cv.metrics_for(y, P)
    ref_auc = np.mean([roc_auc_score(y, P[r]) for r in range(3)])
    ref_ap = np.mean([average_precision_score(y, P[r]) for r in range(3)])
    ref_br = np.mean([brier_score_loss(y, P[r]) for r in range(3)])
    assert abs(auc[0] - ref_auc) < 1e-9 and abs(ap[0] - ref_ap) < 1e-9 and abs(br[0] - ref_br) < 1e-9


def test_integer_weights_equal_row_replication():
    rng = np.random.default_rng(2)
    y = rng.integers(0, 2, 120)
    P = rng.random((2, 120))
    w = rng.integers(0, 4, (1, 120)).astype(float)
    auc_w, ap_w, br_w = cv.metrics_for(y, P, w)
    rep = np.repeat(np.arange(120), w[0].astype(int))
    auc_r = np.mean([roc_auc_score(y[rep], P[r][rep]) for r in range(2)])
    assert abs(auc_w[0] - auc_r) < 1e-3          # ties created by replication cost a little; weighted version is the reference


def test_folds_are_participant_grouped_and_balanced():
    df = _toy()
    pids = df.participant_id.unique()
    rates = df.groupby("participant_id").y.mean().loc[pids].to_numpy()
    f = cv.assign_folds(pids, rates, 5, np.random.default_rng(3))
    assert set(f) == set(pids)
    sizes = np.bincount(list(f.values()))
    assert sizes.max() - sizes.min() <= 1
    assert (df.groupby("participant_id").participant_id.apply(lambda s: len(set([f[s.iloc[0]]]))) == 1).all()


def test_transformer_uses_only_training_statistics():
    df = _toy()
    tr = cv.Transformer(["a", "c", "incident_mode"], ["c"]).fit(df.iloc[:100])
    X = tr.transform(df.iloc[100:])
    expected = (np.log1p(df.iloc[100:]["c"].to_numpy()) - tr.mu[1]) / tr.sd[1]
    np.testing.assert_allclose(X[:, 2], expected)
    np.testing.assert_allclose(X[:, 3], df.iloc[100:]["incident_mode"].to_numpy())     # binary column untouched
    assert np.all(X[:, 0] == 1.0)


def test_cv_predictions_deterministic_and_complete():
    df = _toy(50)
    cfg = dict(repeat_seeds=[11, 12], outer_folds=5, inner_folds=3, inner_seed_offset=500, C_grid=[0.1, 1.0])
    models = {"B0": ["incident_mode"], "BG": ["incident_mode", "a", "b"]}
    o1, ch1 = cv.cv_predictions(df, models, [], cfg)
    o2, ch2 = cv.cv_predictions(df, models, [], cfg)
    for m in models:
        assert np.isfinite(o1[m]).all()
        np.testing.assert_array_equal(o1[m], o2[m])
    assert len(ch1) == 2 * 5 * 2


def test_permutation_keeps_blocks_intact_and_moves_only_matching_participants():
    df = _toy(80)
    df["period"] = np.where(df.period_jun == 1, "jun", "other")
    out, moved, fixed = cv.permute_gaze_blocks(df, ["a", "b"], ["incident_mode", "period"], np.random.default_rng(4))
    assert moved + fixed == df.participant_id.nunique()
    assert np.allclose(np.sort(out["a"].to_numpy()), np.sort(df["a"].to_numpy()))
    rows = df.reset_index(drop=True).groupby("participant_id").indices
    before = {p: df.reset_index(drop=True).loc[ix, ["a", "b"]].to_numpy() for p, ix in rows.items()}
    after = {p: out.loc[ix, ["a", "b"]].to_numpy() for p, ix in rows.items()}
    pool = [tuple(map(tuple, v)) for v in before.values()]
    assert all(tuple(map(tuple, v)) in pool for v in after.values())                  # every block is an original block
    assert (out["y"].to_numpy() == df["y"].to_numpy()).all() and (out["offset"].to_numpy() == df["offset"].to_numpy()).all()
