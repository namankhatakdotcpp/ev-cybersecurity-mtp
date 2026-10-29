# Gate 2 report: primary analysis (H1, B + exposure vs B + G + exposure)

Protocol: v1, frozen at commit `58e59c0e5fd2dc1cdd647336363984f349457ec7` (tag `protocol-v1`, D066). Code and config were committed before any analysis was run (`7e11442`, `a1e3211`, `5672700`); both runs below record code commit `5672700` with a clean tree. Runs: `results/registry.csv`, run folders `h1_claim_a_20261029_135241_323255` and `h1_claim_b_20261029_135319_404947`. Row-level artifacts (analysis table, out-of-fold predictions) are kept local and are not committed.

## Result in one paragraph

**H1 is not supported.** Claim A (association of the gaze block with choosing an attacked kiosk, beyond exposure, design covariates and behaviour): likelihood-ratio test chi-square 8.17 on 6 df, **p = 0.226**; the participant-block permutation p-value is 0.387. Claim B (out-of-sample gain): paired AUROC difference B+G minus B = **+0.005, 95% participant-bootstrap CI [-0.006, +0.015]**; the permuted-gaze control scores as well as the real gaze (permutation p = 0.49). By the rule fixed in Protocol section 2 the finding is: **no evidence that gaze adds to behaviour for this target at this sample size.** This is a valid negative result, consistent with the Gate 0 descriptive finding that gaze features are near chance among charge decisions. It is not evidence that gaze is irrelevant to attention or choice; it shows that these six head-local summary features add nothing detectable here.

## What was run (and what was not)

Run, as specified: T1 primary set (492 rows, 112 participants, 220 events), exposure offset `logit(p_exp)`, design covariates (incident mode, collection period), behaviour block (log window duration, `ai_help_used`, trial index), gaze block (six AOI-free features, `log1p` for counts, z-scored).
- Claim A: marginal-ML random-intercept logistic regression (Gauss-Hermite, 21 nodes), nested LRT with 6 df, alpha 0.05; robustness at 41 nodes; ordinary logistic LRT; participant-clustered robust Wald; within/between decomposition; participant-block permutation of the gaze block (1,000 permutations); sensitivity analyses E2, S3, S4.
- Claim B: ridge logistic regression with fixed offset, 5 outer folds x 20 repeats, participant-grouped and stratified by participant event-rate tertile, inner 3-fold selection of C on log-loss, all preprocessing inside training folds; 2,000-resample participant bootstrap; participant-block permutation with the full nested CV (200 permutations).

**Not run in this gate (by design):** S2 (early-window features, secondary), S1, S5-S8, the EEG set, the model grid (Gate 3), threshold-based metrics at pre-specified operating points, calibration curves and false-safe/false-warning rates (these need the full model comparison and are part of Gate 3). PR-AUC and Brier are reported below.

## Claim A

| Quantity | Value |
|---|---|
| Rows / participants / events | 492 / 112 / 220 |
| LRT, gaze block vs reduced model | chi-square 8.17, df 6, **p = 0.226** |
| Same, 41 quadrature nodes | 8.17, p = 0.226 |
| Same, ordinary logistic regression | 8.17, p = 0.226 (identical: see random-effect variance) |
| Participant-clustered robust Wald, 6 df | 8.43, p = 0.208 |
| Participant-block permutation of gaze (1,000), observed LRT 8.17 | **p = 0.387** (permuted LRT: mean 7.56, 95th percentile 13.25; 91 of 112 participants permuted, 21 had no same-stratum partner and stayed in place) |
| Random-intercept SD (both models) | estimated at the lower bound (1e-4), latent ICC about 0 |
| Within/between decomposition | within-participant gaze given between means: chi-square 5.70, df 6, p = 0.457; between-participant means given within: 10.26, df 6, p = 0.114; both vs reduced (12 df): 16.50, p = 0.169 |
| Cross-check of the engine | ordinary-logit coefficients agree with statsmodels GLM to 6e-15 |

**Coefficients (full model, per unit; Wald p-values are descriptive, not tests):** gaze features (per SD): fixations OR 1.60 (p 0.050), clusters 0.95, transitions 0.66 (p 0.091), transitions per fixation 0.94, dispersion 0.97, entropy 1.62 (p 0.074). They jointly explain nothing (LRT above); the opposite signs for fixations and transitions reflect collinearity, not separate effects. `ai_help_used` has OR 0.46 (Wald p 0.038), one of 14 terms and outside the tested hypothesis; treat as exploratory (it also rests on few rows with assistant requests).

**Sensitivity analyses (pre-specified as sensitivity, not tested hypotheses):**

| Analysis | Rows | Participants | Events | LRT chi-square (6 df) | p |
|---|---|---|---|---|---|
| E2 drop participants with duplicate folders | 472 | 107 | 213 | 7.12 | 0.310 |
| S3 drop RAG-contaminated sessions | 314 | 77 | 143 | 15.12 | **0.019** |
| S4 at least 200 valid gaze samples in the window | 490 | 112 | 220 | 6.89 | 0.331 |

S3 is nominally below 0.05 and must be reported. How to read it: it is one of three sensitivity runs (a Bonferroni illustration gives 0.058), it is a subset of the primary data and therefore not independent of the primary result, the protocol assigned no mechanism for gaze effects differing by assistant state, and the analysis removes 37 sessions that cluster in time (so it also changes the collection-period mix). It is a **hypothesis-generating lead only**. Following it up on these 126 participants would be a data-driven fork, so I recommend not pursuing it here; it can only be tested with new data under a pre-specified analysis (Protocol section 11).

## Claim B

Pooled out-of-fold performance, mean over 20 repeats, with participant-bootstrap 95% CIs (resampling participants, all their rows kept):

