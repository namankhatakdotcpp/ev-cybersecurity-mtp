# Gate 0 audit: repository and data (read-only)

Status: complete, awaiting approval before Gate 1. No model was trained, no repository code was changed, no experiment was run. Every number below was recomputed from raw files or from committed outputs on the lab workstation unless marked **(unverified)** or **(claim)**. Scratch outputs were written outside the repository (`D:\MTP_scratch\gate0`).

Evidence kinds used: **raw** = recomputed from `backend/raw_data` interaction logs and gaze CSVs, independent of `build_feature_table.py`; **table** = read from the committed `feature_table.csv`; **code** = read from source; **descriptive** = pooled summary statistic, not a model result and not a cross-validated estimate (it ignores participant clustering).

## 0. Headline findings (read these first)

1. **The "risky decision" target is dominated by randomised kiosk exposure, which no existing model uses.** Risky rate by number of attacked kiosks at the station: 0 attacked -> 0.0% (192 of 1,123 rows, 17.1%, risky is impossible), 1 -> 26.5%, 2 -> 61.5%, 3 -> 67.1%. The layout is logged before the decision. Descriptive AUROC of "number of attacked kiosks" alone for risky: 0.767 over all rows, 0.827 among charge decisions. Participants did not avoid attacked kiosks: 48.3% of charge decisions were at an attacked kiosk against roughly 50.9% expected if an available kiosk were chosen at random (approximate).
2. **The existing "behaviour-only" AUROC (about 0.67) is almost entirely a skip-versus-charge detector.** `risky` requires `charge`, so all 315 skips are non-risky. A score that only knew "this participant charged" would reach AUROC 0.715 (computed from the class counts). `window_duration_s` alone has pooled descriptive AUROC 0.664 over all rows but 0.488 among charge decisions (chance). Skip windows are about 5 s, charge windows about 16 s, because charging requires the keypad dialog.
3. **The gaze features show no signal once the skip/charge path is held fixed.** Among the 777 charge rows with gaze, descriptive per-feature AUROC for risky is 0.49-0.52 for all six gaze features. Gaze clusters, fixations and entropy differ strongly between skip and charge (e.g. median clusters 3 vs 5), which is a UI-path effect. The D052 finding that gaze cluster count and entropy are associated with risky decisions (OR 1.66 and 1.32) was estimated over all rows and is plausibly this artifact. This was not re-tested here and is a Gate 2 question, not a conclusion.
4. **The existing ablation already shows gaze not helping behaviour** (committed `final_ablation_table.csv`, random grouped CV, no `rag_contaminated`): behaviour-only AUROC 0.666 [0.632, 0.700]; behaviour+gaze 0.642 [0.605, 0.679]; gaze-only 0.631 [0.592, 0.671].
5. **The premise "the assistant is not a recommendation engine" is contradicted by the code and the logs.** `ai_assistant.py` builds a "Help Agent" prompt that recommends the safest kiosk, is fed previous-station attack outcomes, screenshot analysis and a RAG store, and has experimenter "malicious override" templates. All 95 logged assistant requests (38 sessions) carry the same text, "Recommend the safest available kiosk...". The assistant's responses and the benign/malicious condition are **not logged** anywhere in the raw data, so which sessions saw which condition cannot be recovered.
6. **No untouched test set exists.** D045 through D063 iterated on the same 126 participants. Any confirmatory claim needs new data or a pre-registered analysis with a clearly labelled exploratory status for everything already seen.
7. **Reproducibility is broken on any machine but the original Mac.** 25 hardcoded absolute home-directory path occurrences (original machine) remain in 13 Python files (including 5 in `build_feature_table.py`, so the committed feature table cannot be regenerated here without edits).

## 1. Repository inventory

