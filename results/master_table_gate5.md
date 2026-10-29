# Gate 5 SLM benchmark: master tables (generated from the registry; do not edit by hand)

Scenario set v1 (approved): 240 stations, 599 available kiosks, quota-sampled; per-class results are the unit of interpretation and overall numbers are not prevalence-weighted. Scoring per `docs/protocol/GATE5_scoring_spec.md`: UNSAFE is the positive class; a failed reply counts as wrong on every kiosk it covers; false-safe and false-warning are always shown together; intervals on rates are Wilson 95% (nominal: kiosks within a station are not independent); comparisons with the best reference predictor use a scenario-level bootstrap (2000 resamples) and Holm adjustment over 10 comparisons (5 models x V1 and V2 excluding label-flagged images). A model is never described as detecting anything if it is flagged degenerate.

Runs: mistral:7b-instruct: `g5_slm_mistral_7b-instruct_20261029_171424_147876` (code unknown); llama3.1:8b: `g5_slm_llama3.1_8b_20261029_171424_179780` (code unknown); phi3:3.8b: `g5_slm_phi3_3.8b_20261029_171424_199310` (code unknown); gemma2:9b: `g5_slm_gemma2_9b_20261029_171424_218825` (code unknown); qwen2.5:7b: `g5_slm_qwen2.5_7b_20261029_171424_237838` (code unknown)


### Table 1. Format pilot (20 synthetic stations, no accuracy score)

| Model | Compliant replies | Failure categories | Flagged (< 90%) |
|---|---|---|---|
| mistral:7b-instruct | 0.95 [0.76, 0.99] (19/20) | {"missing_key": 1} | no |
| llama3.1:8b | 1.00 [0.84, 1.00] (20/20) | none | no |
| phi3:3.8b | 0.95 [0.76, 0.99] (19/20) | {"missing_key": 1} | no |
| gemma2:9b | 1.00 [0.84, 1.00] (20/20) | none | no |
| qwen2.5:7b | 1.00 [0.84, 1.00] (20/20) | none | no |

### Table 2a. Detection, V1 cue-free, all kiosks

| Model | Failed replies | Degenerate | False-safe (attacked judged SAFE) | False-warning (safe judged UNSAFE) | Balanced acc. | Best reference (bal. acc.) | Diff. vs best ref. [95% CI] | Holm p | Better than baseline |
|---|---|---|---|---|---|---|---|---|---|
| mistral:7b-instruct | 0.129 [0.093, 0.178] (31/240) | no | 0.880 [0.837, 0.912] | 0.214 [0.172, 0.263] | 0.453 | deepfake-image rule (0.730) | -0.277 [-0.324, -0.231] | 0.010 | no |
| llama3.1:8b | 0.000 [0.000, 0.016] (0/240) | no | 0.856 [0.811, 0.891] | 0.136 [0.102, 0.179] | 0.504 | deepfake-image rule (0.730) | -0.226 [-0.270, -0.184] | 0.010 | no |
| phi3:3.8b | 0.017 [0.006, 0.042] (4/240) | no | 0.787 [0.736, 0.830] | 0.182 [0.143, 0.229] | 0.516 | deepfake-image rule (0.730) | -0.215 [-0.261, -0.170] | 0.010 | no |
| gemma2:9b | 0.000 [0.000, 0.016] (0/240) | DEGENERATE (1% UNSAFE) | 0.993 [0.975, 0.998] | 0.003 [0.001, 0.018] | 0.502 | deepfake-image rule (0.730) | -0.229 [-0.264, -0.192] | 0.010 | no |
| qwen2.5:7b | 0.000 [0.000, 0.016] (0/240) | no | 0.653 [0.597, 0.705] | 0.295 [0.247, 0.349] | 0.526 | deepfake-image rule (0.730) | -0.205 [-0.253, -0.161] | 0.010 | no |
| reference: always SAFE | - | - | 1.000 [0.987, 1.000] | 0.000 [0.000, 0.012] | 0.500 | - | - | - | - |
| reference: always UNSAFE | - | - | 0.000 [0.000, 0.013] | 1.000 [0.988, 1.000] | 0.500 | - | - | - | - |
| reference: deepfake-image rule | - | - | 0.357 [0.305, 0.414] | 0.182 [0.143, 0.229] | 0.730 | - | - | - | - |
| reference: discount-badge rule | - | - | 0.777 [0.725, 0.821] | 0.201 [0.160, 0.250] | 0.511 | - | - | - | - |
| reference: random (expected) | - | - | 0.500 [0.443, 0.557] | 0.500 [0.445, 0.555] | 0.500 | - | - | - | - |

### Table 2b. Detection, V2 image descriptions, all kiosks

