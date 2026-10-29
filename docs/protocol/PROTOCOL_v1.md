# Protocol v1 (Gate 1): freeze for approval

Status: **draft for approval, not yet frozen.** Documents only: no model was trained and no repository code was changed in this gate. Once approved, this file is frozen by recording its git commit hash in the experiment registry; any later deviation is logged in `Decision.md` as a new entry referencing this protocol, never by editing this file silently.

Source of every number: Gate 0 audit (`docs/audit/GATE0_audit.md`) plus the read-only counts computed for this gate from the raw interaction logs and the committed feature table (see section 14, "Basis of the numbers"). Wording rule: "associated with" and "predictive of"; no causal language anywhere.

**An honesty note that governs the whole protocol.** The Gate 0 audit already showed descriptive evidence that the gaze features are near chance among charge decisions (pooled per-feature AUROC 0.49-0.52). This protocol was therefore written knowing the likely answer to the primary question is a null. It is pre-specified to make that null (or any surprise) defensible, but it is **not blind**: the target was redefined after seeing the data, and there is no untouched confirmatory sample. Every result from the existing 126 participants is reported as pre-specified but exploratory with respect to the data-driven redefinition of the target. Only newly collected data could be confirmatory (section 11).

## 1. Prediction target, unit and timestamp

**Unit.** One station visit by one participant (`participant_id`, `session_dir`, `trial`), as in the feature table.

**Why the legacy target is retired as primary.** `risky` = charged at an attacked kiosk. Gate 0 showed it is set largely by randomised exposure (0.0/26.5/61.5/67.1% for 0/1/2/3 attacked kiosks) and by whether the participant charged at all (skip vs charge), so it mixes randomised exposure, a choice to charge, and a choice of kiosk. It is kept only as a labelled legacy secondary outcome.

**Primary target (T1).** Among station visits where the participant **charged** and the station was **informative** (at least one attacked and at least one safe kiosk among the *available* kiosks, using the layout logged for that station), `y = 1` if the chosen kiosk was an attacked kiosk, else 0. The ground truth for `y` is the layout's own attack flag for the kiosk the participant used, which Gate 0 verified equals the logged `kiosk_attack` label in 815 of 815 charge events. Exposure enters every primary model as an **offset**: `logit(p_exp)` with `p_exp = (number of attacked available kiosks) / (number of available kiosks)`, so that "chose an attacked kiosk" is evaluated against what random choice would give at that station.

**Prediction timestamp.** `t_commit` = the logged `charging` event of that station visit. Features are computed over `[Reached, t_commit]`. Limitation, stated up front: the kiosk-selection and amount-confirmation clicks are not logged, so the true moment of commitment is unknown and the window includes the keypad dialog and confirm step. T1 findings are therefore claims of **association with the decision outcome measured over the decision window**, not of prediction before commitment. A pre-specified sensitivity analysis (S2, section 4) restricts to the first 5 seconds after `Reached`.

**Pre-specified eligibility, exclusions and data rules** (written now, before any Gate 2 modelling):
- E1. Participants with no station events (6, near-empty logs) are not in the analysis table (already the case).
- E2. Duplicate participant folders keep the folder with the larger interaction log (existing pipeline rule). Sensitivity: drop all participants that had duplicate folders (6).
- E3. Primary rows must have gaze features (`gaze_missing == False`, at least 3 valid samples in the window) so that B and B+G are always fitted on identical rows. Sensitivity S4: require at least 1 s (200 samples) of valid gaze.
- E4. `incident_mode` is taken from the layout event for the station (present for all 1,123 events), not from `system_config.json` (missing for one session).
- E5. No participant or row is dropped for any other reason, and none because of a model result. Every exclusion is counted in the registry.
- E6. `rag_contaminated` is never a model feature. Sensitivity S3: drop the 38 flagged sessions.

**Counts under these rules** (Gate 1 read-only counts):

| Set | Rows | Participants | Events (`y=1`) |
|---|---|---|---|
| All charge decisions, informative stations (T1 universe) | 516 | 115 | 233 (45.2%) |
| T1 with gaze features (primary analysis set) | 492 | 112 | 220 |
| T1 with gaze and EEG (matched EEG set) | 150 | 49 | 70 |
| Station visits at informative stations (for the skip/charge secondary target) | 719 | not computed | charge rate 71.8% |