- Git: branch `main`, 12 commits ahead of `origin/main`, no uncommitted tracked changes at the start (backup branch `backup-mac-history-963d319` holds the old Mac history). The remote and the original Mac history share no common ancestor (probably a history rewrite before the repository went public, cause not confirmed); at the time of the sync their contents differed only by the post-D057 additions.
- Tracked files: about 36 before this report; `backend/pipeline` has 23 tracked files plus `video_pilot/` (6). No `docs/` existed before this gate.
- Documents: `README.md`, `Decision.md` (D001-D063, about 2,600 lines), four Research Audit PDFs, two `.docx`. **I have read Decision.md only in part (D020, D026, D030, D045-D063 in varying depth) and have not read the PDFs or the `.docx` files in this gate.** Treat statements here about earlier decisions as limited to what was read.
- Implemented vs executed vs reproducible:

| Item | Implemented | Executed (per Decision.md / committed outputs) | Reproducible on this machine today |
|---|---|---|---|
| `build_feature_table.py` | yes | yes (D034+) | no (Mac paths; EEG decode folders and raw data now local, so fixable) |
| `train_baselines.py`, `final_ablation_table.py` | yes | yes; outputs committed as CSV | `train_baselines.py` yes (paths made portable in commit `5f037bf`); `final_ablation_table.py` no (1 Mac path) |
| `train_mlp.py` | yes (38 lines) | yes (D037); **results not saved to any file**; baseline numbers hardcoded in the script | partly (imports `train_baselines`) |
| `mixed_effects_model.py` (D052) | yes | yes | no (Mac path) |
| `train_production_model.py`, `calibrate_risk_model.py` | yes | yes; model artifact committed | no (Mac paths) |
| `compare_slm_classifiers.py` | yes | yes on this machine (D063), results outside repo | yes (paths now portable) |
| `session_qc.py` | yes | smoke-tested (D053) | no (Mac paths) |
| Live warning path | scaffold only | never run live | not applicable |

- Stale or contradictory documentation found: `SCHEMA.md` says video is "confirmed absent from the dataset entirely" (superseded by D059: 158 mp4s exist) and quotes "132/140 participants" for behavioural availability (the table has 126 participants); `README.md`/Decision.md use "140 sessions" while the raw folder holds 139 session folders for 132 participant ids.
- Results storage: `phase4a_ablation_results.csv` and `final_ablation_table.csv` are overwritten by their scripts; there is no experiment registry, no run ids, no environment capture. Seeds: `RANDOM_STATE = 42` is used consistently; cross-validation is a single `GroupKFold(5)` with no repeats.
- Tests: 29 unit tests across four files (gaze online, head-pose consumer, RAG reset, warning system). None cover the labelling or feature-table code.

## 2. Data inventory

Raw (`backend/raw_data`):
- 139 session folders; 132 distinct participant ids, contiguous 1-132. One folder has a non-standard name (a duplicated id suffix and a trailing free-text note; the pipeline parses the leading id 126).
- Six participants have more than one folder: 001 (2), 022 (2), 034 (2), 055 (3), 064 (2), 082 (2). The pipeline keeps the folder with the most interaction lines and drops the rest; these drops are documented in D019/D029 but the rule is a heuristic ("larger log = the real session").
- Missing files: 1 folder without an interactions log, 1 without `consent.json`/`demographics.json`/`system_config.json`; `final_points.json` is absent from 97 of 139 folders (it appears only in later sessions). 8 folders have no gaze file (6 are duplicate/aborted folders; the canonical sessions without gaze are 069 and 132).
- Gaze file naming is irregular: 001/002 use `varjo_gaze_output_<timestamp>.csv`, 032 has `032_1.csv` and `032_2.csv`, 011 has a gaze file my reader could not decode as UTF-8 (the pipeline obtained gaze rows for 011, so which file it used is unverified).
- Session dates: 37 distinct collection days, 2026-04-19 to 2026-08-03. Both `incident_mode` configurations were run (64 participants False, 61 True, 1 unknown).
- Personal data: `demographics.json` (age, gender, education, specialization, EV experience, driving experience) exists for nearly every session. It has not been used in any model and has not been audited here.
- Video: 158 mp4s and 169 gaze CSVs in `Varjo/` (D059); outside the scope of the feature table. Two mp4s are truncated.

Analysis table (`feature_table.csv`, raw-recomputed): 1,123 rows, 126 participants, 126 sessions. My independent parse of the raw interaction logs reproduces the table's per-session row counts exactly (0 mismatches over 126 sessions). Six participants have no rows (near-empty logs, zero station events, per D052).