| Model | Failed replies | Degenerate | False-safe (attacked judged SAFE) | False-warning (safe judged UNSAFE) | Balanced acc. | Best reference (bal. acc.) | Diff. vs best ref. [95% CI] | Holm p | Better than baseline |
|---|---|---|---|---|---|---|---|---|---|
| mistral:7b-instruct | 0.275 [0.222, 0.335] (66/240) | no | 0.660 [0.604, 0.712] | 0.539 [0.483, 0.594] | 0.401 | deepfake-image rule (0.730) | -0.330 [-0.386, -0.273] | - | n/a (not in family) |
| llama3.1:8b | 0.025 [0.012, 0.053] (6/240) | no | 0.395 [0.341, 0.452] | 0.468 [0.413, 0.523] | 0.569 | deepfake-image rule (0.730) | -0.162 [-0.202, -0.123] | - | n/a (not in family) |
| phi3:3.8b | 0.075 [0.048, 0.115] (18/240) | no | 0.368 [0.314, 0.424] | 0.542 [0.486, 0.597] | 0.545 | deepfake-image rule (0.730) | -0.185 [-0.229, -0.144] | - | n/a (not in family) |
| gemma2:9b | 0.050 [0.029, 0.085] (12/240) | no | 0.296 [0.246, 0.350] | 0.750 [0.699, 0.795] | 0.477 | deepfake-image rule (0.730) | -0.253 [-0.291, -0.217] | - | n/a (not in family) |
| qwen2.5:7b | 0.025 [0.012, 0.053] (6/240) | no | 0.378 [0.324, 0.435] | 0.539 [0.483, 0.594] | 0.542 | deepfake-image rule (0.730) | -0.189 [-0.232, -0.148] | - | n/a (not in family) |
| reference: always SAFE | - | - | 1.000 [0.987, 1.000] | 0.000 [0.000, 0.012] | 0.500 | - | - | - | - |
| reference: always UNSAFE | - | - | 0.000 [0.000, 0.013] | 1.000 [0.988, 1.000] | 0.500 | - | - | - | - |
| reference: deepfake-image rule | - | - | 0.357 [0.305, 0.414] | 0.182 [0.143, 0.229] | 0.730 | - | - | - | - |
| reference: discount-badge rule | - | - | 0.777 [0.725, 0.821] | 0.201 [0.160, 0.250] | 0.511 | - | - | - | - |
| reference: random (expected) | - | - | 0.500 [0.443, 0.557] | 0.500 [0.445, 0.555] | 0.500 | - | - | - | - |

### Table 2c. Detection, V2 excluding kiosks whose description holds the explicit 'deepfake' label (headline)

| Model | Failed replies | Degenerate | False-safe (attacked judged SAFE) | False-warning (safe judged UNSAFE) | Balanced acc. | Best reference (bal. acc.) | Diff. vs best ref. [95% CI] | Holm p | Better than baseline |
|---|---|---|---|---|---|---|---|---|---|
| mistral:7b-instruct | 0.275 [0.222, 0.335] (66/240) | no | 0.691 [0.632, 0.744] | 0.542 [0.485, 0.597] | 0.384 | deepfake-image rule (0.723) | -0.339 [-0.396, -0.281] | 0.010 | no |
| llama3.1:8b | 0.025 [0.012, 0.053] (6/240) | no | 0.424 [0.365, 0.484] | 0.452 [0.396, 0.508] | 0.562 | deepfake-image rule (0.723) | -0.161 [-0.203, -0.120] | 0.010 | no |
| phi3:3.8b | 0.075 [0.048, 0.115] (18/240) | no | 0.393 [0.336, 0.453] | 0.528 [0.472, 0.584] | 0.539 | deepfake-image rule (0.723) | -0.184 [-0.229, -0.141] | 0.010 | no |
| gemma2:9b | 0.050 [0.029, 0.085] (12/240) | no | 0.328 [0.274, 0.387] | 0.742 [0.690, 0.789] | 0.465 | deepfake-image rule (0.723) | -0.258 [-0.297, -0.219] | 0.010 | no |
| qwen2.5:7b | 0.025 [0.012, 0.053] (6/240) | no | 0.412 [0.354, 0.473] | 0.525 [0.469, 0.581] | 0.531 | deepfake-image rule (0.723) | -0.192 [-0.238, -0.149] | 0.010 | no |
| reference: always SAFE | - | - | 1.000 [0.986, 1.000] | 0.000 [0.000, 0.013] | 0.500 | - | - | - | - |
| reference: always UNSAFE | - | - | 0.000 [0.000, 0.014] | 1.000 [0.987, 1.000] | 0.500 | - | - | - | - |
| reference: deepfake-image rule | - | - | 0.397 [0.340, 0.457] | 0.157 [0.120, 0.203] | 0.723 | - | - | - | - |
| reference: discount-badge rule | - | - | 0.786 [0.733, 0.832] | 0.204 [0.162, 0.253] | 0.505 | - | - | - | - |
| reference: random (expected) | - | - | 0.500 [0.440, 0.560] | 0.500 [0.444, 0.556] | 0.500 | - | - | - | - |