Per participant (T1 universe): median 4 rows (1-12); 99 participants have at least 2 rows, 88 at least 3, 47 at least 5; 87 have both outcomes; 11 always chose an attacked kiosk, 17 never did. Expected events under random choice among available kiosks: 254.5 (49.3%) vs 233 observed (45.2%).

## 2. Primary hypothesis (single) and secondary hypotheses

**H1 (primary, the only confirmatory-style test).** Within the primary analysis set, adding the six AOI-free gaze features to a model that already contains the exposure offset, the pre-specified design covariates and the pre-specified behaviour features is associated with the choice of an attacked kiosk, and improves out-of-sample discrimination: **B + exposure** versus **B + G + exposure**, where
- exposure block = `logit(p_exp)` offset, `n_available`;
- design covariates = layout `incident_mode`, collection period (April / June / July-August);
- behaviour block B = `log(window_duration_s)`, `ai_help_used`, trial index;
- gaze block G = `gaze_n_fixations`, `gaze_n_clusters`, `gaze_n_transitions`, `gaze_transitions_per_fixation`, `gaze_dispersion`, `gaze_entropy_bits` (z-scored, `log1p` for counts, scaling fixed from the training data only in CV).

Two claims are distinct and reported separately:
- **Claim A (association beyond B):** the 6-df nested likelihood-ratio test of the gaze block, alpha 0.05, two-sided. This is the **primary inferential test**, chosen because it uses all rows and all participants once, with fewer analytic degrees of freedom than a resampling scheme.
- **Claim B (incremental predictive value):** paired difference in out-of-sample AUROC (B+G minus B) from the nested grouped CV of section 4, with a participant-level bootstrap 95% CI and a participant-block permutation p-value. It is the **companion estimate**, not a second hypothesis, and it is never described as "prediction" if Claim B's CI includes 0.

Decision rule, fixed now: "gaze adds value" may be written only if Claim A has p < 0.05 **and** Claim B's CI excludes 0. If only Claim A holds the sentence is "associated with, but no demonstrated out-of-sample gain". If neither holds the finding is "no evidence that gaze adds to behaviour for this target at this sample size", which is a valid result.

**Secondary / exploratory (never used to rescue H1).** Held-family correction: Holm across the confirmatory secondary list, FDR (Benjamini-Hochberg) across the exploratory list, each reported with the number of tests.

| ID | Question | Family |
|---|---|---|
| S1 | G alone vs exposure baseline (T1) | secondary (Holm) |
| S2 | H1 repeated with early-window features (first 5 s after `Reached`; drops `window_duration_s`) | secondary (Holm) |
| S3 | H1 excluding RAG-contaminated sessions | sensitivity (not tested) |
| S4 | H1 with at least 1 s valid gaze | sensitivity (not tested) |
| S5 | Skip vs charge at informative stations (T2), B vs B+G | secondary (Holm) |
| S6 | EEG: B vs B+G vs B+G+EEG on the matched set | secondary (Holm) |
| S7 | Legacy target `risky` with exposure offset, same comparisons | exploratory (FDR) |
| S8 | Any ML model vs logistic regression | exploratory (FDR) |

## 3. Statistical framework

The design is repeated decisions per participant (median 4 per participant in T1, 1-12), so both frameworks apply:

1. **Mixed-effects logistic regression with a participant random intercept** for Claim A. Fitted by marginal maximum likelihood (adaptive Gauss-Hermite quadrature, at least 15 nodes) so that the likelihood-ratio test is valid. Engine to be fixed in Gate 2 after an environment check: R `lme4::glmer` is the reference but R is not installed on this machine (installing it needs your approval); a Python alternative is a small, unit-tested random-intercept implementation. Whichever is used, an ordinary logistic fit with participant-clustered robust standard errors is run alongside as a sensitivity analysis.
2. **Participant-grouped predictive comparison** for Claim B (section 4).

**Clustering caveat, from the data:** the residual intraclass correlation of `y - p_exp` estimated by the ANOVA method is 0.000 (design effect 1.00, effective N equal to nominal 516). With a median of 4 rows per participant this estimate is imprecise and is truncated at zero; read it as "no detectable participant clustering after exposure", not as proof of independence. If the fitted random-intercept variance is also near zero, the mixed model and ordinary logistic regression will agree, and both are still reported. A within/between decomposition (adding participant means of each gaze feature) is a pre-specified sensitivity analysis, because association with a participant's average gaze and association with decision-to-decision variation are different claims.

