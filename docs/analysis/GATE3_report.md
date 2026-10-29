# Gate 3 report: ML benchmark (pre-specified grid, S1, S2, exploratory S8)

Protocol v1 frozen at `58e59c0` (tag `protocol-v1`, D066). Config `configs/gate3_grid.yaml` and all Gate 3 code were committed before any Gate 3 run (`0e1d1bd`, `4f9daf6`, `dca9470`); the runs record code commit `dca9470`. The tables below are generated programmatically from the registry into `results/master_table_gate3.md` (long form: `results/master_table_gate3_long.csv`); this report quotes only the headline figures, and the generated file is the reference.

## Result in one paragraph

**No model, and no modality set, does better than the exposure-only reference B0.** On the primary set (492 rows, 112 participants, 220 events) every pre-specified model sits at AUROC 0.59-0.63 with participant-bootstrap CIs of about +/-0.05, and no paired difference to B0 has a CI above zero. The best-looking number (ridge logistic regression with gaze, AUROC 0.633 vs 0.627 for B0) is a difference of +0.006 [-0.005, +0.017]. The more flexible learners are not better: random forest is nominally worse than ridge when behaviour or gaze is added (exploratory, FDR-adjusted p about 0.03-0.04), and gradient boosting is consistent with ridge but with worse calibration. S1 (gaze alone vs exposure baseline) and S2 (H1 on early-window features) are both null. The boosting challenger was not run because its entry criterion (a pre-specified model beating B0 with a CI above zero) was not met.

## What was run

- Learners: ridge logistic regression with the exposure offset, random forest (300 trees; grid over `max_depth` 3/6/10 and `min_samples_leaf` 5/20), `HistGradientBoostingClassifier` (grid over learning rate 0.03/0.1 and `max_leaf_nodes` 4/8, 150 iterations). Tree models receive `logit(p_exp)` as an ordinary feature because they cannot take an offset.
- Modality sets (exposure and design covariates always present): B0, B (+ window duration, `ai_help_used`, trial index), G (+ six gaze features), BG.
- Evaluation: 5-fold participant-grouped, stratified, nested CV, 20 repeats; inner 3-fold selection on pooled inner out-of-fold log-loss; all transformations, hyperparameters and thresholds fitted inside the training fold; CIs from the 2,000-resample participant bootstrap (same resamples for every model, so paired comparisons are valid). A constant training-fold event-rate prediction is included as the lowest reference.
- Operating points fixed on each training fold's inner validation predictions: **A** maximises balanced accuracy; **B** is the largest threshold that keeps recall at or above 0.80 (my reading of "smallest threshold reaching recall 0.80": the stricter threshold that still meets the recall target, hence the highest specificity at that recall). False-safe rate = 1 - recall; false-warning rate = 1 - specificity.
- S1: G vs B0 with ridge: 6-df LRT, paired AUROC, participant-block permutation of the gaze block (200, full nested CV). S2: first 5 s after `Reached` only, window duration dropped (the early-window `ai_help_early` replaces `ai_help_used`), 470 rows, 111 participants, 214 events (22 primary rows lost because the early window had no usable gaze features); LRT, paired AUROC, permutation. Holm adjustment is declared over {S1, S2, S5, S6}; S5 and S6 run later, so the adjusted values below are upper bounds at family size 4.
- Exploratory S8: random forest and boosting vs ridge on each set, paired bootstrap, Benjamini-Hochberg over 8 comparisons.

## Headline figures (see the generated tables for everything)

| Model | Set | AUROC [95% CI] | Brier | Calibration slope |
|---|---|---|---|---|
| Ridge | B0 | 0.627 [0.569, 0.681] | 0.230 | 1.05 [0.64, 1.49] |
| Ridge | B | 0.626 [0.569, 0.679] | 0.231 | 1.01 |
| Ridge | G | 0.633 [0.576, 0.686] | 0.231 | 1.00 |
| Ridge | BG | 0.631 [0.574, 0.684] | 0.231 | 0.97 |
| Random forest | B0 / B / G / BG | 0.626 / 0.605 / 0.605 / 0.591 | 0.235-0.242 | 0.87-0.94 |
| Boosting | B0 / B / G / BG | 0.620 / 0.610 / 0.619 / 0.609 | 0.237-0.241 | 0.61-0.73 |