### Table 2d. Detection, V2 excluding kiosks whose description holds 'fake', 'scam' or 'phish'

| Model | Failed replies | Degenerate | False-safe (attacked judged SAFE) | False-warning (safe judged UNSAFE) | Balanced acc. | Best reference (bal. acc.) | Diff. vs best ref. [95% CI] | Holm p | Better than baseline |
|---|---|---|---|---|---|---|---|---|---|
| mistral:7b-instruct | 0.265 [0.211, 0.326] (59/223) | no | 0.711 [0.648, 0.767] | 0.493 [0.428, 0.559] | 0.398 | deepfake-image rule (0.696) | -0.298 [-0.364, -0.233] | - | n/a (not in family) |
| llama3.1:8b | 0.027 [0.012, 0.057] (6/223) | no | 0.472 [0.407, 0.539] | 0.425 [0.362, 0.491] | 0.551 | deepfake-image rule (0.696) | -0.145 [-0.194, -0.098] | - | n/a (not in family) |
| phi3:3.8b | 0.081 [0.052, 0.124] (18/223) | no | 0.450 [0.385, 0.516] | 0.475 [0.410, 0.541] | 0.538 | deepfake-image rule (0.696) | -0.159 [-0.205, -0.108] | - | n/a (not in family) |
| gemma2:9b | 0.054 [0.031, 0.092] (12/223) | no | 0.390 [0.328, 0.456] | 0.652 [0.587, 0.711] | 0.479 | deepfake-image rule (0.696) | -0.217 [-0.262, -0.175] | - | n/a (not in family) |
| qwen2.5:7b | 0.018 [0.007, 0.045] (4/223) | no | 0.454 [0.389, 0.520] | 0.452 [0.388, 0.518] | 0.547 | deepfake-image rule (0.696) | -0.150 [-0.198, -0.101] | - | n/a (not in family) |
| reference: always SAFE | - | - | 1.000 [0.983, 1.000] | 0.000 [0.000, 0.017] | 0.500 | - | - | - | - |
| reference: always UNSAFE | - | - | 0.000 [0.000, 0.017] | 1.000 [0.983, 1.000] | 0.500 | - | - | - | - |
| reference: deepfake-image rule | - | - | 0.427 [0.363, 0.493] | 0.181 [0.136, 0.237] | 0.696 | - | - | - | - |
| reference: discount-badge rule | - | - | 0.798 [0.740, 0.846] | 0.181 [0.136, 0.237] | 0.510 | - | - | - | - |
| reference: random (expected) | - | - | 0.500 [0.434, 0.566] | 0.500 [0.435, 0.565] | 0.500 | - | - | - | - |

### Table 3a. Detection error by visible-cue class, V1 cue-free, all kiosks

Cell = error rate with Wilson 95% interval and count. Attacked classes: false-safe (attacked kiosk judged SAFE). Safe classes: false-warning (safe kiosk judged UNSAFE).

