"""Engine validation (Gate 2): simulation recovery, agreement with ordinary logistic regression and statsmodels,
quadrature convergence, gradient correctness, likelihood-ratio calibration under the null, boundary behaviour."""
import numpy as np
import pytest
import statsmodels.api as sm
from scipy.special import expit

from backend.pipeline.gate2 import mixed_logit as ml


def simulate(rng, n_clusters, size, beta, sigma, offset_scale=0.5, n_cov=None):
    p = len(beta)
    groups = np.repeat(np.arange(n_clusters), size)
    X = np.c_[np.ones(len(groups)), rng.normal(size=(len(groups), p - 1))]
    off = offset_scale * rng.normal(size=len(groups))
    b = rng.normal(scale=sigma, size=n_clusters)[groups] if sigma > 0 else 0.0
    y = rng.binomial(1, expit(off + X @ beta + b))
    return y, X, groups, off


def test_ordinary_logit_matches_statsmodels_glm_with_offset():
    rng = np.random.default_rng(1)
    y, X, g, off = simulate(rng, 150, 4, np.array([-0.3, 0.8, -0.5, 0.2]), 0.0)
    ours = ml.fit_logit(y, X, off)
    ref = sm.GLM(y, X, family=sm.families.Binomial(), offset=off).fit()
    assert ours.converged
    np.testing.assert_allclose(ours.coef, ref.params, atol=1e-6)
    assert abs(ours.loglik - ref.llf) < 1e-6


def test_mixed_with_sigma_fixed_tiny_equals_ordinary_logit():
    rng = np.random.default_rng(2)
    y, X, g, off = simulate(rng, 120, 5, np.array([0.1, 0.7, -0.4]), 0.0)
    ordf = ml.fit_logit(y, X, off)
    mixf = ml.fit_mixed_logit(y, X, g, off, sigma_fixed=1e-7)
    assert abs(mixf.loglik - ordf.loglik) < 1e-6
    np.testing.assert_allclose(mixf.coef, ordf.coef, atol=1e-4)


def test_gauss_hermite_node_convergence():
    rng = np.random.default_rng(3)
    y, X, g, off = simulate(rng, 100, 6, np.array([-0.2, 0.9, 0.3]), 1.3)
    # non-adaptive quadrature at a large sigma (1.3 simulated, about 1.5 estimated): the protocol minimum of 15
    # nodes is accurate to about 3e-3 log-likelihood units, the engine default of 21 to better than 1e-3.
    f15 = ml.fit_mixed_logit(y, X, g, off, n_nodes=15)
    f21 = ml.fit_mixed_logit(y, X, g, off, n_nodes=21)
    f41 = ml.fit_mixed_logit(y, X, g, off, n_nodes=41)
    assert abs(f15.loglik - f41.loglik) < 5e-3
    assert abs(f21.loglik - f41.loglik) < 1e-3
    assert abs(f21.sigma - f41.sigma) < 5e-3


def test_analytic_gradient_matches_finite_difference():
    rng = np.random.default_rng(4)
    y, X, g, off = simulate(rng, 40, 4, np.array([0.0, 0.5, -0.5]), 0.8)
    D = ml._Data(y, X, off, g)
    from numpy.polynomial.hermite import hermgauss
    z, w = hermgauss(21)
    logw = np.log(w)
    theta = np.array([0.1, 0.3, -0.2, np.log(0.9)])
    f0, g0 = ml._nll_and_grad(theta, D, z, logw)
    num = np.zeros_like(theta)
    for i in range(len(theta)):
        e = np.zeros_like(theta)
        e[i] = 1e-6
        num[i] = (ml._nll_and_grad(theta + e, D, z, logw)[0] - ml._nll_and_grad(theta - e, D, z, logw)[0]) / 2e-6
    np.testing.assert_allclose(g0, num, rtol=1e-5, atol=1e-5)


def test_recovers_known_parameters_in_a_large_simulation():
    rng = np.random.default_rng(5)
    beta = np.array([-0.4, 0.8, -0.6])
    y, X, g, off = simulate(rng, 1500, 5, beta, 1.0)
    f = ml.fit_mixed_logit(y, X, g, off)
    assert f.converged
    np.testing.assert_allclose(f.coef, beta, atol=0.12)
    assert abs(f.sigma - 1.0) < 0.12
    se = np.sqrt(np.diag(f.cov_coef))
    assert np.all(se > 0) and np.all(se < 0.15)


