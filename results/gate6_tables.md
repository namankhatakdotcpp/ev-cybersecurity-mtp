# Gate 6 (reduced): B0 descriptive tables (generated; do not edit by hand)

Primary set: 492 rows, 112 participants, 220 events. B0 = exposure offset + n_available + incident_mode + period dummies. Final-fit ridge C = 0.01 (same inner rule as Gate 2/3, selected on all rows). Intervals are 2.5th/97.5th percentiles of a participant bootstrap (2000 resamples); descriptive only, no test.

## Coefficients (log-odds of choosing an attacked kiosk; the exposure offset enters with coefficient 1 by construction)

| Term | Ridge coef. [95% CI] | Unpenalised coef. (cluster SE) | Odds ratio [95% CI] |
|---|---|---|---|
| const | -0.211 [-0.750, +0.384] | -0.285 (0.577) | 0.75 [0.26, 2.61] |
| n_available | +0.002 [-0.212, +0.201] | +0.011 (0.203) | 1.01 [0.66, 1.46] |
| incident_mode | -0.012 [-0.089, +0.064] | -0.080 (0.199) | 0.92 [0.62, 1.39] |
| period_jun | +0.006 [-0.045, +0.058] | +0.111 (0.344) | 1.12 [0.51, 2.20] |
| period_jul_aug | +0.027 [-0.051, +0.105] | +0.168 (0.198) | 1.18 [0.79, 1.78] |

n_available is per extra available kiosk (raw units). Free-slope check: if the logit of the exposure is entered as a covariate instead of an offset, its slope is 1.10 (cluster 95% CI 0.68 to 1.52); a slope of 1 means choice follows exposure as the offset assumes, 0 means choice ignores exposure.

## Error analysis of the Gate 3 out-of-fold B0 predictions

Observed minus B0 prediction and observed minus exposure (the rate expected from a random choice) with participant-bootstrap intervals; Brier score of B0 and of the exposure alone; within-stratum AUROC only with at least 20 events and 20 non-events.

| Family | Stratum | Rows | Participants | Events | Observed | Mean B0 | Mean exposure | Obs - B0 [95% CI] | Obs - exposure [95% CI] | Brier B0 | Brier exposure | AUROC B0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n_attacked | 1 | 357 | 104 | 134 | 0.375 | 0.381 | 0.428 | -0.006 [-0.054, +0.044] | -0.052 [-0.101, -0.003] | 0.228 | 0.230 | 0.553 |
| n_attacked | 2 | 135 | 76 | 86 | 0.637 | 0.621 | 0.667 | +0.016 [-0.079, +0.101] | -0.030 [-0.124, +0.055] | 0.232 | 0.232 | 0.442 |
| n_available | 2 | 202 | 89 | 91 | 0.450 | 0.451 | 0.500 | -0.000 [-0.068, +0.068] | -0.050 [-0.117, +0.018] | 0.249 | 0.250 | 0.420 |
| n_available | 3 | 290 | 101 | 129 | 0.445 | 0.444 | 0.489 | +0.000 [-0.057, +0.055] | -0.044 [-0.101, +0.010] | 0.216 | 0.217 | 0.655 |
| exposure_cell | 1 of 2 attacked | 202 | 89 | 91 | 0.450 | 0.451 | 0.500 | -0.000 [-0.068, +0.068] | -0.050 [-0.117, +0.018] | 0.249 | 0.250 | 0.420 |
| exposure_cell | 1 of 3 attacked | 155 | 83 | 43 | 0.277 | 0.291 | 0.333 | -0.013 [-0.089, +0.065] | -0.056 [-0.132, +0.022] | 0.201 | 0.204 | 0.438 |
| exposure_cell | 2 of 3 attacked | 135 | 76 | 86 | 0.637 | 0.621 | 0.667 | +0.016 [-0.079, +0.101] | -0.030 [-0.124, +0.055] | 0.232 | 0.232 | 0.442 |
| trial_index | 1-5 | 209 | 101 | 92 | 0.440 | 0.468 | 0.514 | -0.028 [-0.102, +0.047] | -0.074 [-0.148, +0.000] | 0.224 | 0.228 | 0.647 |
| trial_index | 6-10 | 154 | 74 | 76 | 0.494 | 0.435 | 0.482 | +0.058 [-0.016, +0.135] | +0.012 [-0.063, +0.088] | 0.241 | 0.237 | 0.612 |
| trial_index | 11-15 | 114 | 59 | 45 | 0.395 | 0.432 | 0.478 | -0.037 [-0.129, +0.049] | -0.083 [-0.175, +0.002] | 0.226 | 0.230 | 0.615 |
| trial_index | 16-20 | 15 | 15 | 7 | 0.467 | 0.387 | 0.433 | +0.080 [-0.154, +0.326] | +0.033 [-0.200, +0.278] | 0.209 | 0.202 | n/a |
| collection_period | apr | 185 | 38 | 79 | 0.427 | 0.445 | 0.494 | -0.018 [-0.079, +0.043] | -0.067 [-0.126, -0.006] | 0.225 | 0.228 | 0.643 |
| collection_period | jun | 44 | 15 | 20 | 0.455 | 0.441 | 0.489 | +0.013 [-0.144, +0.150] | -0.034 [-0.190, +0.101] | 0.254 | 0.254 | 0.519 |
| collection_period | jul_aug | 263 | 59 | 121 | 0.460 | 0.449 | 0.494 | +0.011 [-0.052, +0.070] | -0.034 [-0.095, +0.025] | 0.229 | 0.228 | 0.636 |
| incident_mode | 0 | 239 | 60 | 107 | 0.448 | 0.443 | 0.488 | +0.005 [-0.056, +0.062] | -0.040 [-0.100, +0.017] | 0.237 | 0.238 | 0.595 |
| incident_mode | 1 | 253 | 52 | 113 | 0.447 | 0.451 | 0.498 | -0.004 [-0.065, +0.055] | -0.051 [-0.112, +0.007] | 0.222 | 0.224 | 0.662 |
| all | primary set | 492 | 112 | 220 | 0.447 | 0.447 | 0.493 | +0.000 [-0.042, +0.043] | -0.046 [-0.088, -0.004] | 0.229 | 0.230 | 0.628 |