| Model | legitimate_discount (false-warning) | fake_discount (false-safe) | ambiguous_safe_deepfake (false-warning) | obvious_attack_deepfake (false-safe) | ambiguous_attack_real (false-safe) | benign_plain (false-warning) |
|---|---|---|---|---|---|---|
| mistral:7b-instruct | 0.10 [0.05, 0.20] (6/62) | 0.92 [0.83, 0.97] (60/65) | 0.15 [0.07, 0.28] (6/41) | 0.84 [0.77, 0.89] (127/152) | 0.93 [0.85, 0.97] (69/74) | 0.26 [0.21, 0.33] (54/205) |
| llama3.1:8b | 0.19 [0.11, 0.31] (12/62) | 0.80 [0.69, 0.88] (52/65) | 0.07 [0.03, 0.19] (3/41) | 0.84 [0.77, 0.89] (127/152) | 0.95 [0.87, 0.98] (70/74) | 0.13 [0.09, 0.18] (27/205) |
| phi3:3.8b | 0.24 [0.15, 0.36] (15/62) | 0.69 [0.57, 0.79] (45/65) | 0.12 [0.05, 0.26] (5/41) | 0.76 [0.68, 0.82] (115/152) | 0.93 [0.85, 0.97] (69/74) | 0.18 [0.13, 0.23] (36/205) |
| gemma2:9b | 0.02 [0.00, 0.09] (1/62) | 0.97 [0.89, 0.99] (63/65) | 0.00 [0.00, 0.09] (0/41) | 1.00 [0.98, 1.00] (152/152) | 1.00 [0.95, 1.00] (74/74) | 0.00 [0.00, 0.02] (0/205) |
| qwen2.5:7b | 0.50 [0.38, 0.62] (31/62) | 0.54 [0.42, 0.65] (35/65) | 0.27 [0.16, 0.42] (11/41) | 0.59 [0.51, 0.66] (89/152) | 0.89 [0.80, 0.94] (66/74) | 0.24 [0.19, 0.30] (49/205) |
| reference: always SAFE | 0.00 [0.00, 0.06] (0/62) | 1.00 [0.94, 1.00] (65/65) | 0.00 [0.00, 0.09] (0/41) | 1.00 [0.98, 1.00] (152/152) | 1.00 [0.95, 1.00] (74/74) | 0.00 [0.00, 0.02] (0/205) |
| reference: always UNSAFE | 1.00 [0.94, 1.00] (62/62) | 0.00 [0.00, 0.06] (0/65) | 1.00 [0.91, 1.00] (41/41) | 0.00 [0.00, 0.02] (0/152) | 0.00 [0.00, 0.05] (0/74) | 1.00 [0.98, 1.00] (205/205) |
| reference: deepfake-image rule | 0.24 [0.15, 0.36] (15/62) | 0.46 [0.35, 0.58] (30/65) | 1.00 [0.91, 1.00] (41/41) | 0.00 [0.00, 0.02] (0/152) | 1.00 [0.95, 1.00] (74/74) | 0.00 [0.00, 0.02] (0/205) |
| reference: discount-badge rule | 1.00 [0.94, 1.00] (62/62) | 0.00 [0.00, 0.06] (0/65) | 0.00 [0.00, 0.09] (0/41) | 1.00 [0.98, 1.00] (152/152) | 1.00 [0.95, 1.00] (74/74) | 0.00 [0.00, 0.02] (0/205) |
| reference: random (expected) | 0.50 [0.38, 0.62] (31/62) | 0.50 [0.38, 0.62] (32/65) | 0.50 [0.35, 0.65] (20/41) | 0.50 [0.42, 0.58] (76/152) | 0.50 [0.39, 0.61] (37/74) | 0.50 [0.43, 0.57] (102/205) |

### Table 3b. Detection error by visible-cue class, V2 image descriptions, all kiosks

Cell = error rate with Wilson 95% interval and count. Attacked classes: false-safe (attacked kiosk judged SAFE). Safe classes: false-warning (safe kiosk judged UNSAFE).

| Model | legitimate_discount (false-warning) | fake_discount (false-safe) | ambiguous_safe_deepfake (false-warning) | obvious_attack_deepfake (false-safe) | ambiguous_attack_real (false-safe) | benign_plain (false-warning) |
|---|---|---|---|---|---|---|
| mistral:7b-instruct | 0.50 [0.38, 0.62] (31/62) | 0.71 [0.59, 0.80] (46/65) | 0.39 [0.26, 0.54] (16/41) | 0.56 [0.48, 0.64] (85/152) | 0.82 [0.72, 0.89] (61/74) | 0.58 [0.51, 0.65] (119/205) |
| llama3.1:8b | 0.44 [0.32, 0.56] (27/62) | 0.45 [0.33, 0.57] (29/65) | 0.71 [0.56, 0.82] (29/41) | 0.17 [0.12, 0.24] (26/152) | 0.81 [0.71, 0.88] (60/74) | 0.43 [0.36, 0.50] (88/205) |
| phi3:3.8b | 0.48 [0.36, 0.61] (30/62) | 0.37 [0.26, 0.49] (24/65) | 0.98 [0.87, 1.00] (40/41) | 0.18 [0.13, 0.25] (27/152) | 0.76 [0.65, 0.84] (56/74) | 0.47 [0.41, 0.54] (97/205) |
| gemma2:9b | 0.87 [0.77, 0.93] (54/62) | 0.31 [0.21, 0.43] (20/65) | 1.00 [0.91, 1.00] (41/41) | 0.07 [0.04, 0.12] (11/152) | 0.74 [0.63, 0.83] (55/74) | 0.66 [0.60, 0.72] (136/205) |
| qwen2.5:7b | 0.58 [0.46, 0.70] (36/62) | 0.37 [0.26, 0.49] (24/65) | 0.85 [0.72, 0.93] (35/41) | 0.20 [0.14, 0.27] (30/152) | 0.76 [0.65, 0.84] (56/74) | 0.46 [0.40, 0.53] (95/205) |
| reference: always SAFE | 0.00 [0.00, 0.06] (0/62) | 1.00 [0.94, 1.00] (65/65) | 0.00 [0.00, 0.09] (0/41) | 1.00 [0.98, 1.00] (152/152) | 1.00 [0.95, 1.00] (74/74) | 0.00 [0.00, 0.02] (0/205) |
| reference: always UNSAFE | 1.00 [0.94, 1.00] (62/62) | 0.00 [0.00, 0.06] (0/65) | 1.00 [0.91, 1.00] (41/41) | 0.00 [0.00, 0.02] (0/152) | 0.00 [0.00, 0.05] (0/74) | 1.00 [0.98, 1.00] (205/205) |
| reference: deepfake-image rule | 0.24 [0.15, 0.36] (15/62) | 0.46 [0.35, 0.58] (30/65) | 1.00 [0.91, 1.00] (41/41) | 0.00 [0.00, 0.02] (0/152) | 1.00 [0.95, 1.00] (74/74) | 0.00 [0.00, 0.02] (0/205) |
| reference: discount-badge rule | 1.00 [0.94, 1.00] (62/62) | 0.00 [0.00, 0.06] (0/65) | 0.00 [0.00, 0.09] (0/41) | 1.00 [0.98, 1.00] (152/152) | 1.00 [0.95, 1.00] (74/74) | 0.00 [0.00, 0.02] (0/205) |
| reference: random (expected) | 0.50 [0.38, 0.62] (31/62) | 0.50 [0.38, 0.62] (32/65) | 0.50 [0.35, 0.65] (20/41) | 0.50 [0.42, 0.58] (76/152) | 0.50 [0.39, 0.61] (37/74) | 0.50 [0.43, 0.57] (102/205) |