## 3. Decision unit

- One row = one station visit: from the `Flowgraph Reached` event to the first `charging`/`disabled_charging` event (decision "charge") or `driving` event (decision "skip").
- 1,123 rows; 808 charge, 315 skip.
- Decisions per participant: min 1, median 8.5, mean 8.9, max 23. 6 participants have exactly 1 decision, 8 have 2 or fewer, 99 have 5 or more. Distribution: 1:6, 2:2, 3:13, 4:6, 5:6, 6:12, 7:9, 8:9, 9:7, 10:10, 11:9, 12:9, 13:6, 14:1, 15:8, 16:4, 17:5, 19:2, 21:1, 23:1.
- Attack vs benign exposure per participant is **not balanced**: attacked kiosks per station average 1.23 (median) per participant, ranging from 0.00 to 3.00; 2 participants never saw an attacked kiosk. Overall: 192 stations had no attacked kiosk, 533 had one, 322 had two, 76 had three. Of 2,994 available kiosk records, 50.3% were attacked. Image type is an imperfect cue: kiosks with a "deepfake" image were attacked 78.7% of the time, "real" images 20.2% (consistent with the configured 0.8/0.2 probabilities), and `discount_coupon` is not decisive either.
- Exposure is randomised by the game, so it is a design variable, not a participant trait. It must be conditioned on or offset in any analysis.
- Repeated measures are real: this is a many-decisions-per-participant design, so a participant random effect is the natural model and participant-grouped CV is mandatory.

## 4. Labels

- Pipeline definition (`train_baselines.py::make_label`): risky = `decision == "charge"` and `kiosk_attack` in {`Cyber Attack`, `System Anomaly`}.
- **Normalisation verified from raw data.** The logged `kiosk_attack` string agrees with the layout's own `attack` flag for the chosen kiosk in 815 of 815 charge events (421 Safe, 394 attacked). The label vocabulary is determined by the session's `incident_mode`: config False yields `System Anomaly`, config True yields `Cyber Attack`, with no exceptions (16 rows have no config and still match their layout). The D045 labelling bug is fixed in the current code.
- Base rate (raw-recomputed, equals the table): **decision level 390/1,123 = 34.73%**; among charge decisions 48.27%; charge rate 71.95%.
- Participant level: 112 of 126 participants (88.9%) have at least one risky decision; mean participant risky rate 35.1%, median 32.5%; 14 participants have none, 5 have all of theirs risky (4.0%); 35 participants have a rate of 0.5 or more; 47 have at least 4 risky decisions. **The figure "~49 positive participants" could not be reproduced** under any participant-level definition I tried (rate >= 0.4 gives 55, >= 0.5 gives 35, >= 4 risky gives 47). It needs a definition from you (open question 1).
- Label noise and ambiguity: (a) risky mixes two things, whether the participant charged and whether the chosen kiosk was attacked; (b) the same participant behaviour yields different labels depending on the randomised layout; (c) `disabled_charging` follows `charging` in the logs and is correctly not counted as a second decision; (d) "post-charge vehicle fault" is not used anywhere in the pipeline (no occurrence in `backend/pipeline/*.py`).
- Time structure: the decision-level risky rate varies from 0.08 to 0.60 by collection day (days with at least 15 rows). The rate is 0.355 in non-contaminated and 0.333 in RAG-contaminated sessions.

## 5. Feature timing audit

Prediction timestamp is not stated anywhere in the existing code. The window is [`Reached`, decision event], so every windowed feature ends at the decision commit as logged by the backend. The kiosk selection click (Set Amount, Confirm) is **not** logged, so the moment the participant committed to a kiosk is unknown.

