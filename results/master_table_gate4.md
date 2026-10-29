# Gate 4 master comparison, S6 matched EEG set (generated; do not edit by hand)

Matched set: 150 rows, 49 participants, 70 events; identical rows for every model. 5 x 20 participant-grouped nested CV, participant bootstrap CIs (2,000). Exploratory; descriptive power only. Runs: Ridge logistic (offset), primary: `g4_s6_ridge_20261029_143016_647045` (code 13b06c7); Random forest (exploratory): `g4_s6_rf_20261029_143147_663265` (code 13b06c7); HistGradientBoosting (exploratory): `g4_s6_hgb_20261029_143227_260197` (code 13b06c7).

### Table 1. Discrimination and calibration on the matched set

| Model | Set | AUROC | PR-AUC | Brier | Calibration slope |
|---|---|---|---|---|---|
| constant event rate (reference) | - | n/a | 0.427 [0.344, 0.546] | 0.251 [0.244, 0.259] | n/a |
| Ridge logistic (offset), primary | B0 | 0.618 [0.528, 0.696] | 0.569 [0.457, 0.683] | 0.236 [0.216, 0.257] | 0.87 [0.30, 1.45] |
| Ridge logistic (offset), primary | B | 0.610 [0.516, 0.692] | 0.563 [0.449, 0.683] | 0.236 [0.217, 0.258] | 0.86 [0.27, 1.47] |
| Ridge logistic (offset), primary | BG | 0.634 [0.535, 0.722] | 0.592 [0.468, 0.719] | 0.232 [0.211, 0.255] | 0.94 [0.31, 1.58] |
| Ridge logistic (offset), primary | BGE | 0.666 [0.556, 0.755] | 0.643 [0.503, 0.760] | 0.229 [0.205, 0.257] | 0.99 [0.29, 1.74] |
| Random forest (exploratory) | B0 | 0.600 [0.510, 0.683] | 0.538 [0.430, 0.660] | 0.243 [0.222, 0.263] | 0.68 [0.13, 1.33] |
| Random forest (exploratory) | B | 0.518 [0.436, 0.603] | 0.513 [0.404, 0.634] | 0.253 [0.238, 0.269] | 0.23 [-0.55, 1.02] |
| Random forest (exploratory) | BG | 0.494 [0.423, 0.569] | 0.469 [0.375, 0.592] | 0.255 [0.243, 0.267] | -0.09 [-1.02, 0.87] |
| Random forest (exploratory) | BGE | 0.545 [0.440, 0.639] | 0.532 [0.403, 0.667] | 0.250 [0.234, 0.266] | 0.46 [-0.61, 1.51] |
| HistGradientBoosting (exploratory) | B0 | 0.623 [0.525, 0.710] | 0.545 [0.432, 0.672] | 0.242 [0.214, 0.271] | 0.61 [0.18, 1.07] |
| HistGradientBoosting (exploratory) | B | 0.536 [0.448, 0.620] | 0.514 [0.395, 0.641] | 0.266 [0.241, 0.294] | 0.18 [-0.23, 0.61] |
| HistGradientBoosting (exploratory) | BG | 0.506 [0.431, 0.579] | 0.474 [0.377, 0.595] | 0.279 [0.255, 0.303] | 0.00 [-0.34, 0.35] |
| HistGradientBoosting (exploratory) | BGE | 0.607 [0.512, 0.687] | 0.586 [0.454, 0.715] | 0.252 [0.225, 0.284] | 0.42 [0.05, 0.81] |

### Table 2. Operating points, ridge