- **Paired differences to B0 (AUROC, CI):** ridge: B -0.001 [-0.009, +0.009], G +0.006 [-0.005, +0.017], BG +0.004 [-0.007, +0.015]. Random forest: B -0.021 [-0.039, -0.003], BG -0.035 [-0.063, -0.006] (worse than B0). Boosting: all CIs span zero. Ridge BG minus B (the H1 contrast): +0.004 [-0.006, +0.015], the Gate 2 result reproduced exactly.
- **Calibration:** ridge slopes are close to 1 (all CIs include 1, but they are wide, about 0.6-1.5), calibration-in-the-large is about 0 for all models; boosting is over-confident (slopes 0.61-0.73, CIs below 1), as is random forest to a lesser degree.
- **Operating point B (recall about 0.80):** for ridge the false-warning rate is 0.59-0.61 for every set (so about six in ten non-risky choices would trigger a warning); for random forest 0.60-0.69 and for boosting 0.62-0.74, i.e. no model improves on B0 and the tree models with extra features are worse. At operating point A all models have balanced accuracy 0.57-0.60 (recall 0.52-0.64, false-warning 0.35-0.48). No operating point is described as validated.
- **S1:** LRT chi-square 7.80 (df 6), p = 0.253; delta AUROC +0.006 [-0.005, +0.017]; permutation p = 0.453; provisional Holm upper bound 1.0.
- **S2:** LRT chi-square 4.65 (df 6), p = 0.590; delta AUROC BGE minus BE -0.002 [-0.011, +0.007]; permutation p = 0.796; provisional Holm upper bound 1.0. The result for the "keypad stage" concern is therefore: restricting to the first 5 s does not reveal a gaze effect either.
- **S8 (exploratory):** random forest minus ridge: B -0.022 [-0.037, -0.005], G -0.028 [-0.050, -0.006], BG -0.039 [-0.063, -0.015] (FDR 0.037, 0.037, 0.032); B0 -0.001 (FDR 0.91). Boosting minus ridge: all FDR above 0.14. In plain terms, adding flexibility is not helpful here and, for random forest, is likely harmful.

## Deviations, limitations and things to know

1. **Choices made in the config before running (logged as D068):** the gradient-boosting grid and iteration count, the random-forest grid values, the interpretation of operating point B, the Holm family size, and the S2 definition (5 s window, `ai_help_early`, minimum window 5 s, rows requiring computable early gaze features). The frozen protocol left these open; none was changed after seeing a Gate 3 result.
2. **Inner selection rule:** Gate 3 pools the inner out-of-fold predictions and selects on their log-loss (needed to fix thresholds from the same predictions); Gate 2 averaged the per-fold losses. The ridge results are identical to Gate 2 to the printed precision, so this changed nothing for the primary comparison.
3. **Grid boundaries again.** Ridge chose the smallest C (0.01) in 95-99% of folds; boosting chose the smallest learning rate and the smaller trees in 98-100% of folds for sets B, G and BG. Both are at the weakest edge of their grid, which is what a problem without signal beyond the offset looks like. The grids were fixed in advance and not extended; a wider grid would change little about the conclusion, but that was not tested.
4. **Strong shrinkage makes comparisons optimistic about precision.** The narrow paired CIs for ridge arise because the predictions of the four sets are nearly identical; for the tree learners the CIs are about twice as wide.
5. **The constant-rate reference** is a reference for Brier and PR-AUC only. Its AUROC and calibration slope are not meaningful (a constant gives AUROC 0.5 in principle, and the training-fold event rate varies against the held-out fold's, which pushes the pooled value below 0.5 by construction), so the generated table shows n/a.
6. **Calibration slopes** have wide CIs on 492 rows; "close to 1" means "not distinguishable from 1", not "well calibrated".
7. **Permutation tests** for S1 and S2 use the ridge learner only; no permutation test was run for the tree learners.
8. **Operating-point CIs** treat the out-of-fold predictions and the thresholds as fixed during bootstrapping (participants are resampled, not refitted).
9. **Dependence:** all analyses reuse the same 492 rows; nothing here is an independent replication.
10. The feature table is still a committed artefact (Mac paths in `build_feature_table.py` unchanged); S2 re-used the pipeline's fixation and clustering functions unchanged on a shorter window.

## Preview of the final-selection rubric (to be finalised in Gate 7, not a decision)

Best predictive model: by the protocol's tie-break, the simplest model within the CI of the best, which is the exposure-only ridge reference B0 (no set is distinguishable from it). Best safety-oriented model: none identifiable (no model lowers the false-safe rate at the recall target relative to B0 with a CI separation). Best deployment model: B0, but note it contains no behaviour or gaze signal and would not be a participant-specific warning. Best SLM: separate track (Gate 5).

## Critical review block

- **What we learned.** Across three learner families and four feature sets, nothing beats the layout-based exposure reference. The information a warning system could use (window duration, assistant use, gaze summaries) adds no detectable discrimination for the choice of an attacked kiosk, and flexible learners only add variance.
- **What changed.** The comparison is now reproducible from the registry with an automatic master table; the earlier ablations (legacy `risky`, skip/charge confounded) are superseded as evidence about modality value, as already recorded in D064/D067.
- **What failed and why.** The hope that boosting or random forests would find non-linear structure did not materialise; with 220 events and weak features they overfit (random forest) or are over-confident (boosting). The early-window variant (S2) removed the keypad-stage concern and the null stayed a null.
- **Statistically defensible.** Absence of detectable improvement over B0 for any of the 12 learner-set combinations (all paired CIs vs B0 span zero or are negative); ridge BG minus B reproduces H1's null; S1 and S2 nulls with p above 0.25; calibration slopes for ridge consistent with 1.
- **Not defensible.** Any claim that gaze or behaviour helps; any claim that tree models are inherently worse (exploratory, grid-limited); any operating point as "good" (all have false-warning rates of 35-74%); any statement about EEG, SLMs or online use.
- **To test next.** Gate 4: B, B+G, B+G+EEG on the identical matched EEG set (150 rows, 49 participants, 70 events), exploratory, with the selection-bias report; power there is limited (only large effects are detectable).
- **Not to test.** More learners or grids on this target, XGBoost/LightGBM (entry criterion not met), deep learning, S3 follow-ups.
