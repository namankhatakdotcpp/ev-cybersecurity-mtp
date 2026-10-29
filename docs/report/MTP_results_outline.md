# Results chapter outline

Built only from existing reports and the registry. No new analysis was run to write it. Every number below is quoted from `docs/analysis/GATE2_report.md` to `GATE6_report.md`, `docs/audit/GATE0_audit.md` or `results/master_table_gate5.md`. Anything marked (not run) was not done. Wording rule: "associated with" and "not detected", never causal language, never "predicts" for a result that failed to beat its baseline.

## 1. Framing of the results chapter

- **Question as originally posed:** can gaze, EEG or a language model flag a risky charging decision in the VR simulation?
- **What the audit changed (Gate 0):** the target was dominated by randomised kiosk layout; the earlier behaviour AUROC of about 0.67 was largely a skip-versus-charge detector; no untouched test set exists. The chapter therefore reports a redefined target and presents everything as exploratory or pre-specified-negative.
- **Data in one table:** 126 participants in the feature table; primary set 492 rows, 112 participants, 220 events; EEG-matched set 150 rows, 49 participants, 70 events; SLM scenario set 240 stations, 599 available kiosks.

## 2. Methods summary (point to Protocol v1)

- Target T1 and the exposure offset logit(n_attacked / n_available).
- Feature blocks: exposure/design (B0), behaviour (B), gaze (G), EEG.
- Models: random-intercept logistic (marginal ML), ridge with offset, random forest, boosting.
- Evaluation: repeated participant-grouped nested CV, participant-level bootstrap, block permutation, Holm over {S1, S2, S5, S6}, BH-FDR for exploratory S8.
- Process controls: frozen protocol (tag `protocol-v1`), config committed before each run, experiment registry, generated tables, Decision.md.

## 3. Results sections

### 3.1 Descriptive audit findings (Gate 0)
- Risky rate by number of attacked kiosks: 0 attacked 0.0%, 1: 26.5%, 2: 61.5%, 3: 67.1%. Layout alone: AUROC 0.827 among charge decisions.
- Charge decisions at an attacked kiosk 48.3% against about 50.9% expected by random choice.
- Window duration is chance (0.488) among charge decisions; skip windows about 5 s, charge windows about 16 s.
- Gaze features 0.49 to 0.52 per-feature AUROC among charge rows.
- Figure/table candidates: risky rate by exposure; skip vs charge window length.

### 3.2 Primary hypothesis H1 (Gate 2)
- LRT chi-square 8.17, df 6, p = 0.226; permutation p = 0.387; paired AUROC +0.005 [-0.006, +0.015]. Not supported.
- Sensitivity: E2 p = 0.310; S4 p = 0.331; S3 (RAG-free subset) p = 0.019, reported as hypothesis for new data, not a finding.
- Table candidate: Claim A and sensitivity table.

### 3.3 ML benchmark (Gate 3)
- Ridge B0 0.627 [0.569, 0.681]; B 0.626; G 0.633; BG 0.631. All paired differences to B0 span zero. Random forest worse (B -0.021, BG -0.035).
- Calibration: ridge slopes near 1 with wide CIs; boosting over-confident.
- Operating point B (recall about 0.80): false-warning 0.59 to 0.61 for ridge, no improvement over B0.
- S1 p = 0.253; S2 p = 0.590.
- Table candidate: the generated master table (`results/master_table_gate3.md`).

### 3.4 EEG (Gate 4)
- BGE minus BG +0.031 [-0.013, +0.070]; permutation p = 0.22; 17-df LRT p = 0.027 (descriptive, unreliable at 70 events, Holm upper bound 0.11).
- Noise-column diagnostic: +0.006 for 17 random columns (post-hoc).
- Selection bias: 41.1% of windows fall after the recording ended; trial index SMD -0.53 [-0.83, -0.29]; April share 49% vs 22% (FDR 0.012).
- Statement allowed: "not established"; not "no effect".