| Set | Operating point | Recall | Specificity | Precision | False-safe | False-warning |
|---|---|---|---|---|---|---|
| B0 | A | 0.47 [0.36, 0.57] | 0.72 [0.65, 0.78] | 0.60 [0.46, 0.71] | 0.53 [0.43, 0.64] | 0.28 [0.22, 0.35] |
| B0 | B | 0.79 [0.69, 0.87] | 0.36 [0.27, 0.46] | 0.52 [0.41, 0.62] | 0.21 [0.13, 0.31] | 0.64 [0.54, 0.73] |
| B | A | 0.46 [0.34, 0.56] | 0.75 [0.67, 0.81] | 0.62 [0.48, 0.73] | 0.54 [0.44, 0.66] | 0.25 [0.19, 0.33] |
| B | B | 0.79 [0.68, 0.88] | 0.38 [0.28, 0.48] | 0.53 [0.41, 0.63] | 0.21 [0.12, 0.32] | 0.62 [0.52, 0.72] |
| BG | A | 0.57 [0.47, 0.66] | 0.62 [0.54, 0.70] | 0.57 [0.44, 0.67] | 0.43 [0.34, 0.53] | 0.38 [0.30, 0.46] |
| BG | B | 0.79 [0.68, 0.89] | 0.39 [0.28, 0.49] | 0.53 [0.42, 0.63] | 0.21 [0.11, 0.32] | 0.61 [0.51, 0.72] |
| BGE | A | 0.56 [0.43, 0.66] | 0.70 [0.62, 0.77] | 0.62 [0.48, 0.73] | 0.44 [0.34, 0.57] | 0.30 [0.23, 0.38] |
| BGE | B | 0.79 [0.66, 0.89] | 0.37 [0.27, 0.46] | 0.52 [0.41, 0.62] | 0.21 [0.11, 0.34] | 0.63 [0.54, 0.73] |

### Table 3. Paired AUROC differences

| Model | Comparison | Delta AUROC | Bootstrap p |
|---|---|---|---|
| Ridge logistic (offset), primary | BGE minus BG (primary S6 contrast) | 0.031 [-0.013, 0.070] | 0.140 |
| Ridge logistic (offset), primary | BG minus B | 0.023 [-0.002, 0.047] | 0.071 |
| Ridge logistic (offset), primary | BGE minus B | 0.054 [0.006, 0.099] | 0.032 |
| Ridge logistic (offset), primary | BGE minus B0 | 0.047 [-0.007, 0.096] | 0.089 |
| Ridge logistic (offset), primary | BG minus B0 | 0.016 [-0.012, 0.042] | 0.266 |
| Ridge logistic (offset), primary | B minus B0 | -0.007 [-0.020, 0.005] | 0.224 |
| Random forest (exploratory) | BGE minus BG (primary S6 contrast) | 0.047 [-0.044, 0.133] | 0.292 |
| Random forest (exploratory) | BG minus B | -0.025 [-0.088, 0.044] | 0.475 |
| Random forest (exploratory) | BGE minus B | 0.023 [-0.091, 0.133] | 0.694 |
| Random forest (exploratory) | BGE minus B0 | -0.056 [-0.166, 0.051] | 0.334 |
| Random forest (exploratory) | BG minus B0 | -0.103 [-0.171, -0.035] | 0.004 |
| Random forest (exploratory) | B minus B0 | -0.078 [-0.120, -0.034] | 0.003 |
| HistGradientBoosting (exploratory) | BGE minus BG (primary S6 contrast) | 0.100 [0.009, 0.187] | 0.027 |
| HistGradientBoosting (exploratory) | BG minus B | -0.031 [-0.092, 0.035] | 0.344 |
| HistGradientBoosting (exploratory) | BGE minus B | 0.069 [-0.029, 0.163] | 0.170 |
| HistGradientBoosting (exploratory) | BGE minus B0 | -0.015 [-0.124, 0.093] | 0.776 |
| HistGradientBoosting (exploratory) | BG minus B0 | -0.115 [-0.193, -0.037] | 0.004 |
| HistGradientBoosting (exploratory) | B minus B0 | -0.084 [-0.138, -0.030] | 0.001 |

### Table 4. Tests of the EEG block (BGE vs BG)

| Test | Value |
|---|---|
| Participant-block permutation of the EEG block (CV AUROC of BGE; 200 permutations) | observed 0.666; permuted mean 0.654, 95th percentile 0.677; p = 0.219 (37 participants permuted, 12 left in place) |
| 17-df likelihood-ratio test (descriptive only; 70 events) | chi-square 29.85, p = 0.027; random-intercept SD 0.64 without EEG, 0.0001 with EEG |
| Provisional Holm upper bounds (family S1, S2, S5, S6) | S6: p 0.027 -> 0.110; S1: p 0.253 -> 0.760; S2: p 0.590 -> 1.000 |