### Table 3c. Detection error by visible-cue class, V2 excluding kiosks whose description holds the explicit 'deepfake' label (headline)

Cell = error rate with Wilson 95% interval and count. Attacked classes: false-safe (attacked kiosk judged SAFE). Safe classes: false-warning (safe kiosk judged UNSAFE).

| Model | legitimate_discount (false-warning) | fake_discount (false-safe) | ambiguous_safe_deepfake (false-warning) | obvious_attack_deepfake (false-safe) | ambiguous_attack_real (false-safe) | benign_plain (false-warning) |
|---|---|---|---|---|---|---|
| mistral:7b-instruct | 0.49 [0.37, 0.61] (30/61) | 0.77 [0.64, 0.86] (43/56) | 0.39 [0.25, 0.56] (13/33) | 0.58 [0.50, 0.66] (77/132) | 0.82 [0.72, 0.89] (61/74) | 0.58 [0.51, 0.65] (119/205) |
| llama3.1:8b | 0.43 [0.31, 0.55] (26/61) | 0.50 [0.37, 0.63] (28/56) | 0.64 [0.47, 0.78] (21/33) | 0.17 [0.12, 0.25] (23/132) | 0.81 [0.71, 0.88] (60/74) | 0.43 [0.36, 0.50] (88/205) |
| phi3:3.8b | 0.48 [0.36, 0.60] (29/61) | 0.43 [0.31, 0.56] (24/56) | 0.97 [0.85, 0.99] (32/33) | 0.17 [0.12, 0.25] (23/132) | 0.76 [0.65, 0.84] (56/74) | 0.47 [0.41, 0.54] (97/205) |
| gemma2:9b | 0.87 [0.76, 0.93] (53/61) | 0.36 [0.24, 0.49] (20/56) | 1.00 [0.90, 1.00] (33/33) | 0.08 [0.05, 0.14] (11/132) | 0.74 [0.63, 0.83] (55/74) | 0.66 [0.60, 0.72] (136/205) |
| qwen2.5:7b | 0.57 [0.45, 0.69] (35/61) | 0.41 [0.29, 0.54] (23/56) | 0.82 [0.66, 0.91] (27/33) | 0.22 [0.16, 0.30] (29/132) | 0.76 [0.65, 0.84] (56/74) | 0.46 [0.40, 0.53] (95/205) |
| reference: always SAFE | 0.00 [0.00, 0.06] (0/61) | 1.00 [0.94, 1.00] (56/56) | 0.00 [0.00, 0.10] (0/33) | 1.00 [0.97, 1.00] (132/132) | 1.00 [0.95, 1.00] (74/74) | 0.00 [0.00, 0.02] (0/205) |
| reference: always UNSAFE | 1.00 [0.94, 1.00] (61/61) | 0.00 [0.00, 0.06] (0/56) | 1.00 [0.90, 1.00] (33/33) | 0.00 [0.00, 0.03] (0/132) | 0.00 [0.00, 0.05] (0/74) | 1.00 [0.98, 1.00] (205/205) |
| reference: deepfake-image rule | 0.23 [0.14, 0.35] (14/61) | 0.54 [0.41, 0.66] (30/56) | 1.00 [0.90, 1.00] (33/33) | 0.00 [0.00, 0.03] (0/132) | 1.00 [0.95, 1.00] (74/74) | 0.00 [0.00, 0.02] (0/205) |
| reference: discount-badge rule | 1.00 [0.94, 1.00] (61/61) | 0.00 [0.00, 0.06] (0/56) | 0.00 [0.00, 0.10] (0/33) | 1.00 [0.97, 1.00] (132/132) | 1.00 [0.95, 1.00] (74/74) | 0.00 [0.00, 0.02] (0/205) |
| reference: random (expected) | 0.50 [0.38, 0.62] (30/61) | 0.50 [0.37, 0.63] (28/56) | 0.50 [0.34, 0.66] (16/33) | 0.50 [0.42, 0.58] (66/132) | 0.50 [0.39, 0.61] (37/74) | 0.50 [0.43, 0.57] (102/205) |

