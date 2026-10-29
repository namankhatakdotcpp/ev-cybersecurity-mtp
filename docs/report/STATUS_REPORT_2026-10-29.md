# EV charging VR cybersecurity project: status report, 2026-10-29

This report supersedes `EV_Charging_VR_Cybersecurity_Project_Status_Report.docx` (the earlier status report, which predates Gates 1 to 7 and lists the analyses as not done). Item-by-item mapping: `docs/audit/STATUS_RECONCILIATION.md`. Figures below are copied from `docs/report/FINAL_REPORT.md` (generated from `results/registry.csv`); the registry run id or Decision ID is given in brackets. All statements are associations in a small, mostly exploratory sample.

## 1. Where the project stands

The gated protocol (Gates 0 to 7) is complete for the data collected so far. The analyses the earlier report listed as pending have been run and, for the main questions, did not support the hypotheses. What remains is the FPS measurement on the lab workstation, the thesis writing, and three decisions or confirmations outside the repository.

| Gate | Content | State | Evidence |
|---|---|---|---|
| 0 | Repository and data audit | Done | `docs/audit/GATE0_audit.md` (D064) |
| 1 | Protocol v1 frozen (tag `protocol-v1`) | Done | D065, D066 |
| 2 | Primary hypothesis H1 | Done, not supported | `h1_claim_a`, `h1_claim_b` (D067) |
| 3 | ML benchmark | Done, negative | `g3_grid_*`, `g3_secondary_S1`, `g3_secondary_S2` (D068) |
| 4 | EEG on the matched subset and selection-bias report | Done, exploratory | `g4_s6_*`, `g4_selection_bias` (D069) |
| 5 | Small language models | Done, negative | `g5_slm_*`, `g5_malicious_*` (D070 to D083) |
| 6 | Reduced descriptive and error analysis, follow-ups | Done, exploratory | `g6_*` (D072 to D075) |
| 7 | Final report from the registry | Done | `docs/report/FINAL_REPORT.md` (D082, D083) |

## 2. Key findings

1. **The original "risky" label is largely exposure-driven.** Risky rate rose with the number of attacked kiosks at a station: 0.0% with none, 26.5% with one, 61.5% with two, 67.1% with three; layout alone gave an AUROC of 0.827 among charge decisions (Gate 0 audit, D064). The target was therefore redefined to the chosen kiosk being attacked, given a charge at a station with both attacked and safe kiosks (D065). The redefinition was made after the data had been seen.
2. **H1 is not supported.** Primary set 492 rows, 112 participants, 220 events [`h1_claim_a`]. Gaze beyond behaviour and exposure: LRT chi-square 8.17, df 6, p = 0.226; permutation p = 0.387 [`h1_claim_a`]. Out-of-sample AUROC difference +0.005 [-0.006, +0.015] [`h1_claim_b`].
3. **No pre-specified model beats the exposure-only reference.** Best mean AUROC 0.633 [0.576, 0.686] (ridge, gaze set); the reference, ridge with exposure only, is 0.627 [0.569, 0.681]; all 12 model-set pairs overlap [`g3_grid_ridge`, `g3_grid_rf`, `g3_grid_hgb`]. The tie rule selects the exposure-only reference as the best predictive model.
4. **EEG is not established.** On identical rows (150 rows, 49 participants, 70 events) adding EEG to gaze and behaviour gave +0.031 [-0.013, +0.070] [`g4_s6_ridge`]. The EEG rows are a biased subset: 41.1% of decision windows fall after the recording ended [`g4_selection_bias`]. Cohort funnel: `docs/audit/EEG_COHORT_FUNNEL.md`.
5. **Small language models do not show reliable detection above the rule baselines.** Five models, 240 stations. Best rule baseline balanced accuracy 0.730 (cue-free) and 0.723 (with image descriptions); models 0.384 to 0.562 [`g5_slm_*`]. With image descriptions, false-safe fell but false-warning rose to 0.45 to 0.74, and the descriptions can reveal the image type. Recommendations on mixed stations were near the random-choice rate (0.514 to 0.515). With an explicit instruction to recommend an attacked kiosk, the models chose the designated target at 0.98 to 1.00 of 60 stations, against 0.25 to 0.45 without the instruction [`g5_malicious_*`]; this is instruction-following only.