| Model | AUROC | PR-AUC | Brier |
|---|---|---|---|
| B0 (exposure + design only) | 0.627 [0.569, 0.681] | 0.555 [0.484, 0.631] | 0.2295 [0.2172, 0.2421] |
| B (+ behaviour) | 0.626 [0.569, 0.679] | 0.551 [0.482, 0.628] | 0.2305 [0.2180, 0.2431] |
| B+G (+ gaze) | 0.631 [0.574, 0.684] | 0.568 [0.496, 0.642] | 0.2314 [0.2187, 0.2441] |

| Paired difference in AUROC | Point | 95% CI | Bootstrap SE |
|---|---|---|---|
| **B+G minus B (headline)** | **+0.0046** | **[-0.0063, +0.0151]** | 0.0054 |
| B+G minus B0 | +0.0038 | [-0.0075, +0.0151] | 0.0058 |
| B minus B0 | -0.0009 | [-0.0095, +0.0089] | 0.0048 |

Across the 20 repeats the headline difference ranged from -0.006 to +0.014 (SD 0.004). **Participant-block permutation (200, full nested CV):** the model with permuted gaze blocks scored a mean AUROC of 0.6315 (95th percentile 0.646), at least as high as the real-gaze model (0.6308); permutation p = 0.49. Brier scores are slightly worse with each block added, and the baseline reference B0 (exposure alone) scores no worse than B or B+G.

## Deviations, limitations and things to know

1. **Strong shrinkage dominated the CV.** The inner loop chose the smallest C in the grid (0.01) in 95-99% of folds for every model, so the three models' predictions are nearly identical and the paired-difference SE (0.005) is much smaller than the 0.01-0.015 assumed in the Protocol's planning figures. A narrow CI therefore reflects regularisation to the offset-only model, not evidence that small true effects were excluded for an unpenalised model. The grid was fixed in advance and was not changed after seeing this. The unpenalised Claim A test (p 0.226) is the better-calibrated statement about sensitivity, and its power statement (odds ratio of about 1.29 per SD for a single feature, wider for a 6-df test) still stands.
2. **No participant clustering detected after exposure.** The random-intercept variance is estimated at zero in every fit, so the mixed model and ordinary logistic regression agree exactly. This was expected from the Gate 1 ICC estimate but means the "mixed model" claim adds nothing beyond logistic regression here.
3. **Z-scoring differs by stage.** Claim A uses a global z-score of the (outcome-free) predictors; Claim B fits transformations on each training fold only, as specified.
4. **Bootstrap scope.** CIs resample participants for fixed out-of-fold predictions; they reflect sampling variability of the evaluation, not refitting variability.
5. **Test expectation changes during engine validation (not engine changes):** the quadrature test originally demanded 1e-4 log-likelihood agreement between 15 and 41 nodes at a large random-effect variance; the actual difference was about 2e-3, so the test now states 5e-3 for 15 nodes and 1e-3 for the engine default of 21 nodes. The boundary test originally required an estimated SD below 0.2 on data simulated with SD 0; sampling variation gave 0.23, so it now requires agreement of the LRT statistics within 0.5. The engine code itself was not modified after the tests were written. pytest was pinned below 9 because 9.2.0 crashed on this Python (3.10.0rc2). Type-I error of the LRT under the null was 1-11% over 150 simulated sets, within the stated band.
6. **Descriptive context:** the exposure-only reference reaches AUROC 0.63 here, lower than the 0.659 pooled descriptive value in Gate 1 because the CV scores are out-of-fold and use only three distinct offset values.
7. **Dependence between analyses:** the sensitivity analyses and permutation tests reuse the same 492 rows; none is an independent replication.
8. **Reproducibility:** the feature table is a committed artefact; regenerating it still needs the Mac paths in `build_feature_table.py` made configurable (not done in this gate). The analysis code is config-driven and has 22 passing tests.

## Critical review block

- **What we learned.** With exposure, design covariates and behaviour in the model, the six gaze summary features add no detectable association or out-of-sample discrimination for the choice of an attacked kiosk at informative stations. Behaviour (window duration, `ai_help_used`, trial index) adds nothing over exposure either (B minus B0 about -0.001). There is no detectable participant clustering after exposure.
- **What changed.** The pipeline now has a tested estimation engine, a config-driven table builder checked against independent counts, a registry, and a frozen analysis that reproduces on demand. The earlier D052 gaze association is not supported once exposure is offset and the skip/charge path is removed.
- **What failed and why.** H1 failed to find an effect. Plausible reasons that this analysis cannot separate: (a) there is no effect; (b) the effect is too small for 220 events (below about 1.3 odds ratio per SD); (c) the head-local, whole-window summary features cannot capture where participants looked (no AOI mapping exists for this data); (d) the window includes the keypad stage (S2 not yet run).
- **Statistically defensible.** The two H1 conclusions (Claim A p = 0.226; Claim B delta AUROC +0.005 with CI including 0, permutation p about 0.49), the agreement of five analysis variants for the primary set, and the near-zero random-intercept variance.
- **Not defensible.** Any claim that gaze helps (or, strongly, that it cannot help); any reading of the S3 result beyond a lead; any interpretation of individual gaze coefficients; any statement about EEG, SLMs, the legacy `risky` target or online warning.
- **To test next.** Gate 3: the pre-specified model grid on B0, B, G, B+G with the same nested grouped CV, producing the master table programmatically, with threshold-based metrics and calibration. S2 (early-window) and S1 (gaze alone) belong with it.
- **Not to test.** Further variants of H1 on these data (feature subsets, other windows, other transforms, targeted follow-up of S3): each would be a fork. No deep learning.
