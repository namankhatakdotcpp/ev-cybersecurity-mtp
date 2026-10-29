"""Random-intercept logistic regression by marginal maximum likelihood (Gate 2 engine, Protocol v1 section 3).

Model: y_ij ~ Bernoulli(expit(o_ij + x_ij.beta + b_i)),  b_i ~ N(0, sigma^2), clusters i = participants.
The marginal likelihood integrates b_i out by Gauss-Hermite quadrature (default 21 nodes, protocol minimum 15).
The offset o_ij is fixed (coefficient 1), as required for the exposure term logit(p_exp).

Also provides: ordinary and ridge-penalised logistic regression with offset (Newton/IRLS), used as the
sigma -> 0 reference, as the clustered-robust sensitivity fit, and as the regularised learner of Claim B.
Pure numpy/scipy; no random numbers are used inside the fitting routines.
"""
from dataclasses import dataclass, field

import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.optimize import minimize
from scipy.special import expit, log_expit, logsumexp
from scipy.stats import chi2

SIGMA_MIN = 1e-4
SIGMA_MAX = 10.0


# ----------------------------------------------------------------------------------------------------
# ordinary / ridge logistic regression with offset (Newton-Raphson)
# ----------------------------------------------------------------------------------------------------
@dataclass
class LogitFit:
    coef: np.ndarray
    loglik: float
    converged: bool
    n_iter: int
    cov: np.ndarray = field(default=None, repr=False)

    def predict_proba(self, X, offset=None):
        eta = X @ self.coef + (0.0 if offset is None else offset)
        return expit(eta)


def _loglik_logit(y, eta):
    return float(np.sum(y * log_expit(eta) + (1 - y) * log_expit(-eta)))


def fit_logit(y, X, offset=None, l2=0.0, unpenalized=None, max_iter=100, tol=1e-10):
    """Maximise  loglik(beta) - 0.5 * l2 * sum_{j penalised} beta_j^2  by Newton-Raphson with step halving.

    `unpenalized`: indices of coefficients that are not penalised (typically the intercept column).
    Returns the *penalised* fit; `loglik` is the plain (unpenalised) log-likelihood at the solution.
    """
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n, p = X.shape
    o = np.zeros(n) if offset is None else np.asarray(offset, float)
    pen = np.full(p, float(l2))
    if unpenalized is not None:
        pen[list(unpenalized)] = 0.0
    P = np.diag(pen)
    beta = np.zeros(p)

    def objective(b):
        return _loglik_logit(y, o + X @ b) - 0.5 * b @ P @ b

    f = objective(beta)
    converged = False
    it = 0
    for it in range(1, max_iter + 1):
        mu = expit(o + X @ beta)
        w = mu * (1 - mu)
        g = X.T @ (y - mu) - P @ beta
        H = (X * w[:, None]).T @ X + P
        try:
            step = np.linalg.solve(H + 1e-12 * np.eye(p), g)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, g, rcond=None)[0]
        t = 1.0
        while t > 1e-8:
            f_new = objective(beta + t * step)
            if f_new >= f - 1e-14:
                break
            t *= 0.5
        beta = beta + t * step
        if abs(f_new - f) < tol * (1 + abs(f)) and np.max(np.abs(t * step)) < 1e-7:
            f = f_new
            converged = True
            break
        f = f_new
    mu = expit(o + X @ beta)
    w = mu * (1 - mu)
    H = (X * w[:, None]).T @ X + P
    cov = np.linalg.pinv(H)
    return LogitFit(beta, _loglik_logit(y, o + X @ beta), converged, it, cov)