| Feature | Modality | Definition | Window | Missingness | Class | Flag |
|---|---|---|---|---|---|---|
| `window_duration_s` | behaviour | Reached to decision event, seconds | whole window | none | during | Equals decision latency, only known when the decision happens; strongly separates skip (about 5 s) from charge (about 16 s). Not usable for a before-commit warning |
| `ai_help_used` | behaviour | any `assistant_chat` event in the window | whole window | none | before/during | 8.1% of rows; response content and condition not logged |
| `rag_contaminated` | session flag | session in D029 list | static | none | unknown | Session-level proxy for collection period; not a decision feature; already excluded from later models |
| `decision`, `kiosk_used`, `kiosk_attack` | outcome | the choice and its attack status | at decision | none | **after/at decision** | Label ingredients; must never be features |
| `charge_amount`, `points_lost` | outcome | amount delivered, points before minus after | after decision | none | **after decision** | Consequences. Median charge is 12 for risky vs 40 for safe charges (game mechanic reduces charge when attacked) |
| `gaze_n_fixations`, `gaze_n_clusters`, `gaze_n_transitions`, `gaze_transitions_per_fixation`, `gaze_dispersion`, `gaze_entropy_bits` | gaze | I-VT (30 deg/s, 100 ms) on head-local `gaze_forward`, DBSCAN eps 0.08 | whole window | 5.9% of rows missing (66 rows), 4 participants fully missing | during, but includes the post-selection keypad/confirm segment | Partly after-decision because commit time is unknown; they encode the UI path length |
| `eeg_*` (16 band powers + `eeg_low_motion_fraction`) | EEG | relative Welch band power, low-motion subset | whole window, at least 2 s | 71.1% of rows missing | during (same caveat) | Motion threshold is the median of the whole session's accelerometer magnitude (session-wide statistic, mild look-ahead, not outcome-related) |
| `trial` | design | station number | static | none | before | Time-in-session proxy; not currently a model feature |
| layout fields (`attack` per kiosk, image, coupon, `cyber_attack_mode`, availability) | design | `StationGenerated` event | logged after `Reached`, before the decision in all 1,123 events | none | **before decision** | **Not in the feature table at all**, and the strongest available predictor |

Only before/during features relative to a stated prediction timestamp are eligible; Gate 1 must fix that timestamp. Outcome-adjacent variables (`decision`, `kiosk_used`, `kiosk_attack`, `charge_amount`, `points_lost`) are correctly outside the model feature sets.

## 6. Leakage review of existing experiments

