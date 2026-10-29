"""Gate 3 benchmark machinery (Protocol v1 sections 4-7): learners (ridge logistic with offset, random forest,
histogram gradient boosting), nested participant-grouped CV that also fixes two operating points from the inner
validation predictions of each training fold, and weighted participant-bootstrap evaluation of every metric.

Everything fitted (transformations, hyperparameters, thresholds) is fitted inside the training fold. Random state
comes only from seeds in the configuration."""
import os
import numpy as np
import pandas as pd
import yaml
from scipy.special import expit, logit
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier

from . import mixed_logit as ml
from .config import REPO_ROOT, load_config
from .cv import Transformer, _participant_rates, assign_folds, metrics_for


def load_gate3(path=None):
    cfg = load_config()
    p = path or REPO_ROOT / "configs" / "gate3_grid.yaml"
    with open(p, "r", encoding="utf-8") as f:
        cfg["g3"] = yaml.safe_load(f)
    cfg["g3"]["_path"] = os.path.relpath(p, REPO_ROOT).replace(os.sep, "/")   # repo-relative: provenance must not embed a machine path
    return cfg


def set_columns(cfg, name):
    f = cfg["features"]
    return list(f["exposure"] + f["design"] + cfg["g3"]["sets"][name]["extra"])


# ---------------------------------------------------------------------------------------------------
# learners
# ---------------------------------------------------------------------------------------------------
def hp_grid(learner, g3):
    L = g3["learners"][learner]
    if learner == "ridge":
        return [dict(C=c) for c in L["C_grid"]]
    if learner == "rf":
        return [dict(max_depth=d, min_samples_leaf=m) for d in L["max_depth"] for m in L["min_samples_leaf"]]
    if learner == "hgb":
        return [dict(learning_rate=a, max_leaf_nodes=b) for a in L["learning_rate"] for b in L["max_leaf_nodes"]]
    raise ValueError(learner)


def detrend_within_fold(train, test, cols, spec):
    """Gate 6 deviation (D075): remove a linear trend on `spec["by"]` from each listed column present in `cols`, fitted on the training rows only.
    Default off: only active when g3 carries a `detrend_on` entry."""
    train, test = train.copy(), test.copy()
    for c in [c for c in spec["cols"] if c in cols]:
        slope, icpt = np.polyfit(train[spec["by"]].to_numpy(float), train[c].to_numpy(float), 1)
        for d in (train, test):
            d[c] = d[c].to_numpy(float) - (icpt + slope * d[spec["by"]].to_numpy(float))
    return train, test


def fit_predict(learner, hp, train, test, cols, log1p, g3, seed):
    if g3.get("detrend_on"):
        train, test = detrend_within_fold(train, test, cols, g3["detrend_on"])
    ytr = train["y"].to_numpy(float)
    if learner == "ridge":
        tr = Transformer(cols, log1p).fit(train)
        f = ml.fit_logit(ytr, tr.transform(train), train["offset"].to_numpy(float), l2=1.0 / hp["C"], unpenalized=[0])
        return f.predict_proba(tr.transform(test), test["offset"].to_numpy(float))
    tcols = list(cols) + ["offset"]                     # trees cannot take an offset, so logit(p_exp) is a feature
    tr = Transformer(tcols, log1p).fit(train)
    Xtr, Xte = tr.transform(train)[:, 1:], tr.transform(test)[:, 1:]
    if len(np.unique(ytr)) < 2:
        return np.full(len(test), float(ytr.mean()))
    L = g3["learners"][learner]
    if learner == "rf":
        m = RandomForestClassifier(n_estimators=L["n_estimators"], max_depth=hp["max_depth"], min_samples_leaf=hp["min_samples_leaf"],
                                   class_weight=L["class_weight"], random_state=seed, n_jobs=1)
    else:
        m = HistGradientBoostingClassifier(learning_rate=hp["learning_rate"], max_leaf_nodes=hp["max_leaf_nodes"], max_iter=L["max_iter"],
                                           min_samples_leaf=L["min_samples_leaf"], l2_regularization=L["l2_regularization"],
                                           early_stopping=L["early_stopping"], random_state=seed)
    m.fit(Xtr, ytr)
    return m.predict_proba(Xte)[:, list(m.classes_).index(1)]


def _log_loss(y, p):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