### Table 4a. Recall on attacked kiosks by hidden attack mode, V1 cue-free, all kiosks

Measures recall on attacked kiosks with the cues they happen to show, not recognition of the mode (the modes are consequences after charging).

| Model | reduced | blocked |
|---|---|---|
| mistral:7b-instruct | 0.14 [0.10, 0.19] (32/226) | 0.05 [0.02, 0.13] (3/65) |
| llama3.1:8b | 0.17 [0.13, 0.22] (38/226) | 0.06 [0.02, 0.15] (4/65) |
| phi3:3.8b | 0.24 [0.19, 0.30] (54/226) | 0.12 [0.06, 0.22] (8/65) |
| gemma2:9b | 0.01 [0.00, 0.03] (2/226) | 0.00 [0.00, 0.06] (0/65) |
| qwen2.5:7b | 0.36 [0.30, 0.42] (81/226) | 0.31 [0.21, 0.43] (20/65) |

### Table 4b. Recall on attacked kiosks by hidden attack mode, V2 excluding kiosks whose description holds the explicit 'deepfake' label (headline)

Measures recall on attacked kiosks with the cues they happen to show, not recognition of the mode (the modes are consequences after charging).

| Model | reduced | blocked |
|---|---|---|
| mistral:7b-instruct | 0.31 [0.25, 0.38] (63/203) | 0.31 [0.20, 0.43] (18/59) |
| llama3.1:8b | 0.59 [0.52, 0.65] (119/203) | 0.54 [0.42, 0.66] (32/59) |
| phi3:3.8b | 0.60 [0.53, 0.66] (121/203) | 0.64 [0.52, 0.75] (38/59) |
| gemma2:9b | 0.67 [0.61, 0.74] (137/203) | 0.66 [0.53, 0.77] (39/59) |
| qwen2.5:7b | 0.59 [0.52, 0.66] (120/203) | 0.58 [0.45, 0.69] (34/59) |

### Table 5a. Recommendation by station type, V1 cue-free, all kiosks

| Model | Degenerate | Mixed: safe kiosk chosen | Mixed: attacked kiosk chosen | Mixed: SKIP | Random-choice safe rate | Safe-choice interval vs random | Benign: SKIP (over-caution) | All-attacked: SKIP (protective) | All-attacked: attacked kiosk chosen | Failed replies |
|---|---|---|---|---|---|---|---|---|---|---|
| mistral:7b-instruct | no | 0.53 [0.45, 0.61] (85/160) | 0.47 [0.39, 0.55] (75/160) | 0.00 [0.00, 0.02] (0/160) | 0.515 | overlaps | 0.00 [0.00, 0.09] (0/40) | 0.00 [0.00, 0.09] (0/40) | 1.00 [0.91, 1.00] (40/40) | 0.00 [0.00, 0.02] (0/240) |
| llama3.1:8b | no | 0.55 [0.47, 0.63] (88/160) | 0.45 [0.37, 0.53] (72/160) | 0.00 [0.00, 0.02] (0/160) | 0.515 | overlaps | 0.00 [0.00, 0.09] (0/40) | 0.00 [0.00, 0.09] (0/40) | 1.00 [0.91, 1.00] (40/40) | 0.00 [0.00, 0.02] (0/240) |
| phi3:3.8b | no | 0.46 [0.39, 0.54] (74/160) | 0.54 [0.46, 0.61] (86/160) | 0.00 [0.00, 0.02] (0/160) | 0.515 | overlaps | 0.00 [0.00, 0.09] (0/40) | 0.00 [0.00, 0.09] (0/40) | 1.00 [0.91, 1.00] (40/40) | 0.00 [0.00, 0.02] (0/240) |
| gemma2:9b | no | 0.54 [0.47, 0.62] (87/160) | 0.46 [0.38, 0.53] (73/160) | 0.00 [0.00, 0.02] (0/160) | 0.515 | overlaps | 0.00 [0.00, 0.09] (0/40) | 0.00 [0.00, 0.09] (0/40) | 1.00 [0.91, 1.00] (40/40) | 0.00 [0.00, 0.02] (0/240) |
| qwen2.5:7b | no | 0.37 [0.30, 0.45] (59/160) | 0.45 [0.37, 0.53] (72/160) | 0.18 [0.13, 0.25] (29/160) | 0.515 | below | 0.12 [0.05, 0.26] (5/40) | 0.15 [0.07, 0.29] (6/40) | 0.85 [0.71, 0.93] (34/40) | 0.00 [0.00, 0.02] (0/240) |
| reference: always SKIP | - | 0.000 | 0.000 | 1.000 | - | - | 1.000 | 1.000 | 0.000 | - |