## 3. Claims register (from `FINAL_REPORT.md`, section 9)

| Claim | Status |
|---|---|
| Gaze adds to behaviour for the redefined target (H1) | Not supported |
| Any pre-specified ML model beats exposure-only | No |
| EEG adds information | Not established (biased subset, low power) |
| Skipping follows exposure | Not supported |
| Any tested SLM showed reliable detection above the rule baselines | No |
| A best SLM | Not claimed |
| Any tested SLM recommends a safe kiosk above chance | No |
| The tested SLMs follow an instruction to recommend an attacked kiosk | Yes, in this setup (instruction-following only) |
| A warning operating point is validated | No |
| A best overall system | Withheld |

## 4. Deviations and disclosures (all logged)

- The target was redefined after Gate 0 (D065); there is no untouched test set (D045 to D063 iterated on the same participants).
- The Gate 5 format pilot and accuracy pass started before a recorded approval (D071); a provisional scoring look preceded the scoring spec (D078); the override condition was then rerun under a rule written first (Amendment A2, D083).
- Duplicate consistency rows from a resumed mistral run: the first reply per item and seed is scored; one missing reply was filled (D076, D083).
- Post-hoc follow-ups are labelled as such (D074, D075).
- History rewrite before the push (D077), with `docs/audit/HASH_MAP.md`; the `protocol-v1` tag was moved to the rewritten protocol commit and the protocol file is byte-identical.
- Local backups removed after the push (D084).

## 5. Open items

| Item | State | Needs |
|---|---|---|
| FPS before/after measurement (target about 90 FPS) | Not done | the lab workstation; protocol being prepared |
| Results chapter and thesis | Outline and generated report only | writing, in progress |
| Participant-code and session-folder linkage in older public files | Open | supervisor decision under the consent terms (`docs/audit/LEGACY_EXPOSURE_PLAN.md`) |
| Machine-specific paths in 13 Python files | Planned | approval (`docs/audit/HARDCODED_PATHS.md`) |
| Missing session log for one EEG recording | Open | the lab |
| Integrated gaze or EEG risk-warning system | Not built, not claimed | out of scope for the existing data |
| New data collection and automation-bias experiment | Future | design recommendations in `docs/report/SUPERVISOR_BRIEF.md` |

## 6. Progress estimate

These are my planning estimates, not measurements, and they treat "done" as "committed with evidence".

| Workstream | Estimate | Basis |
|---|---|---|
| Audit, protocol and research design | about 95% | Gates 0 and 1 done; literature review not in the repository and not re-checked here |
| Analyses on the existing data | about 90% | Gates 2 to 6 done; descriptive error analysis reduced; no untouched test set possible |
| Reproducibility package | about 80% | registry, generated report, `docs/REPRODUCE.md`; machine paths in 13 files remain |
| Language-model track | about 90% | scored and registered; hardware-specific compliance numbers not re-measured |
| FPS measurement | about 10% | candidates and a protocol only; nothing measured |
| Thesis writing | about 25% | outline, generated final report; chapter text not yet written |

## 7. What must not be claimed

- Any measured FPS improvement.
- That gaze or EEG add predictive value, or that a language model is a reliable detector.
- That a language model benefits users or that the in-game assistant was tested.
- A causal reason for risky decisions: all results are associations.
- A final EEG sample size beyond the funnel in `EEG_COHORT_FUNNEL.md`.

## 8. Critical review

- **What could still be wrong:** the progress percentages are judgement; the literature review and novelty analysis are not in the repository, so their state is taken from the earlier report; the 10% for FPS is a placeholder for a task with no data.
- **Not done:** the old report in Downloads has no "superseded" header, because it lies outside the repository and I did not edit a file outside it; this report states the supersession instead.