# ---------------------------------------------------------------------------------------------------
# operating points (chosen on inner validation predictions only)
# ---------------------------------------------------------------------------------------------------
def choose_thresholds(y, p, recall_target):
    y = np.asarray(y)
    p = np.asarray(p, float)
    if y.min() == y.max():
        t = float(np.median(p))
        return t, t
    cand = np.unique(p)
    pos, neg = p[y == 1], p[y == 0]
    rec = np.array([(pos >= t).mean() for t in cand])
    spec = np.array([(neg < t).mean() for t in cand])
    ba = (rec + spec) / 2
    t_a = float(np.median(cand[ba >= ba.max() - 1e-12]))
    ok = cand[rec >= recall_target]
    t_b = float(ok.max()) if len(ok) else float(cand.min())
    return t_a, t_b


# ---------------------------------------------------------------------------------------------------
# one repeat of nested CV
# ---------------------------------------------------------------------------------------------------
def run_repeat(df, model_cols, learner, cfg, r, log1p, with_const=False):
    cb, g3 = cfg["claim_b"], cfg["g3"]
    df = df.reset_index(drop=True)
    n = len(df)
    seed = cb["repeat_seeds"][r]
    rng = np.random.default_rng(seed)
    pids, rates = _participant_rates(df)
    fold_of = assign_folds(pids, rates, cb["outer_folds"], rng)
    fidx = df["participant_id"].map(fold_of).to_numpy()
    grid = hp_grid(learner, g3)
    base_seed = g3["learners"].get(learner, {}).get("seed_offset", 0) + 1000 * r
    names = list(model_cols) + (["CONST"] if with_const else [])
    res = {m: dict(oof=np.full(n, np.nan), pa=np.zeros(n, bool), pb=np.zeros(n, bool), chosen=[]) for m in names}
    target = g3["operating_points"]["recall_target"]
    for k in range(cb["outer_folds"]):
        tr_mask = fidx != k
        train, test = df[tr_mask], df[~tr_mask]
        te_idx = np.where(~tr_mask)[0]
        ipids, irates = _participant_rates(train)
        ifold = assign_folds(ipids, irates, cb["inner_folds"], np.random.default_rng(cb["inner_seed_offset"] + 100 * r + k))
        ifidx = train["participant_id"].map(ifold).to_numpy()
        ytrain = train["y"].to_numpy(float)
        for m, cols in model_cols.items():
            best = None
            for hi, hp in enumerate(grid):
                ip = np.full(len(train), np.nan)
                for j in range(cb["inner_folds"]):
                    a, b = train[ifidx != j], train[ifidx == j]
                    if len(a) and len(b):
                        ip[ifidx == j] = fit_predict(learner, hp, a, b, cols, log1p, g3, base_seed + 100 * k + 10 * hi + j)
                loss = _log_loss(ytrain, ip)
                if best is None or loss < best[0] - 1e-12:
                    best = (loss, hi, hp, ip)
            _, hi, hp, ip = best
            t_a, t_b = choose_thresholds(ytrain, ip, target)
            p = fit_predict(learner, hp, train, test, cols, log1p, g3, base_seed + 100 * k + 99)
            res[m]["oof"][te_idx] = p
            res[m]["pa"][te_idx] = p >= t_a
            res[m]["pb"][te_idx] = p >= t_b
            res[m]["chosen"].append(dict(repeat=r, fold=k, model=m, **hp))
        if with_const:
            c = float(ytrain.mean())
            res["CONST"]["oof"][te_idx] = c
            res["CONST"]["pa"][te_idx] = False
            res["CONST"]["pb"][te_idx] = False
    return res


# ---------------------------------------------------------------------------------------------------
# weighted evaluation over (resampled) participants
# ---------------------------------------------------------------------------------------------------
def _confusion(y, pred, W):
    tp = (W * (y * pred)).sum(1)
    fn = (W * (y * (~pred))).sum(1)
    fp = (W * ((1 - y) * pred)).sum(1)
    tn = (W * ((1 - y) * (~pred))).sum(1)
    return tp, fn, fp, tn


