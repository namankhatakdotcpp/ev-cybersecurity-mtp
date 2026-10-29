# Gate 4 selection-bias report (generated; do not edit by hand)

Primary T1 rows with gaze: 492 rows, 112 participants. Matched (usable EEG): 150 rows, 49 participants. Other: 342 rows, 84 participants. 21 participants contribute rows to both groups (their early stations have EEG, later ones do not).

## Why rows lack EEG (participants whose recording was confirmed to overlap their session)

67 participants, 572 rows. Link between EEG recording and canonical session folder: 0 mismatches.

| Window position relative to the EEG recording | EEG unusable | EEG usable |
|---|---|---|
| inside EEG span | 11 | 322 |
| window after EEG end | 235 | 0 |
| window partly outside EEG span | 2 | 2 |

Share of rows whose decision window falls after the recording ended: 41.1%. Median trial index of rows with usable EEG 3 vs 8 for rows after the recording ended.

## Row level: matched vs other primary rows (standardised mean difference, participant-cluster bootstrap 95% CI)

| Variable | Matched mean | Other mean | SMD [95% CI] |
|---|---|---|---|
| trial_index | 5.427 | 7.599 | -0.53 [-0.83, -0.29] |
| window_duration_s | 24.240 | 21.834 | 0.13 [-0.10, 0.38] |
| n_attacked | 1.307 | 1.260 | 0.10 [-0.10, 0.29] |
| p_exp | 0.500 | 0.490 | 0.08 [-0.12, 0.28] |
| n_available | 2.613 | 2.579 | 0.07 [-0.11, 0.26] |
| ai_help_used | 0.113 | 0.099 | 0.05 [-0.23, 0.31] |
| y | 0.467 | 0.439 | 0.06 [-0.16, 0.28] |
| gaze_valid_rate (valid samples per second in the window) | 133.946 | 132.356 | 0.06 [-0.32, 0.50] |

## Participant level (49 matched vs 63 other primary participants; exploratory, Benjamini-Hochberg across all tests)

| Variable | Matched | Other | Effect size | p | FDR |
|---|---|---|---|---|---|
| n_rows | 4.449 | 4.349 | SMD 0.04 | 0.598 | 0.831 |
| event_rate | 0.447 | 0.429 | SMD 0.06 | 0.639 | 0.831 |
| incident_mode | 0.367 | 0.540 | SMD -0.35 | 0.071 | 0.464 |
| gaze_valid_rate | 133.846 | 131.578 | SMD 0.09 | 0.286 | 0.619 |
| age | 21.625 | 21.825 | SMD -0.10 | 0.841 | 0.841 |
| period (largest matched category: apr) | 0.49 | 0.22 | Cramer's V 0.35 | 0.001 | 0.012 |
| gender (largest matched category: male) | 0.80 | 0.79 | Cramer's V 0.11 | 0.507 | 0.824 |
| education (largest matched category: Bachelor's) | 0.67 | 0.68 | Cramer's V 0.19 | 0.376 | 0.699 |
| specialization (largest matched category: CSE) | 0.49 | 0.32 | Cramer's V 0.59 | 0.203 | 0.619 |
| ev_experience (largest matched category: Never) | 0.90 | 0.78 | Cramer's V 0.21 | 0.160 | 0.619 |
| driving_years (largest matched category: Less than 1 year) | 0.61 | 0.57 | Cramer's V 0.13 | 0.731 | 0.841 |
| driving_frequency (largest matched category: Rarely) | 0.45 | 0.46 | Cramer's V 0.14 | 0.803 | 0.841 |
| terrain_experience (largest matched category: 5 - Never) | 0.53 | 0.41 | Cramer's V 0.24 | 0.249 | 0.619 |

Event rate: matched rows 0.467, other rows 0.439.