def cluster_robust_cov(y, X, offset, fit, groups):
    """Sandwich covariance (CR0 with the usual G/(G-1) small-sample factor) for an ordinary logit fit."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    o = np.zeros(len(y)) if offset is None else np.asarray(offset, float)
    mu = expit(o + X @ fit.coef)
    w = mu * (1 - mu)
    bread = np.linalg.pinv((X * w[:, None]).T @ X)
    _, gi = np.unique(groups, return_inverse=True)
    score = X * (y - mu)[:, None]
    S = np.zeros((gi.max() + 1, X.shape[1]))
    np.add.at(S, gi, score)
    meat = S.T @ S
    G = S.shape[0]
    return bread @ meat @ bread * (G / (G - 1))


# ----------------------------------------------------------------------------------------------------
# random-intercept logistic regression, marginal ML by Gauss-Hermite quadrature
# ----------------------------------------------------------------------------------------------------
@dataclass
class MixedFit:
    coef: np.ndarray
    sigma: float
    loglik: float
    converged: bool
    at_sigma_lower_bound: bool
    n_nodes: int
    cov_coef: np.ndarray = field(default=None, repr=False)
    message: str = ""


class _Data:
    """Rows sorted by cluster; holds cluster boundaries for reduceat."""

    def __init__(self, y, X, offset, groups):
        groups = np.asarray(groups)
        order = np.argsort(groups, kind="stable")
        self.order = order
        self.y = np.asarray(y, float)[order]
        self.X = np.asarray(X, float)[order]
        self.o = (np.zeros(len(order)) if offset is None else np.asarray(offset, float)[order])
        g_sorted = groups[order]
        _, self.start, self.count = np.unique(g_sorted, return_index=True, return_counts=True)
        self.gidx = np.repeat(np.arange(len(self.start)), self.count)
        self.n, self.p = self.X.shape
        self.G = len(self.start)


def _nll_and_grad(theta, D, z, logw, sigma_fixed=None):
    """Negative marginal log-likelihood and gradient w.r.t. (beta, log sigma)."""
    p = D.p
    beta = theta[:p]
    sigma = sigma_fixed if sigma_fixed is not None else float(np.exp(theta[p]))
    lin = D.o + D.X @ beta                                     # n
    b = np.sqrt(2.0) * sigma * z                               # K
    eta = lin[:, None] + b[None, :]                            # n x K
    ll = D.y[:, None] * log_expit(eta) + (1 - D.y[:, None]) * log_expit(-eta)
    cl = np.add.reduceat(ll, D.start, axis=0)                  # G x K
    a = cl + logw[None, :]
    lse = logsumexp(a, axis=1)                                 # G
    nll = -float(np.sum(lse) - 0.5 * D.G * np.log(np.pi))
    r = np.exp(a - lse[:, None])                               # posterior weights over nodes, G x K
    resid = D.y[:, None] - expit(eta)                          # n x K
    rg = r[D.gidx]                                             # n x K
    S = np.sum(rg * resid, axis=1)                             # n
    g_beta = -(D.X.T @ S)
    if sigma_fixed is not None:
        return nll, g_beta
    g_sigma = -float(np.sum(rg * resid * (np.sqrt(2.0) * z)[None, :])) * sigma   # d/dlog(sigma)
    return nll, np.append(g_beta, g_sigma)


def fit_mixed_logit(y, X, groups, offset=None, n_nodes=21, sigma_fixed=None, max_iter=500):
    """Marginal-ML fit. `X` must contain an intercept column if one is wanted. Returns MixedFit."""
    D = _Data(y, X, offset, groups)
    z, w = hermgauss(n_nodes)
    logw = np.log(w)
    init = fit_logit(D.y, D.X, D.o)
    p = D.p
    results = []
    if sigma_fixed is not None:
        res = minimize(lambda t: _nll_and_grad(t, D, z, logw, sigma_fixed), init.coef, jac=True, method="L-BFGS-B",
                       options=dict(maxiter=max_iter, ftol=1e-13, gtol=1e-8))
        cov = _cov_coef(res.x, D, z, logw, sigma_fixed)
        return MixedFit(res.x, float(sigma_fixed), -res.fun, bool(res.success), False, n_nodes, cov, res.message)
    bounds = [(None, None)] * p + [(np.log(SIGMA_MIN), np.log(SIGMA_MAX))]
    for s0 in (0.5, 0.1, 1.5):
        t0 = np.append(init.coef, np.log(s0))
        res = minimize(lambda t: _nll_and_grad(t, D, z, logw), t0, jac=True, method="L-BFGS-B", bounds=bounds,
                       options=dict(maxiter=max_iter, ftol=1e-13, gtol=1e-8))
        results.append(res)
    res = min(results, key=lambda r: r.fun)
    sigma = float(np.exp(res.x[p]))
    cov = _cov_coef(res.x, D, z, logw, None)
    return MixedFit(res.x[:p], sigma, -res.fun, bool(res.success), bool(res.x[p] <= np.log(SIGMA_MIN) + 1e-6),
                    n_nodes, cov, res.message)


def _cov_coef(theta, D, z, logw, sigma_fixed, eps=1e-5):
    """Observed-information covariance of beta from finite differences of the analytic gradient."""
    k = len(theta)
    Hs = np.zeros((k, k))
    for i in range(k):
        e = np.zeros(k)
        e[i] = eps
        gp = _nll_and_grad(theta + e, D, z, logw, sigma_fixed)[1]
        gm = _nll_and_grad(theta - e, D, z, logw, sigma_fixed)[1]
        Hs[:, i] = (gp - gm) / (2 * eps)
    Hs = 0.5 * (Hs + Hs.T)
    try:
        cov = np.linalg.inv(Hs)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(Hs)
    return cov[:D.p, :D.p]


def likelihood_ratio_test(ll_full, ll_reduced, df):
    stat = 2.0 * (ll_full - ll_reduced)
    return dict(stat=float(stat), df=int(df), p=float(chi2.sf(max(stat, 0.0), df)))
