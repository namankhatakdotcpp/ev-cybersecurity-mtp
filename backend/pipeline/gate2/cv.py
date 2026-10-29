"""Claim B machinery (Protocol v1 section 4): repeated stratified participant-grouped nested CV with a ridge
logistic learner and a fixed exposure offset, participant-level bootstrap, and participant-block permutation.

All preprocessing (log1p, z-scoring), hyperparameter selection and any other fitted step happens inside the
training fold. Nothing here uses random state that is not derived from a seed in the config."""
import numpy as np
import pandas as pd

from . import mixed_logit as ml

BINARY = {"incident_mode", "period_jun", "period_jul_aug", "ai_help_used", "ai_help_early"}


class Transformer:
    """log1p on count columns, z-score on continuous columns (fitted on the training rows only), intercept first."""

    def __init__(self, cols, log1p_cols):
        self.cols, self.log1p = list(cols), set(log1p_cols)

    def _raw(self, df):
        X = df[self.cols].to_numpy(float).copy()
        for j, c in enumerate(self.cols):
            if c in self.log1p:
                X[:, j] = np.log1p(X[:, j])
        return X

    def fit(self, df):
        X = self._raw(df)
        self.mu = X.mean(axis=0)
        self.sd = X.std(axis=0)
        self.sd[self.sd == 0] = 1.0
        for j, c in enumerate(self.cols):
            if c in BINARY:
                self.mu[j], self.sd[j] = 0.0, 1.0
        return self

    def transform(self, df):
        X = (self._raw(df) - self.mu) / self.sd
        return np.c_[np.ones(len(X)), X]


# ---------------------------------------------------------------------------------------------------
# fold construction
# ---------------------------------------------------------------------------------------------------
def assign_folds(participants, rates, n_folds, rng):
    """Participant-grouped folds, stratified by tertile of the participant's event rate (tie-broken by a seeded
    jitter), dealt round-robin so fold sizes stay balanced. Returns {participant: fold}."""
    participants = np.asarray(participants)
    jitter = rng.random(len(participants)) * 1e-9
    order = np.argsort(np.asarray(rates, float) + jitter, kind="stable")
    tert = np.empty(len(participants), int)
    for k, chunk in enumerate(np.array_split(order, 3)):
        tert[chunk] = k
    fold_of, counter = {}, int(rng.integers(0, n_folds))
    for k in range(3):
        members = participants[tert == k]
        members = members[rng.permutation(len(members))]
        for m in members:
            fold_of[m] = counter % n_folds
            counter += 1
    return fold_of


def _participant_rates(df):
    g = df.groupby("participant_id")["y"].mean()
    return g.index.to_numpy(), g.to_numpy()


def _fit_predict(train, test, cols, log1p_cols, C):
    tr = Transformer(cols, log1p_cols).fit(train)
    f = ml.fit_logit(train["y"].to_numpy(float), tr.transform(train), train["offset"].to_numpy(float), l2=1.0 / C, unpenalized=[0])
    return f.predict_proba(tr.transform(test), test["offset"].to_numpy(float))


def _log_loss(y, p):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def select_C(train, cols, log1p_cols, C_grid, inner_folds, seed):
    rng = np.random.default_rng(seed)
    pids, rates = _participant_rates(train)
    fold_of = assign_folds(pids, rates, inner_folds, rng)
    fidx = train["participant_id"].map(fold_of).to_numpy()
    scores = []
    for C in C_grid:
        losses = []
        for k in range(inner_folds):
            a, b = train[fidx != k], train[fidx == k]
            if len(b) == 0 or len(a) == 0:
                continue
            losses.append(_log_loss(b["y"].to_numpy(float), _fit_predict(a, b, cols, log1p_cols, C)))
        scores.append(np.mean(losses))
    return C_grid[int(np.argmin(scores))], scores