def test_unbiased_on_average_over_replications():
    beta = np.array([-0.2, 0.6])
    est = []
    for s in range(30):
        rng = np.random.default_rng(100 + s)
        y, X, g, off = simulate(rng, 250, 4, beta, 0.9)
        f = ml.fit_mixed_logit(y, X, g, off)
        est.append(np.append(f.coef, f.sigma))
    est = np.array(est)
    assert abs(est[:, 1].mean() - 0.6) < 0.05
    assert abs(est[:, 2].mean() - 0.9) < 0.12


def test_lrt_type_one_error_is_near_nominal_under_the_null():
    rejections = 0
    reps = 150
    for s in range(reps):
        rng = np.random.default_rng(1000 + s)
        y, X0, g, off = simulate(rng, 90, 5, np.array([-0.3, 0.6]), 0.6)
        Z = rng.normal(size=(len(y), 3))                  # three irrelevant covariates
        full = ml.fit_mixed_logit(y, np.c_[X0, Z], g, off)
        red = ml.fit_mixed_logit(y, X0, g, off)
        p = ml.likelihood_ratio_test(full.loglik, red.loglik, 3)["p"]
        rejections += p < 0.05
    rate = rejections / reps
    assert 0.01 <= rate <= 0.11, rate


def test_lrt_has_power_for_a_true_effect():
    hits = 0
    for s in range(40):
        rng = np.random.default_rng(2000 + s)
        y0, X0, g, off = simulate(rng, 120, 5, np.array([-0.3, 0.6]), 0.5)
        Z = rng.normal(size=(len(y0), 2))
        eta = off + X0 @ np.array([-0.3, 0.6]) + 0.6 * Z[:, 0] + rng.normal(scale=0.5, size=120)[g]
        y = rng.binomial(1, expit(eta))
        full = ml.fit_mixed_logit(y, np.c_[X0, Z], g, off)
        red = ml.fit_mixed_logit(y, X0, g, off)
        hits += ml.likelihood_ratio_test(full.loglik, red.loglik, 2)["p"] < 0.05
    assert hits / 40 > 0.8


def test_boundary_case_no_clustering_agrees_with_ordinary_lrt():
    rng = np.random.default_rng(6)
    y, X0, g, off = simulate(rng, 140, 4, np.array([-0.1, 0.5]), 0.0)
    Z = rng.normal(size=(len(y), 2))
    Z2 = np.c_[X0, Z]
    mf, mr = ml.fit_mixed_logit(y, Z2, g, off), ml.fit_mixed_logit(y, X0, g, off)
    of, orr = ml.fit_logit(y, Z2, off), ml.fit_logit(y, X0, off)
    lm = ml.likelihood_ratio_test(mf.loglik, mr.loglik, 2)
    lo = ml.likelihood_ratio_test(of.loglik, orr.loglik, 2)
    # data simulated with sigma = 0: the estimate is small but, by sampling variation, not exactly zero
    assert mf.sigma < 0.4
    assert abs(lm["stat"] - lo["stat"]) < 0.5


def test_ridge_logit_with_offset_shrinks_and_reduces_to_ordinary_when_lambda_is_zero():
    rng = np.random.default_rng(7)
    y, X, g, off = simulate(rng, 100, 4, np.array([0.0, 0.8, -0.8]), 0.0)
    f0 = ml.fit_logit(y, X, off, l2=0.0)
    f1 = ml.fit_logit(y, X, off, l2=0.0, unpenalized=[0])
    f_pen = ml.fit_logit(y, X, off, l2=20.0, unpenalized=[0])
    np.testing.assert_allclose(f0.coef, f1.coef, atol=1e-8)
    assert np.linalg.norm(f_pen.coef[1:]) < np.linalg.norm(f0.coef[1:])


def test_cluster_robust_covariance_is_positive_definite_and_close_to_model_based_without_clustering():
    rng = np.random.default_rng(8)
    y, X, g, off = simulate(rng, 200, 4, np.array([-0.2, 0.5, 0.2]), 0.0)
    f = ml.fit_logit(y, X, off)
    rob = ml.cluster_robust_cov(y, X, off, f, g)
    assert np.all(np.linalg.eigvalsh(rob) > 0)
    ratio = np.sqrt(np.diag(rob) / np.diag(f.cov))
    assert np.all((ratio > 0.7) & (ratio < 1.4))