| Experiment | Splits and preprocessing | Verdict |
|---|---|---|
| `train_baselines.py` (Phase 4A) | `GroupKFold(5)` by participant; imputer and scaler fit inside each training fold; fixed hyperparameters; mean of fold metrics; folds with a single class skipped silently | No row-level leakage found. **Invalid as evidence about modality value** because of findings 1-3 (exposure and the skip/charge path) |
| `final_ablation_table.py` | pooled out-of-fold predictions, participant-level bootstrap (2,000), plus a single time-ordered 75/25 participant split (about 31 test participants) | No leakage found. Reproducible after path fix. Same target confounds. The time split is one split on a calendar confound |
| `check_cutoff_sensitivity.py`, `check_seed_sensitivity.py`, `check_time_confound*.py` | not read line by line in this gate | Not assessed (**unverified**) |
| `mixed_effects_model.py` (D052) | participant random effect; Attempt 1 is circular (the chosen kiosk's attack type and risky are the same fact); Attempt 2 uses station layout | Read via D052 only. The gaze association is over all rows, so it is confounded with skip/charge. **Preliminary** |
| `train_mlp.py` (D037) | same grouped CV | Gate compared against baseline numbers hardcoded from a result file after the best baseline was already chosen; MLP output not saved. **Preliminary** |
| `train_production_model.py`, `calibrate_risk_model.py` (D055/D057) | production model fit on all rows (in-sample accuracy 1.0, meaningless); calibrator and thresholds chosen from pooled out-of-fold probabilities of the same dataset | Operating-point figures (77% would warn) are measured on the data used to choose the thresholds, so they are optimistic by construction. Scoring the training sessions is a demonstration |
| `compare_slm_classifiers.py` (D063) | one fold, 212 rows, zero-shot | **Preliminary**, not a ranking |

Cross-cutting: there is no locked, untouched test set. About twenty analyses (D045-D063) were run on the same participants, with the labelling fix (D045) and several design choices made after seeing results. Even with correct splits, the headline numbers carry a forking-paths risk that grouped CV does not remove.

Results I would treat as **invalid** for modality claims: all B/G/EEG ablation AUROCs on `risky` as currently defined. **Preliminary**: D052 gaze associations, D037 MLP, D057 operating point, D063 SLM numbers. **Reproducible after path fix**: Phase 4A and the final ablation table.

## 7. EEG

- Decode summary: 76 participant folders decoded; 69 with `overlap_confirmed` timestamp sync, 6 `NO_OVERLAP_MISMATCH`, 1 with no samples. Applying the pipeline's rule (sync confirmed, flatline fraction below 0.15, gap fraction below 0.5) yields **67 qualified participants, matching D019**. 65 of them appear in the feature table.
- QC of the qualified set: median recording 23 minutes, median maximum flatline fraction 0.010, median gap fraction 0.000, 256 Hz, 4 channels (TP9, AF7, AF8, TP10).
- **Row-level coverage is much lower than participant-level coverage:** the 65 table participants contribute 564 rows, but only 324 rows (57%) have a usable EEG window (at least 2 s of samples in the decision window). 58 participants have at least one usable row; with gaze as well, 308 rows from 56 participants. Why 43% of qualified-participant windows are empty was not investigated (open question).
- Selection bias (participant level, EEG-qualified vs rest, unadjusted Mann-Whitney, exploratory, 8 tests): decisions per participant 8.7 vs 9.2 (p 0.80); risky rate 0.370 vs 0.331 (p 0.46); charge rate 0.742 vs 0.712 (p 0.95); gaze-valid fraction 0.937 vs 0.952 (p 0.41); median window duration 19.4 vs 14.9 s (p 0.035, not significant after correction for 8 tests); mean attacked kiosks per station 1.31 vs 1.20 (p 0.11); AI help 0.103 vs 0.078 (p 0.83). Demographics were not compared.
- **EEG coverage is strongly tied to collection period:** 77% of April participants, 65% of June, 35% of July, 0% of August. Any EEG-versus-no-EEG contrast is therefore also a calendar contrast.
- Motion: only a median-accelerometer split is used; there is no ICA or blink handling, so any EEG finding stays exploratory. Rows for one participant are not independent.
- Existing EEG results (`final_ablation_table.csv`): EEG-only AUROC 0.579 [0.507, 0.647] on 324 rows from 58 participants; behaviour+gaze+EEG 0.647 [0.565, 0.726] on 308 rows from 56 participants (random grouped CV), with the same target confounds as above.

## 8. Gaze

Raw gaze QC over the canonical sessions (122 readable files):
- Sampling rate 199.5 Hz (range 199.4-199.6), no non-monotonic timestamps.
- `status == 2` (tracked) averages 93.5% of samples; **valid fraction (status 2 and stability above 0) averages 72.3%, median 76.5%**. 37 sessions are below 0.7, 8 below 0.5 and 4 below 0.3 (participants 008, 015, 016, 038; the loss is mostly the `stability > 0` filter, matching D022). Large tracker gaps exist (maximum single gap 848 s in one session).
- Windows: 1,057 of 1,123 rows (94.1%) have gaze features (122 participants). Participants 069, 082, 093 and 132 have no gaze rows; 093 has a gaze file yet no usable windows, which is **unexplained**.
- Computable AOI-free features: all six are computable. Caveats on trustworthiness: (a) `gaze_forward` is head-local, so the features describe eye-in-head dynamics, not where on the screen the participant looked; (b) fixation thresholds are fixed constants never validated against ground truth; (c) the features mostly reflect how many UI steps the participant performed (skip vs charge); (d) per-window valid-sample counts were not audited.
- The AOI route is closed for the existing data: D060-D062 found video-based AOI mapping not validated (a pinhole `gaze_forward` fit was suggestive for one participant but failed the held-out bar). This audit does not reopen it.

## 9. SLM and RAG state

- Hardware: RTX 4090, 24 GB VRAM (about 5 GB used by desktop apps), 128 GB RAM, 32-core CPU, Ollama 0.40.10. Local models actually present: `mistral:7b-instruct`, `llama3.1:8b`, `phi3:3.8b`, `gemma2:9b`, `qwen2.5:7b` (all verified in `ollama list`; model names were taken from the installed list, not assumed). D063 confirmed GPU inference at 100%.
- The in-game assistant (`ai_assistant.py`) is a **recommendation engine**: a "Help Agent" prompt recommends the safest available kiosk from screenshot analysis of the three kiosks, previous-station outcomes (which include the true attack flag of kiosks the participant already used) and a RAG store of earlier events. Default backend Gemini (`gemini-2.5-flash-lite`) or OpenAI (`gpt-4o-mini`); a local SLM path exists. Malicious "experimenter override" templates exist (D024/D028/D038/D046) that force a recommendation regardless of analysis.
- What the raw logs contain: 95 assistant requests in 38 sessions, all with the same prompt text. No assistant response, no condition (benign vs malicious) and no model name is logged. The effect of the assistant on decisions can therefore not be analysed reliably from existing data, and `ai_help_used` is only "asked for a recommendation".
- RAG contamination: 37 sessions (384 table rows) are flagged contaminated by D029.
- Labelled scenario set: **none exists** in the repository. Ground truth can come from simulation metadata: 3,594 kiosk records from logged `StationGenerated` events, each with attack flag, image file, coupon flag, `cyber_attack_mode` (null, reduced, blocked) and availability. Caveat: attack is stochastic given the visible cues (deepfake image 78.7%, real image 20.2%), so a "correct" SAFE/UNSAFE label is not always inferable from what a model can see; a scenario set must say which evidence is shown.
- D063's SLM comparison gave the models only the post-hoc behaviour and gaze numbers, not the kiosk, so it tests the wrong question for an SLM and must not be mixed with a detection or recommendation benchmark.

## 10. Warning scaffold

- Offline scoring only: `score_session_offline()` runs on completed sessions (the module states this). Online performance has never been measured and none is claimed here.
- The risk model uses `window_duration_s`, which is only known when the decision ends, and window-level gaze features computed over the whole window; it cannot run before the decision. `gaze_online.py` (D056) reproduces the offline features on replayed logs only.
- Mismatch between message and model: the warning text says the kiosk "looks unusual", but the model never sees any property of any kiosk. It predicts the participant's own decision from behaviour and gaze.
- Calibration and thresholds: a Platt calibrator was fit on pooled out-of-fold probabilities; its calibration curve was non-monotonic before calibration; thresholds 0.25/0.50 were read off the same out-of-fold distribution. At these thresholds about 77% of decisions trigger a warning, so the warning would fire for most decisions.
- **False-safe rate and false-warning rate are not reported anywhere**, and neither is a cost model. With exposure ignored, the target is partly unpredictable by construction.
- Distinguish: offline prediction (exists, weak) versus online warning (does not exist) versus a human-validated warning (Step 13, not started).

## CRITICAL REVIEW

| # | Problem | Evidence | Severity | Why it matters | Correction |
|---|---|---|---|---|---|
| 1 | Target confounded with randomised exposure | risky rate 0/26.5/61.5/67.1% by 0/1/2/3 attacked kiosks; 17.1% of rows cannot be risky; exposure AUROC 0.77 | Critical | Behavioural and gaze models are scored against a label mostly set by the layout | Define the target relative to exposure (for example choice of an attacked kiosk among charges, or a model with exposure as offset) and report an exposure-only baseline |
| 2 | Existing AUROC is a skip-vs-charge artifact | ceiling 0.715 from class counts; `window_duration_s` AUROC 0.664 overall, 0.488 among charges | Critical | Headline results do not measure risk discrimination | Condition on charge decisions or define the target on charge decisions |
| 3 | Gaze "signal" likely the UI path | gaze AUROC 0.49-0.52 among charges; strong skip/charge differences | High | The only gaze finding (D052) may not survive | Test within charge decisions in Gate 2 |
| 4 | Prediction timestamp undefined; commit time not logged | window ends at the decision event; Set Amount/Confirm not logged | High | Features include post-commit behaviour | Fix a timestamp (for example the `charging` event) and state the limitation, or restrict to features available before the keypad |
| 5 | No untouched test set; forking paths | D045-D063 on the same 126 participants | High | Reported intervals understate uncertainty | Pre-register Gate 2/3, label old results exploratory, plan new-data confirmation |
| 6 | Assistant conditions and outputs not logged | 95 identical requests, no response or condition | High | AI effect cannot be analysed; premise in the brief is wrong | Treat `ai_help_used` as a request flag only; design logging for any new data |
| 7 | Reproducibility | 25 Mac paths in 13 files; no registry; overwritten outputs | Medium | Cannot regenerate the table or re-run experiments | Config-driven paths and a lightweight run registry (Gate 2 prerequisite) |
| 8 | EEG subset is time-confounded and thin | 77/65/35/0% coverage by month; 57% of qualified rows usable; 56 participants with gaze+EEG | Medium | Any EEG gain is confounded with period and underpowered | Matched-subset design only; exploratory label |
| 9 | Warning scaffold is not an online system and reports no false-safe/false-warning rates | see section 10 | Medium | A fixed 77% warning rate would mostly fire | Do not claim online value; report both error rates |
| 10 | Duplicate folders and near-empty logs handled by heuristic | 6 duplicated ids; 6 participants with no events | Low-Medium | Selection can bias | Written exclusion rules before Gate 2 |
| 11 | Quality of a few inputs unclear | session 011 gaze file decode error; participant 093 has a gaze file but no windows | Low | Possible silent data loss | Inspect before Gate 2 |
| 12 | Unreviewed material | Decision.md D001-D044, the four PDFs, several `check_*` scripts, demographics | Unknown | Audit coverage is incomplete | Say so in Gate 1; read before relying on them |

## Open questions for you

1. What definition gives "~49 positive participants"? Under the definitions I tried the count is 35-112.
2. Should the primary target be redefined to control for exposure (for example, among charge decisions, did the participant pick an attacked kiosk, with the number of attacked and available kiosks as an offset)? The layout is known before the decision, so it could be an allowed covariate.
3. Which sessions, if any, ran the malicious assistant condition? Where might the assistant responses and the condition have been recorded, if anywhere?
4. How should the 6 participants with no station events and the 6 duplicated ids be treated? I propose writing a fixed exclusion rule in Gate 1.
5. Do you want the empty-EEG-window rate (43% of qualified rows) and the 011/093 gaze anomalies investigated before Gate 2?
6. Is new data collection for a clean confirmatory set realistic (the NEW_DATA_COLLECTION_PROTOCOL exists)? Without it, every claim stays exploratory.
7. May Gate 2 include making the pipeline paths configurable and adding a run registry (code changes), or must that be a separate gate?

## After-gate critical review

- **What we learned:** the target is mostly set by randomised exposure; the existing AUROC is mostly skip-vs-charge; gaze adds nothing once the path is fixed; label normalisation and the 67-participant EEG subset are verified; the assistant is a recommendation engine whose outputs are unlogged.
- **What changed:** the decision unit is now an exposure-dependent station visit, not an independent risk sample; "B vs B+G" must be evaluated within charge decisions with exposure accounted for.
- **What failed and why:** earlier ablations answered a different question (charge vs skip) because the label folds a choice and a randomised outcome together; "~49 positive participants" could not be reproduced.
- **Statistically defensible now:** the label definition and base rate (34.7% of decisions, 88.9% of participants with at least one risky decision); the exposure dependence; descriptive evidence that gaze features do not separate risky from safe charges.
- **Not defensible now:** any statement that gaze, EEG or behaviour "predicts risky decisions"; the 77% warning rate as a validated operating point; any claim about the AI assistant's effect; any SLM ranking.
- **To test next (Gate 1 then 2):** B vs B+G within charge decisions with exposure as an offset, mixed model plus grouped CV, participant-level permutation test.
- **Not to test:** deep learning (126 participants, a median of 8.5 decisions each, with the signal question unresolved); AOI recovery from video (closed by D062); EEG before the primary question is settled; any SLM-versus-ML single table.