def threshold_metrics(y, PRED, W):
    """Mean over repeats of balanced accuracy, precision, recall, specificity, F1, false-safe (= 1 - recall, events
    predicted low risk) and false-warning (= 1 - specificity, non-events predicted high risk)."""
    R = PRED.shape[0]
    out = {k: np.zeros(W.shape[0]) for k in ("balanced_accuracy", "precision", "recall", "specificity", "f1", "false_safe", "false_warning")}
    for r in range(R):
        tp, fn, fp, tn = _confusion(y, PRED[r], W)
        rec = tp / np.maximum(tp + fn, 1e-12)
        spec = tn / np.maximum(tn + fp, 1e-12)
        out["balanced_accuracy"] += (rec + spec) / 2
        out["precision"] += tp / np.maximum(tp + fp, 1e-12)
        out["recall"] += rec
        out["specificity"] += spec
        out["f1"] += 2 * tp / np.maximum(2 * tp + fp + fn, 1e-12)
        out["false_safe"] += 1 - rec
        out["false_warning"] += 1 - spec
    return {k: v / R for k, v in out.items()}


def calibration(y, P, W, iters=10):
    """Weighted calibration slope (intercept free) and calibration-in-the-large (slope fixed at 1) of the outcome on
    logit(prediction); mean over repeats. Vectorised Newton iterations over bootstrap weights."""
    R, n = P.shape
    B = W.shape[0]
    slope = np.zeros(B)
    citl = np.zeros(B)
    for r in range(R):
        z = logit(np.clip(P[r], 1e-6, 1 - 1e-6))
        a = np.zeros(B)
        b = np.ones(B)
        for _ in range(iters):
            mu = expit(a[:, None] + b[:, None] * z[None, :])
            w = W * mu * (1 - mu)
            ga, gb = (W * (y - mu)).sum(1), (W * (y - mu) * z).sum(1)
            haa, hab, hbb = w.sum(1), (w * z).sum(1), (w * z * z).sum(1)
            det = haa * hbb - hab ** 2
            det = np.where(np.abs(det) < 1e-9, np.nan, det)
            a = a + (hbb * ga - hab * gb) / det
            b = b + (-hab * ga + haa * gb) / det
        slope += b
        c = np.zeros(B)
        for _ in range(iters):
            mu = expit(c[:, None] + z[None, :])
            c = c + (W * (y - mu)).sum(1) / np.maximum((W * mu * (1 - mu)).sum(1), 1e-12)
        citl += c
    return slope / R, citl / R


def reliability(y, P, bins):
    out = []
    for r in range(P.shape[0]):
        o = np.argsort(P[r], kind="stable")
        chunks = np.array_split(o, bins)
        out.append([(P[r][c].mean(), y[c].mean()) for c in chunks])
    return np.mean(np.array(out), axis=0).tolist()


def bootstrap_weights(pid, B, seed):
    rng = np.random.default_rng(seed)
    uniq, inv = np.unique(np.asarray(pid), return_inverse=True)
    counts = np.zeros((B, len(uniq)))
    for b in range(B):
        counts[b] = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
    return counts[:, inv]


def evaluate(y, pid, runs, B, seed, bins=8):
    """runs: {model: dict(oof=(R,n), pa=(R,n) bool, pb=(R,n) bool)}. Returns point estimates, 95% CIs and the
    bootstrap draws needed for paired comparisons (draws keyed by model and metric)."""
    y = np.asarray(y, float)
    W = bootstrap_weights(pid, B, seed)
    ones = np.ones((1, len(y)))
    pt, ci, draws = {}, {}, {}
    q = lambda a: [float(np.nanquantile(a, 0.025)), float(np.nanquantile(a, 0.975))]
    for m, d in runs.items():
        P = d["oof"]
        met = {}
        for tag, w in (("pt", ones), ("bs", W)):
            auc, ap, br = metrics_for(y, P, w)
            cur = dict(auroc=auc, pr_auc=ap, brier=br)
            for op in ("a", "b"):
                tm = threshold_metrics(y, d["p" + op], w)
                cur.update({f"{k}_{op.upper()}": v for k, v in tm.items()})
            sl, ci_ = calibration(y, P, w)
            cur.update(calib_slope=sl, calib_in_the_large=ci_)
            met[tag] = cur
        pt[m] = {k: float(v[0]) for k, v in met["pt"].items()}
        ci[m] = {k: q(v) for k, v in met["bs"].items()}
        draws[m] = met["bs"]
        pt[m]["reliability"] = reliability(y, P, bins)
    return pt, ci, draws


def paired(draws, a, b, metric="auroc"):
    d = draws[a][metric] - draws[b][metric]
    return dict(mean=float(np.nanmean(d)), ci=[float(np.nanquantile(d, 0.025)), float(np.nanquantile(d, 0.975))],
                se=float(np.nanstd(d)), p_boot=float(min(1.0, 2 * min(np.nanmean(d <= 0), np.nanmean(d >= 0)))))