### Table 5b. Recommendation by station type, V2 image descriptions, all kiosks

| Model | Degenerate | Mixed: safe kiosk chosen | Mixed: attacked kiosk chosen | Mixed: SKIP | Random-choice safe rate | Safe-choice interval vs random | Benign: SKIP (over-caution) | All-attacked: SKIP (protective) | All-attacked: attacked kiosk chosen | Failed replies |
|---|---|---|---|---|---|---|---|---|---|---|
| mistral:7b-instruct | no | 0.56 [0.49, 0.64] (90/160) | 0.39 [0.32, 0.47] (63/160) | 0.04 [0.02, 0.09] (7/160) | 0.515 | overlaps | 0.03 [0.00, 0.13] (1/40) | 0.10 [0.04, 0.23] (4/40) | 0.90 [0.77, 0.96] (36/40) | 0.00 [0.00, 0.02] (0/240) |
| llama3.1:8b | no | 0.54 [0.47, 0.62] (87/160) | 0.45 [0.37, 0.53] (72/160) | 0.01 [0.00, 0.03] (1/160) | 0.515 | overlaps | 0.00 [0.00, 0.09] (0/40) | 0.00 [0.00, 0.09] (0/40) | 1.00 [0.91, 1.00] (40/40) | 0.00 [0.00, 0.02] (0/240) |
| phi3:3.8b | no | 0.53 [0.45, 0.60] (84/160) | 0.42 [0.35, 0.50] (68/160) | 0.05 [0.03, 0.10] (8/160) | 0.515 | overlaps | 0.03 [0.00, 0.13] (1/40) | 0.05 [0.01, 0.17] (2/40) | 0.95 [0.83, 0.99] (38/40) | 0.00 [0.00, 0.02] (0/240) |
| gemma2:9b | no | 0.33 [0.26, 0.41] (53/160) | 0.30 [0.23, 0.38] (48/160) | 0.37 [0.30, 0.45] (59/160) | 0.515 | below | 0.50 [0.35, 0.65] (20/40) | 0.38 [0.24, 0.53] (15/40) | 0.62 [0.47, 0.76] (25/40) | 0.00 [0.00, 0.02] (0/240) |
| qwen2.5:7b | no | 0.47 [0.39, 0.55] (75/160) | 0.51 [0.44, 0.59] (82/160) | 0.02 [0.01, 0.05] (3/160) | 0.515 | overlaps | 0.03 [0.00, 0.13] (1/40) | 0.07 [0.03, 0.20] (3/40) | 0.93 [0.80, 0.97] (37/40) | 0.00 [0.00, 0.02] (0/240) |
| reference: always SKIP | - | 0.000 | 0.000 | 1.000 | - | - | 1.000 | 1.000 | 0.000 | - |

### Table 5c. Recommendation by station type, V2 excluding kiosks whose description holds the explicit 'deepfake' label (headline)

| Model | Degenerate | Mixed: safe kiosk chosen | Mixed: attacked kiosk chosen | Mixed: SKIP | Random-choice safe rate | Safe-choice interval vs random | Benign: SKIP (over-caution) | All-attacked: SKIP (protective) | All-attacked: attacked kiosk chosen | Failed replies |
|---|---|---|---|---|---|---|---|---|---|---|
| mistral:7b-instruct | no | 0.54 [0.46, 0.62] (75/139) | 0.43 [0.35, 0.51] (60/139) | 0.03 [0.01, 0.07] (4/139) | 0.514 | overlaps | 0.03 [0.00, 0.14] (1/37) | 0.10 [0.04, 0.26] (3/29) | 0.90 [0.74, 0.96] (26/29) | 0.00 [0.00, 0.02] (0/205) |
| llama3.1:8b | no | 0.50 [0.41, 0.58] (69/139) | 0.50 [0.41, 0.58] (69/139) | 0.01 [0.00, 0.04] (1/139) | 0.514 | overlaps | 0.00 [0.00, 0.09] (0/37) | 0.00 [0.00, 0.12] (0/29) | 1.00 [0.88, 1.00] (29/29) | 0.00 [0.00, 0.02] (0/205) |
| phi3:3.8b | no | 0.53 [0.44, 0.61] (73/139) | 0.45 [0.37, 0.54] (63/139) | 0.02 [0.01, 0.06] (3/139) | 0.514 | overlaps | 0.03 [0.00, 0.14] (1/37) | 0.00 [0.00, 0.12] (0/29) | 1.00 [0.88, 1.00] (29/29) | 0.00 [0.00, 0.02] (0/205) |
| gemma2:9b | no | 0.35 [0.27, 0.43] (48/139) | 0.32 [0.25, 0.41] (45/139) | 0.33 [0.26, 0.41] (46/139) | 0.514 | below | 0.49 [0.33, 0.64] (18/37) | 0.31 [0.17, 0.49] (9/29) | 0.69 [0.51, 0.83] (20/29) | 0.00 [0.00, 0.02] (0/205) |
| qwen2.5:7b | no | 0.46 [0.38, 0.54] (64/139) | 0.52 [0.44, 0.60] (72/139) | 0.02 [0.01, 0.06] (3/139) | 0.514 | overlaps | 0.03 [0.00, 0.14] (1/37) | 0.10 [0.04, 0.26] (3/29) | 0.90 [0.74, 0.96] (26/29) | 0.00 [0.00, 0.02] (0/205) |
| reference: always SKIP | - | 0.000 | 0.000 | 1.000 | - | - | 1.000 | 1.000 | 0.000 | - |

