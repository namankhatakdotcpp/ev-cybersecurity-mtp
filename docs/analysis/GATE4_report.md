# Gate 4 report: EEG on the matched subset (S6, exploratory) and selection-bias report

Protocol v1 frozen at `58e59c0` (tag `protocol-v1`, D066). `configs/gate4_eeg.yaml` and the Gate 4 code were committed before any Gate 4 run (`72ee3a5`, `13b06c7`); the runs record code commit `13b06c7`. Generated tables: `results/master_table_gate4.md` (S6) and `results/selection_bias_gate4.md` (selection bias); registry rows `g4_selection_bias_*`, `g4_s6_ridge_*`, `g4_s6_rf_*`, `g4_s6_hgb_*`.

## Result in one paragraph

**Nothing here establishes that EEG adds information.** On the identical matched rows (150 rows, 49 participants, 70 events) the pre-specified S6 contrast, EEG added to behaviour + gaze (ridge), is **+0.031 AUROC [-0.013, +0.070]**; the participant-block permutation of the EEG block gives **p = 0.22**; the descriptive 17-df likelihood-ratio test (p = 0.027) is not trustworthy with 70 events and its provisional Holm upper bound is 0.11. A post-hoc check shows that adding 17 columns of pure noise already raises the cross-validated AUROC by about +0.006 on this set. Separately, the selection-bias report shows that the EEG rows are not a random subset: they come from **earlier stations of the session** (median trial 3 vs 8) and from the **April-heavy early period**, because the EEG recordings ended before 41% of the decision windows of the participants who had synchronised recordings. Outcome rates, exposure, window durations, gaze quality and demographics are similar between matched and unmatched rows and participants.

## Selection-bias findings (full tables in `results/selection_bias_gate4.md`)