### 3.5 Exposure baseline and exploratory follow-ups (Gate 6 reduced, D072 to D075)
- B0 coefficients all null; offset slope 1.10 [0.68, 1.52]; observed minus exposure -0.046 [-0.088, -0.004] (one signal at three levels, not a finding).
- S5 (skip vs charge): skip rate 29.7 / 28.2 / 25.9% by station type; B+G minus B +0.005; window length alone AUROC 0.887, so not a gaze result.
- Extended ridge grid: null survives. EEG detrending: null survives (+0.030 [-0.015, +0.070], p 0.18).

### 3.6 Language models (Gate 5; kept separate from the ML track)
- Pilot: all five at least 95% format-compliant.
- Detection (accuracy pass): no model beats the best reference under the pre-committed rule; without image descriptions most attacked kiosks are called SAFE; with descriptions models warn indiscriminately (false-warning 0.45 to 0.74).
- Recommendation: safe-kiosk choice not above the 51.5% random-choice rate; all-attacked stations: attacked kiosk chosen 85 to 100% in V1.
- Consistency (5 seeds, T=0.3): same rates within about 0.02; identical replies 0.82 to 1.00; gemma2 V1 degenerate in 5 of 5 seeds.
- Malicious-override condition: run (600 replies) but **not scored** (decision pending). The chapter must say so.
- Disclosure paragraph: forking-paths caveat from the provisional look (D078).
- Table candidates: master table 2a to 2d (detection), 5a to 5c (recommendation), 6 (consistency).

## 4. Cross-cutting discussion points

- Why exposure explains the target: the layout is randomised and logged before the decision.
- Why gaze and EEG nulls are not evidence of irrelevance: power (SE of the EEG contrast 0.020; differences below about 0.06 not distinguishable), minimal EEG preprocessing, window defined by the decision event.
- Why SLM results do not transfer to a deployed assistant: text-only, single scenario set, descriptions from another model, no live interaction.
- What the project can defensibly claim (see section 5).

## 5. Claims register

| Claim | Status |
|---|---|
| Gaze adds to behaviour for the redefined target (H1) | Not supported |
| Any pre-specified ML model beats exposure-only B0 | No |
| EEG adds information | Not established (biased subset, low power) |
| Skipping follows exposure | Not supported (rates about 26 to 30% in every station type) |
| Any tested SLM detects attacked kiosks better than simple rules | No |
| Any tested SLM recommends a safe kiosk above chance | No |
| An SLM can be steered by a malicious instruction | **Not assessed** (unscored) |
| A warning operating point is validated | No |

## 6. Limitations section (copy list)

- 126 participants; no untouched test set; D045 to D063 iterated on the same data.
- EEG rows are an early-session, April-heavy subset; preprocessing minimal.
- Assistant responses and benign/malicious condition were not logged.
- Window ends at the decision, so duration and gaze counts are mechanically linked.
- Several grids selected their own lower edge; a wider ridge grid gave the same conclusion.
- SLM set is quota-sampled; one main decoding setting; mistral consistency file irregular (one pair missing).
- A provisional scoring look preceded the Gate 5 scoring spec (D078).
- Many strata and sensitivity runs; unadjusted p-values are descriptive.

## 7. Open items before the final report (Gate 7)

1. Decide whether to score the malicious pass (needs a rule fixed first).
2. Define the roughly 49 positive participants and how they are used.
3. Make the remaining Mac paths configurable; read D001 to D044 and the audit PDFs in full.
4. Generate the final tables from the registry and re-check every quoted number against the generated files.
5. New data collection design: log decision latency, gaze before the decision, assistant responses and condition, full-session EEG.

## 8. Suggested chapter structure

1. Introduction to the results and the audit correction
2. Methods summary and process controls
3. Descriptive findings
4. H1 and sensitivity analyses
5. ML benchmark
6. EEG and selection bias
7. Exposure baseline and exploratory analyses
8. Language models
9. Synthesis, claims and limitations