def cv_predictions(df, model_cols, log1p_cols, cfg_b, repeats=None):
    """Return {model: array (R, n_rows)} of out-of-fold probabilities, plus the chosen C per (repeat, fold, model).
    `df` must be reset-indexed and contain participant_id, y, offset and every column named in model_cols."""
    df = df.reset_index(drop=True)
    seeds = cfg_b["repeat_seeds"][: (repeats or len(cfg_b["repeat_seeds"]))]
    n = len(df)
    oof = {m: np.full((len(seeds), n), np.nan) for m in model_cols}
    chosen = []
    pids, rates = _participant_rates(df)
    for r, seed in enumerate(seeds):
        rng = np.random.default_rng(seed)
        fold_of = assign_folds(pids, rates, cfg_b["outer_folds"], rng)
        fidx = df["participant_id"].map(fold_of).to_numpy()
        for k in range(cfg_b["outer_folds"]):
            train, test = df[fidx != k], df[fidx == k]
            for m, cols in model_cols.items():
                C, _ = select_C(train, cols, log1p_cols, cfg_b["C_grid"], cfg_b["inner_folds"], cfg_b["inner_seed_offset"] + 100 * r + k)
                oof[m][r, np.where(fidx == k)[0]] = _fit_predict(train, test, cols, log1p_cols, C)
                chosen.append(dict(repeat=r, fold=k, model=m, C=C))
    return oof, pd.DataFrame(chosen)


# ---------------------------------------------------------------------------------------------------
# weighted metrics and participant bootstrap (vectorised over resamples)
# ---------------------------------------------------------------------------------------------------
def _auc_weighted(y_sorted, w_sorted):
    """Mann-Whitney AUROC with row weights; `*_sorted` ordered by ascending score (ties are negligible for
    continuous probabilities and are counted as half only through the ordering)."""
    pos = w_sorted * y_sorted
    neg = w_sorted * (1 - y_sorted)
    cum_neg = np.cumsum(neg, axis=-1) - neg
    return (pos * cum_neg).sum(-1) / (pos.sum(-1) * neg.sum(-1))


def _ap_weighted(y_sorted_desc, w_sorted_desc):
    pos = w_sorted_desc * y_sorted_desc
    tp = np.cumsum(pos, axis=-1)
    fp = np.cumsum(w_sorted_desc * (1 - y_sorted_desc), axis=-1)
    prec = tp / np.maximum(tp + fp, 1e-12)
    return (prec * pos).sum(-1) / pos.sum(-1)


def metrics_for(y, P, w=None):
    """Mean over repeats of AUROC, average precision and Brier for predictions P of shape (R, n); `w` is an optional
    (B, n) matrix of row weights (bootstrap multiplicities). Returns arrays of shape (B,) or scalars."""
    y = np.asarray(y, float)
    R, n = P.shape
    W = np.ones((1, n)) if w is None else w
    auc = np.zeros(W.shape[0]); ap = np.zeros(W.shape[0]); br = np.zeros(W.shape[0])
    for r in range(R):
        o = np.argsort(P[r], kind="stable")
        auc += _auc_weighted(y[o][None, :], W[:, o])
        od = o[::-1]
        ap += _ap_weighted(y[od][None, :], W[:, od])
        br += (W * (P[r] - y) ** 2).sum(1) / W.sum(1)
    return auc / R, ap / R, br / R


def bootstrap(y, pid, preds, B, seed):
    """Participant-level bootstrap (participants resampled with replacement, all their rows kept). Returns per-model
    arrays of AUROC / AP / Brier over resamples and the paired differences for every model pair given in preds order."""
    rng = np.random.default_rng(seed)
    pid = np.asarray(pid)
    uniq, inv = np.unique(pid, return_inverse=True)
    counts = np.zeros((B, len(uniq)))
    for b in range(B):
        counts[b] = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
    W = counts[:, inv]                                        # B x n row multiplicities
    out = {m: dict(zip(("auroc", "ap", "brier"), metrics_for(y, P, W))) for m, P in preds.items()}
    return out


# ---------------------------------------------------------------------------------------------------
# participant-block permutation of the gaze block (Protocol section 4)
# ---------------------------------------------------------------------------------------------------
def permute_gaze_blocks(df, gaze_cols, strata_cols, rng):
    """Permute whole participant gaze blocks between participants with identical (strata, number of eligible rows).
    Returns the modified copy and the number of participants that could be permuted / could not."""
    df = df.reset_index(drop=True).copy()
    rows = df.groupby("participant_id").indices
    meta = {p: (tuple(df.loc[ix[0], strata_cols]) + (len(ix),)) for p, ix in rows.items()}
    buckets = {}
    for p, key in meta.items():
        buckets.setdefault(key, []).append(p)
    Z = df[gaze_cols].to_numpy().copy()
    new = Z.copy()
    moved = fixed = 0
    for key, members in buckets.items():
        if len(members) < 2:
            fixed += len(members)
            continue
        perm = rng.permutation(len(members))
        for a, b in zip(members, [members[i] for i in perm]):
            new[rows[a]] = Z[rows[b]]
        moved += len(members)
    df[gaze_cols] = new
    return df, moved, fixed