- **Why rows lack EEG:** 67 participants had a recording confirmed to overlap their session (0 mismatches between the recording's session link and the canonical session folder). Of their 572 decision windows, 322 have usable EEG, 11 are inside the recording but unusable (short windows or dropouts), 2 + 2 are partly outside it, and **235 (41.1%) fall after the recording ended**. So most missing EEG is a time-in-session effect, not random dropout, and participants contribute EEG for their first stations only (21 participants contribute rows to both the matched and unmatched groups).
- **Row level (matched vs other primary rows, standardised mean difference with participant-cluster bootstrap CI):** trial index **-0.53 [-0.83, -0.29]** (clearly earlier). Window duration +0.13 [-0.10, 0.38], attacked kiosks +0.10 [-0.10, 0.29], expected attack share +0.08, available kiosks +0.07, `ai_help_used` +0.05, event rate +0.06 [-0.16, 0.28], gaze valid-sample rate +0.06 [-0.32, 0.50]: none distinguishable from zero.
- **Participant level (49 matched vs 63 other primary participants; exploratory; Benjamini-Hochberg over 13 tests):** only collection period differs after correction (April 49% vs 22%; Cramer's V 0.35, FDR 0.012). Incident mode (SMD -0.35, FDR 0.46), number of rows, event rate, gaze valid rate, age, gender, education, specialization, EV experience, driving experience and terrain experience show no corrected difference. Several demographic categories are sparse, so these tests have little power and "no difference" means "not detected".
- **Interpretation:** results on the matched set describe early-session decisions of participants recorded in April-heavy sessions. They may not transfer to later stations or to the other periods; nothing about outcomes or exposure suggests a big difference, but the trial-position shift is real and could interact with EEG (alertness, settling-in, electrode contact).

## S6 results (ridge primary; random forest and boosting exploratory)

Mean over 20 repeats of 5-fold participant-grouped nested CV, participant-bootstrap 95% CIs, identical rows for every model.

| Set | AUROC | PR-AUC | Brier |
|---|---|---|---|
| B0 (exposure + design) | 0.618 [0.528, 0.696] | 0.569 | 0.236 |
| B | 0.610 [0.516, 0.692] | 0.563 | 0.236 |
| BG | 0.634 [0.535, 0.722] | 0.592 | 0.232 |
| BGE (+ EEG) | 0.666 [0.556, 0.755] | 0.643 | 0.229 |

- **Primary contrast BGE minus BG:** +0.031 [-0.013, +0.070], bootstrap p = 0.14.
- **Other contrasts (exploratory, not corrected for the six comparisons):** BG minus B +0.023 [-0.002, +0.047]; BGE minus B0 +0.047 [-0.007, +0.096]; BGE minus B +0.054 [+0.006, +0.099] (the only CI that excludes zero, a contrast the protocol did not designate as primary, and one that mixes the EEG effect with the gaze effect).
- **Permutation test of the EEG block** (200 permutations of whole participant blocks within strata of incident mode, period and number of rows; 37 participants permuted, 12 had no partner and stayed in place): observed 0.666 vs permuted mean 0.654 (95th percentile 0.677), p = 0.219. The null mean is itself above the BG value (0.634), so a model that merely carries real-looking EEG vectors from other participants of the same period and mode gains about +0.02.
- **17-df LRT (descriptive):** chi-square 29.85, p = 0.027, provisional Holm upper bound 0.110 with S1 0.760 and S2 1.0. With 70 events and 17 extra parameters (about four events per parameter) the unpenalised test is unreliable; the random-intercept SD falls from 0.64 without EEG to 0 with it, which is what a block of participant-specific, trait-like measurements does in-sample, and says nothing about out-of-sample value.
- **Operating points (ridge):** at the recall-0.80 point the false-warning rate is 0.61-0.64 for every set including B0, so EEG does not change what a warning would cost. No operating point is validated.
- **Exploratory tree learners fail on 150 rows:** random forest scores 0.52 (B), 0.49 (BG), 0.55 (BGE) and boosting 0.54, 0.51, 0.61, i.e. at or below chance, well below B0 (0.60, 0.62). The boosting contrast BGE minus BG (+0.100, nominal p 0.027) comes from a BG model that has collapsed to chance, not from EEG; ignore it.

## Post-hoc diagnostic (not pre-specified; it changes no conclusion)

`backend/pipeline/gate2/diagnostics/g4_noise_columns.py` adds N(0,1) noise columns to BG using the same ridge CV: 17 columns give a mean AUROC of 0.641 vs 0.6345 for BG (mean change +0.006, SD 0.014, 72% of 40 draws above BG, range 0.611-0.678); 5 columns give +0.004. So the evaluation machinery drifts slightly upward as columns are added on this small set. The observed EEG gain (+0.031) is about 1.8 SD above the noise mean, but the pre-specified permutation (real EEG blocks from other participants) has a higher null mean (0.654) and is the appropriate reference.

## Deviations, limitations and things to know

1. **Choices fixed before the run (D069):** the 17-column EEG block, ridge as the primary S6 learner with trees as exploratory, the primary contrast BGE minus BG, the 17-df LRT labelled descriptive, the permutation strata (incident mode, period, number of rows), and the selection-bias variable list.
2. **Power is limited.** The bootstrap SE of the primary contrast is 0.020, so differences below about 0.06 are not distinguishable from zero here (the Protocol's planning range was 0.07-0.10).
3. **The matched set shrinks the sample by two thirds,** and 15 of the 49 participants contribute one row. Calibration slopes have CIs of about 0.3-1.7.
4. **Possible confound not testable here:** EEG band power drifts with time in session and differs between recording days; the block permutation preserves period but not trial position, so a time-in-session proxy could produce a spurious gain. Trial index is in B but only coarsely controls it.
5. **EEG preprocessing is minimal** (median-accelerometer motion split, no ICA or blink handling), as stated in the audit; relative band power across four channels is a coarse measure.
6. **Constant-rate AUROC** is not meaningful; shown as n/a.
7. **Dependence:** the matched rows are a subset of the primary rows used in Gates 2 and 3; nothing here is independent confirmation.

## Critical review block

- **What we learned.** EEG availability is a function of time in the session and of the collection period, not of outcome, exposure or participant characteristics we can measure. On the matched rows, adding the EEG block to behaviour + gaze moves AUROC by about +0.03 with a CI that spans zero and a permutation p of 0.22; the evidence is not distinguishable from no effect and cannot support an EEG claim.
- **What changed.** The EEG analysis now has a defined population (early-session decisions) and a quantified selection mechanism, and a registry-backed comparison on identical rows.
- **What failed and why.** Flexible learners collapse at 150 rows; the unpenalised LRT is unreliable at 4 events per parameter; the evaluation drifts slightly upward with column count. These are properties of this small subset, not findings about EEG.
- **Statistically defensible.** The selection-bias findings (early trials, April-heavy period, 41% of qualified rows after the recording ended); the S6 point estimates and intervals as exploratory; the absence of a Holm-significant result.
- **Not defensible.** Any claim that EEG predicts risky choices, that EEG helps a warning system, or that the matched results generalise to later stations or other periods; any interpretation of the LRT p = 0.027 or of the BGE minus B contrast.
- **To test next (only with new data).** EEG recorded for the full session, with trial position and time-since-start controlled, and a pre-specified single EEG hypothesis; on existing data nothing further is justified.
- **Not to test.** EEG feature selection, other band definitions or EEG-only models on these 49 participants; each would be a fork on an underpowered subset.