If a participant contributed essentially one outcome (the original brief's other case), participant-level prediction would be the only valid analysis; that is not the case here (99 of 115 participants have at least 2 rows), so mixed-model analysis at the decision level is appropriate.

## 4. Evaluation design

- **Primary set:** T1 with gaze, 492 rows, 112 participants, 220 events (about 45%).
- **Scheme:** repeated stratified participant-grouped nested cross-validation. Outer: 5 folds x **20 repeats** (different seeded participant partitions), groups = participant; stratification at participant level by tertile of participant event rate so every fold contains events. Inner: 3 grouped folds for hyperparameter selection from a small pre-specified grid. A fold holds about 22 participants, 98 rows, 44 events, so fold-wise AUROC is noisy; each repeat pools its out-of-fold predictions and the repeat-wise AUROCs are averaged. No single small hold-out is used.
- **Inside the training fold only:** imputation, scaling, feature transformation, feature selection (none is planned), hyperparameter tuning, threshold selection, calibration. The exposure offset is fixed from the layout (not fitted).
- **Headline inference for Claim B:** the paired difference B+G minus B on the same folds and repeats; participant-level bootstrap (2,000 resamples of participants, all their rows kept) for the 95% CI; **participant-block permutation test** (1,000 permutations for the LRT, 200 for the full CV statistic): whole six-feature gaze blocks are permuted between participants **with the same number of eligible rows**, within strata of (incident mode x collection period), keeping each participant's rows and exposure intact; participants in a singleton stratum stay in place and are counted. It breaks any gaze-outcome link while preserving within-participant structure.
- **Pre-specified predictor sets** (T1): B0 = exposure + design only (always the reference baseline); B; G; B+G. Matched EEG set (S6): B, B+G, B+G+EEG fitted on identical rows and participants (150 rows, 49 participants, 70 events).
- **Not allowed:** tuning on an outer fold, choosing metrics or hyperparameters after seeing outer-fold results, dropping any participant or repeat on the basis of a result, re-running with new seeds to improve a number. The seed list is written in the config before the first run.

## 5. Model grid (pre-specified, small)

1. B0 reference: logistic regression with exposure offset and design covariates only.
2. Regularised logistic regression (L2, single `C` grid), the primary learner for Claim B.
3. Random forest (grid over `max_depth`, `min_samples_leaf`, 300 trees, class-balanced weights off, the target is not rebalanced).
4. One gradient-boosting model (scikit-learn `HistGradientBoostingClassifier`).
5. Optional challenger (XGBoost or LightGBM): allowed only if models 2-4 show a sign of discrimination above B0, labelled exploratory (S8), not for the headline.
6. Majority-class baseline is reported but is not a meaningful reference for this balanced-ish target; B0 is.

No other models, no feature-selection search, and no deep learning (section 8).

## 6. Modality sets

- T1 (all non-EEG analyses): B0, B, G, B+G on the 492-row set.
- EEG analyses (S6) only on the matched set: **150 rows, 49 participants, 70 events**, B vs B+G vs B+G+EEG on exactly the same rows. EEG features: the 16 relative band powers and the low-motion fraction. No claim about EEG is made outside this set. The Gate 0 selection-bias findings are reported with it: EEG coverage is tied to collection month (77% / 65% / 35% / 0% for April / June / July / August), only 57% of qualified participants' rows have a usable EEG window, and demographics were not compared.

## 7. Metrics (fixed now)

- **Primary:** AUROC on T1 out-of-fold predictions.
- **Secondary:** PR-AUC, balanced accuracy, precision, recall, specificity, F1, Brier score, calibration curve (reliability plot with 8 quantile bins and a calibration-in-the-large / slope estimate), **false-safe rate** (events predicted low risk) and **false-warning rate** (non-events predicted high risk).
- **Operating points.** A threshold is never chosen on test data. Two are pre-specified, both chosen on the inner validation predictions of each training fold: (a) maximise balanced accuracy; (b) the smallest threshold reaching recall 0.80. False-safe and false-warning rates are reported at both. No operating point is described as validated.
- **Reference baselines in every table:** B0 and a constant (event-rate) prediction. For T1 the exposure-only descriptive AUROC is 0.659 (participant-bootstrap 95% CI 0.610-0.708); a rule that only uses the visible image type of the chosen kiosk gets 0.790 (0.749-0.827) but uses the decision itself and is shown only to contextualise the scale, not as a model.
- Every metric is reported with a participant-bootstrap 95% CI.

## 8. Deep learning decision

**Recommendation: do not run deep learning, sequence models or Transformers.** Argument: the primary set has 112 participants, 220 events, a median of 4 decisions per participant and gaze windows summarised by six numbers; there is no evidence of structure that a sequence model could use that a regularised logistic regression with the same inputs cannot, and the MLP phase already failed its gate (D037, balanced accuracy 0.497 / AUROC 0.522 on the legacy target). A deep model with thousands of parameters on 220 events would mostly add variance and forking paths. Reconsider only if new data reach on the order of hundreds of independent participants with raw gaze sequences and a pre-registered hypothesis that needs sequences; this is a judgement, not a calculated threshold.

## 9. SLM evaluation (separate track; never in one table with the ML models)

This track asks whether a local SLM can **detect** an unsafe kiosk and **recommend** a safe one, using the same kind of evidence the participant had. It does not predict the participant. Results are never ranked against, or tabulated with, the ML models (the existing D063 comparison asked a different question and is not reused).

**Ground truth** is simulation metadata, never a model output: for each available kiosk, the layout's attack flag (`Safe` / `Cyber Attack`), `cyber_attack_mode` (none / reduced / blocked), discount-coupon flag, and image type (deepfake or real), from the logged `StationGenerated` events.

**Counts available** (2,994 available kiosk records from 1,123 stations):

| Component | Count |
|---|---|
| Safe kiosks | 1,489 (with discount coupon 335; without coupon 1,154) |
| of the safe, no coupon: real image / deepfake image (the "looks fake but is safe" ambiguous cases) | 911 / 243 |
| Attacked kiosks | 1,505 (with coupon 286; reduced charge 1,192; blocked/no charge 313) |
| of the attacked, real image (ambiguous "looks real but is attacked") | 295 |
| Stations by number of attacked available kiosks | 0: 192; 1: 533; 2: 322; 3: 76 |

Attack is stochastic given the visible cue (deepfake image 78.7% attacked, real image 20.2%), so detection accuracy has a ceiling: the rule "unsafe iff deepfake image" scores about 0.79 on these kiosks and is reported as the rule baseline. **"Overcharging" does not exist in the game metadata** (attacks reduce or block charge, they do not overcharge); this class would need explicitly synthetic scenarios, clearly labelled, and is otherwise dropped. Class mapping used: benign (safe, no coupon), legitimate discount (safe, coupon), fake discount (attacked, coupon), incomplete charging (attacked, reduced), blocked/no charge (attacked, blocked), ambiguous (deepfake-looking but safe; real-looking but attacked).

**Scenario set (Gate 5 deliverable, shown to you before any run).** Unit = a station (2-3 available kiosks) with the structured text a participant could perceive: kiosk names, availability, coupon presence, and two evidence variants reported separately: V1 cue-free (no image-authenticity statement) and V2 with an image-authenticity description (which gives away the 79% cue). Target size 240 stations stratified over the classes above (minimum 30 per class where metadata allow; Wilson 95% CI half-width is about 0.07 at n=200, 0.10 at n=100), drawn from sessions by a fixed seed, and used for no other purpose.

**Two tasks, scored separately:**
- *Detection*: per kiosk, SAFE or UNSAFE; accuracy, attack-detection recall, **false-safe rate (critical)**, false-warning rate.
- *Recommendation*: which kiosk to choose; metrics: fraction choosing a safe kiosk, fraction choosing an attacked kiosk (a false-safe-type error), skip handling.
- *Malicious-recommendation compliance*: only as a separately defined condition with an explicit override prompt, reported in its own table.

**Identical conditions for all models:** the same prompts, inputs and decoding settings, temperature fixed (0 for the accuracy pass; a fixed non-zero value with 5 seeds for the consistency pass), same context length, same stop rules, parse failures counted and reported, not silently dropped. Models: the five locally installed (`mistral:7b-instruct`, `llama3.1:8b`, `phi3:3.8b`, `gemma2:9b`, `qwen2.5:7b`), chosen by size, VRAM, speed and instruction following using a separate 20-prompt format-compliance pilot that does not use benchmark scenarios; any change to the model list needs your approval.

**Metrics:** accuracy, recall, false-safe, false-warning, policy/instruction compliance, output consistency across seeds, latency, VRAM, failure rate, each with Wilson CIs. Models are never ranked on accuracy alone.

## 10. Interpretability plan

Performed once, in Gate 6, on the **single model selected by the pre-specified rule** of section 12, not on every model. Methods: grouped permutation importance (participant-grouped, computed on out-of-fold data, with participant-bootstrap CIs), SHAP for that model (tree or linear explainer), partial-dependence sketches only for features in the primary gaze block, and error analysis stratified by exposure (`n_attacked / n_available`), incident mode, collection period, number of decisions per participant and gaze-valid fraction. All statements use "associated with" language. No causal reading of any importance value.

## 11. Out of scope (listed explicitly)

- The integrated human experiment on automation bias (assistant correct / absent / misleading) needs **new data collection**; the existing logs contain 95 identical assistant requests in 38 sessions and record neither the assistant's reply nor its condition, so existing data cannot support it. Future-work design only: three conditions randomised between participants, a fixed set of scenarios drawn from a pre-registered scenario set, the assistant's reply, model name and condition logged per request, kiosk-selection and confirmation clicks logged, a head-pose stream (D031) and a calibration step, and a pre-specified primary outcome (choice of an attacked kiosk, with exposure offset).
- No claim of a "best overall system"; no pooling of ML and SLM results; no online warning performance claims (the warning scaffold has never run online); AOI-based gaze analysis is closed for the existing data (D060-D062).
- Anything that needs video-based AOI recovery, head pose, or live gaze streaming.

## 12. Final selection rubric

Four separate selections, each by a rule fixed now:
1. **Best predictive model:** highest mean out-of-fold AUROC on T1, with ties (CI overlap) resolved in favour of the simpler model.
2. **Best safety-oriented model:** lowest false-safe rate at recall 0.80, provided calibration slope is between 0.7 and 1.3 and the false-warning rate is stated.
3. **Best deployment model:** the simplest model within one standard error of the best AUROC that has acceptable calibration, uses only features computable before the keypad stage if S2 supports it, and has the lowest latency.
4. **Best SLM:** by the separate SLM metrics of section 9 (false-safe rate first, then recall, compliance, consistency, latency, VRAM, failure rate).

"Best overall system" is withheld until validated with humans. Each selection is reported with uncertainty, calibration, false-safe rate, latency, interpretability and data needs.

## 13. Reproducibility specification

- **Config-driven runs:** one YAML per experiment (dataset version, feature version, label version, target definition, split scheme, seed list, model, grid, paths via environment variable or config, no hardcoded machine paths, no secrets).
- **Experiment registry:** an append-only file `results/registry.csv` (one row per run) plus a JSON file per run, with columns: `experiment_id`, `timestamp`, `dataset_version` (hash of the analysis table), `feature_version`, `label_version`, `split_scheme`, `seed`, `model`, `hyperparameters`, `environment` (Python and package versions, OS, GPU if used), `git_commit`, `protocol_version` and protocol commit hash, `metrics` (with CIs), `artifact_paths`, `status`, `notes`. Existing outputs are never overwritten: each run writes to a new `results/<experiment_id>/` folder.
- **Deterministic seeds** for splits, models and permutations, recorded per run.
- **Automatic tables and figures:** a generator script reads only the registry and run folders; no number is copied by hand into any report.
- **Reuse before building:** the existing `train_baselines.py`, `final_ablation_table.py` and `build_feature_table.py` are reused where they fit (their Mac paths must be made configurable first); the registry is a flat CSV plus JSON, not a bespoke database. Any tooling beyond that (R, `lme4`, SHAP) is proposed at the start of the gate that needs it and installed only with your approval.
- **Decision.md:** every meaningful decision and deviation from this protocol is appended as a new entry.

## 14. Basis of the numbers used here

Counts and descriptive figures were computed read-only for this gate from `backend/raw_data` interaction logs (kiosk layouts and decisions) and the committed `backend/pipeline/feature_table.csv`; scratch outputs are under `D:\MTP_scratch` and are not committed. Descriptive AUROCs are pooled, ignore participant clustering apart from the bootstrap where stated, and are not model results. Two earlier numbers are retained from Gate 0 for context (legacy `risky` base rate 34.73%, exposure dependence 0/26.5/61.5/67.1%). Nothing here was tuned on any outcome.

## CRITICAL REVIEW OF THIS PROTOCOL: what could still invalidate it

| # | Weakness | Why it matters | Mitigation or honest statement |
|---|---|---|---|
| 1 | Not blind and no confirmatory data | The target and the primary test were chosen after the data had been seen, including a descriptive null for gaze | Declared up front; every result is "pre-specified but exploratory"; new-data collection is the only route to confirmation |
| 2 | Conditioning on "charged" and on informative stations | The estimand is "choice of an attacked kiosk among those who charged at a mixed station", not overall risk; if gaze affects whether people charge, it is invisible to T1 | T2/S5 reports skip vs charge separately; claims are worded for the conditional estimand |
| 3 | Window includes the keypad stage | Features may reflect the UI path, not the kiosk decision | S2 (first 5 s) and the statement that `t_commit` is only a proxy |
| 4 | Gaze is head-local and coarse | Six summary numbers of eye-in-head dynamics cannot say what was looked at; a null is expected and uninformative about attention | Reported as a limitation; no AOI claims |
| 5 | Exposure offset uses hidden truth | Participants cannot see the attack flag, only cues (image type), so the offset is a design variable, not a participant feature | Used as an offset in every model so that B vs B+G both see it; cue-based features of the *chosen* kiosk are excluded because they are the decision itself |
| 6 | Small effective sample | 220 events (112 participants); the 6-df joint test and a 20x5 CV will have wide intervals; the matched EEG set has only 70 events | Precision statement below; EEG labelled exploratory |
| 7 | Cluster structure poorly estimated | Median 4 rows per participant, ICC estimate 0.000 | Both mixed and cluster-robust fits; within/between decomposition as a sensitivity analysis |
| 8 | Calendar and mode confounds | Risky rate varies by collection day; EEG coverage depends on month; incident mode changes label wording | Period and incident mode are covariates; EEG results stratified by period; S3 |
| 9 | Software availability | R is not installed; a custom random-intercept fit could contain bugs | Decide in Gate 2 with a unit test against a known solution; fall back to clustered logistic regression |
| 10 | Multiple comparisons and researcher degrees of freedom | Many secondary analyses | Holm and FDR families fixed above; exploratory results never promoted |
| 11 | SLM ground truth is stochastic given visible cues | Detection accuracy has a ceiling near 0.79 on image cues alone | The rule baseline and the V1/V2 evidence variants make the ceiling explicit |
| 12 | Unreviewed material | Decision.md D001-D044, the Research Audit PDFs, demographics, several `check_*` scripts were not read | To be read before any claim that depends on them |

## Power and precision statement (approximate, assumptions stated)

Under the primary rows (N = 492, 112 participants, 220 events, event rate 0.45) and a design effect of about 1.0, a two-sided test at alpha 0.05 with 80% power can detect, for **one** standardised predictor, a log-odds ratio of about 0.25, that is an **odds ratio of roughly 1.29 per 1 SD**. A 6-df joint test of the gaze block needs larger effects than that to reach the same power; any single gaze feature with a true odds ratio below about 1.3 per SD is not reliably detectable here. For the matched EEG set (N = 150, 49 participants, 70 events) the corresponding figure is about **1.58 per SD**, so only large EEG effects are detectable.

For discrimination, the participant-bootstrap standard error of a single AUROC on this sample is about 0.02-0.025 (descriptive baselines: 0.659 with SE 0.025; 0.790 with SE 0.020). If B and B+G predictions are strongly correlated (assumed correlation about 0.9, not measured), the paired ΔAUROC standard error would be roughly 0.01-0.015, so a ΔAUROC below about **0.03-0.04** will not be reliably distinguishable from 0; on the matched EEG set the corresponding resolution is roughly 0.07-0.10. Realistic confidence-interval half-widths for AUROC are about ±0.04-0.05 on the primary set and ±0.08-0.10 on the matched EEG set. These are normal-theory approximations using the Gate 0 ICC estimate and should be re-estimated by simulation in Gate 2 before the primary test is run; they are planning figures, not guarantees.