### Table 6. Consistency at temperature 0.3, seeds 1 to 5

Empty if the consistency pass has not been run or registered.

| Model | Variant | Seeds scored | False-safe mean [min, max] | False-warning mean [min, max] | Degenerate seeds (detection) | Detection: identical across seeds | Detection: mean pairwise agreement | Recommendation: identical across seeds |
|---|---|---|---|---|---|---|---|---|
| mistral:7b-instruct | V1 | 5 | 0.904 [0.890, 0.931] | 0.222 [0.211, 0.240] | 0/5 | 0.920 [0.893, 0.941] | 0.962 | 0.862 [0.812, 0.900] |
| mistral:7b-instruct | V2 | 5 | 0.673 [0.649, 0.698] | 0.545 [0.532, 0.555] | 0/5 | 0.877 [0.838, 0.908] | 0.939 | 0.875 [0.827, 0.911] |
| llama3.1:8b | V1 | 5 | 0.845 [0.832, 0.856] | 0.145 [0.140, 0.149] | 0/5 | 0.928 [0.904, 0.946] | 0.967 | 0.925 [0.885, 0.952] |
| llama3.1:8b | V2 | 5 | 0.401 [0.395, 0.412] | 0.488 [0.481, 0.494] | 0/5 | 0.918 [0.892, 0.938] | 0.957 | 0.863 [0.813, 0.900] |
| phi3:3.8b | V1 | 5 | 0.814 [0.770, 0.883] | 0.168 [0.146, 0.182] | 0/5 | 0.833 [0.801, 0.862] | 0.920 | 0.804 [0.749, 0.849] |
| phi3:3.8b | V2 | 5 | 0.371 [0.333, 0.409] | 0.559 [0.545, 0.571] | 0/5 | 0.821 [0.784, 0.853] | 0.914 | 0.692 [0.631, 0.747] |
| gemma2:9b | V1 | 5 | 0.993 [0.993, 0.993] | 0.003 [0.003, 0.003] | 5/5 | 1.000 [0.994, 1.000] | 1.000 | 0.967 [0.936, 0.983] |
| gemma2:9b | V2 | 5 | 0.300 [0.299, 0.306] | 0.749 [0.747, 0.750] | 0/5 | 0.996 [0.987, 0.999] | 0.998 | 0.963 [0.930, 0.980] |
| qwen2.5:7b | V1 | 5 | 0.654 [0.649, 0.663] | 0.301 [0.286, 0.308] | 0/5 | 0.955 [0.935, 0.969] | 0.978 | 0.954 [0.920, 0.974] |
| qwen2.5:7b | V2 | 5 | 0.381 [0.375, 0.395] | 0.525 [0.519, 0.532] | 0/5 | 0.965 [0.947, 0.977] | 0.984 | 0.963 [0.930, 0.980] |

### Table 7. Latency and memory (accuracy pass, temperature 0)

| Model | Calls | Median server ms | p95 server ms | Median wall s | Call errors | First-call load s | Peak VRAM MiB | VRAM added MiB |
|---|---|---|---|---|---|---|---|---|
| mistral:7b-instruct | 960 | 157 | 470 | 0.16 | 0 | 2.0 | 10571 | 5308 |
| llama3.1:8b | 960 | 221 | 477 | 0.23 | 0 | 2.3 | 10775 | 5536 |
| phi3:3.8b | 960 | 309 | 570 | 0.32 | 0 | 1.7 | 9480 | 4318 |
| gemma2:9b | 960 | 357 | 693 | 0.37 | 0 | 2.8 | 12312 | 7126 |
| qwen2.5:7b | 960 | 187 | 486 | 0.20 | 0 | 2.3 | 10340 | 5174 |
