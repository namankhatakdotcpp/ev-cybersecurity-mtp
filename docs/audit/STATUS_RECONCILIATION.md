# Status report reconciliation (read-only)

Date: 2026-10-29. Source compared: `EV_Charging_VR_Cybersecurity_Project_Status_Report.docx`. **That file is not in the repository**; it was attached from the user's Downloads folder, so I read it from there and did not copy it in. The old report has not been edited. Evidence is a commit hash or a `Decision.md` ID; result numbers are not repeated here (they are in `docs/report/FINAL_REPORT.md`, generated from `results/registry.csv`).

Legend: **Done** = finished and committed. **Done, negative** = finished; the result does not support the hypothesis. **Partial** = some of it done. **Open** = not done.

## A. Items in the old report's work-status table (section 9)

| Old report item | Old status | Current state | Evidence |
|---|---|---|---|
| Project/codebase understanding | Done / strong | Done | D004 to D018; `docs/audit/GATE0_audit.md` (`de3c4d5`, D064) |
| Behaviour + gaze dataset audit | Mostly done | Done | Gate 0 audit (`de3c4d5`); D034 |
| EEG decoding/investigation | Substantial progress | Done for decoding; cohort funnel now documented (67 screened, 49 matched) | D013, D014 (decoder fix, 76/76), D019 (inclusion rule), D034; funnel in `EEG_COHORT_FUNNEL.md` |
| Literature review | Mostly done | Not in the repo; not re-checked here | none in repo (`Research_Gap_Novelty_Documentation.docx` at the top level) |
| Research gap / novelty | Done | Not in the repo as text; not re-checked here | same |
| Research question / analysis design | Designed | Done and frozen | Protocol v1 `85ad69e`, frozen `58e59c0` (D065, D066); tag `protocol-v1` |
| Risk-label recomputation | Required | Done: original label replaced by T1 (exposure-controlled) | D065; Gate 0 audit; `2c9f1c9` (T1 table checked against Gate 1 counts) |
| Decision/event definition | Required | Done | Protocol v1 (D065, D066); `docs/protocol/PROTOCOL_v1.md` |
| Leakage/timing audit | Required | Done as a documented limitation, not as a per-feature table: the window ends at the decision, so duration and gaze counts are tied to skip versus charge | Gate 0 audit; `FINAL_REPORT.md` section 8 (`a54ad46`) |
| Behaviour feature pipeline | Not final | Done: frozen analysis tables | `2c9f1c9`; `results/_tables/analysis_table_t1.csv` |
| Gaze feature pipeline | Not final | Done: AOI-free features used | D025, D034; Protocol v1 |
| Mixed-effects analysis | Not done | Done | `bc14dfd` (engine, D067), `4b821fa`, `54f8702`, `dd95ace`; claim A |
| ML benchmark | Not done | Done, negative | Gate 3: `5af8a79`, `78dacd4`, `cc8fd64`, `e52067d`, `b59b945`; D068 |
| B vs B+G experiment | Not done | Done, negative (H1 not supported) | Gate 2 claim B; `11bcb2c` (D067) |
| EEG incremental-value experiment | Not done | Done, exploratory, not supported | Gate 4: `47220de`, `ab6dfc5`, `eea7c35`, `6aa3a39`; D069; detrended variant D075 |
| SLM benchmark | Not done | Done, negative | Gate 5: scenario set `335b02e` (D070), harness `1827b9c`, scorer `54f6deb`, consistency `72a20f2` (D080), override rerun `a7297de` and `1eeedd9` (D083); deviations D071, D076, D078 |
| FPS measurement | Not done | **Open**: no measured before/after result in the repo | D001 (target reframed to 90 FPS), D004 (protocol only); `FPS_Update_Measurement_TODO.docx` |
| Integrated AI risk-warning system | Not done | Not built (scaffold only); not claimed | D053, D056; Gate 0 audit |
| New data collection | Not started | Not started; design recommendations written | `SUPERVISOR_BRIEF.md` (D085); `dde934b` (protocol doc, D053) |
| Automation-bias experiment | Future | Future | D017, D018 |
| Final manuscript | Not done | **Open**: outline and generated report only | `d62b6a2` (D081), `94344e0` and `a54ad46` (D082, D083) |

## B. Items in the "completed work" section (section 4)

| Old report claim | Current state | Evidence |
|---|---|---|
| About 140 participant sessions with behaviour and gaze | Consistent; the primary analysis set is a subset | Gate 0 audit; `FINAL_REPORT.md` section 1 |
| 76 Muse recordings decoded, 67 verified | Recordings and 67 are in D013 and D019. The pipeline's matched set is smaller; the stages between are tabulated in `EEG_COHORT_FUNNEL.md` | D013, D019, D034, D069 |
| Decoder fixed for the malformed OPTICS packet | Done | D013, D014 |
| Historical AOI route should not be forced | Confirmed: the video-based AOI route is closed for existing data | D026, D030, D059 to D062 |
| Same attack label under two names; risky rate 19% to 34.7% | Done; the later redefinition made the label itself moot for the main analysis | D045; Gate 0 audit |
| 34.7% must not be converted to a participant count | Followed: the primary analysis is decision-level with participant grouping | Protocol v1; Gate 2 |
| AI assistant is image + RAG, not gaze/EEG driven | Confirmed | Gate 0 audit finding 5; D006, D017 |
| RAG cross-session contamination (about 904 documents), fixed for new sessions | Done; affected sessions documented; S3 sensitivity run excludes them | D018, D053 (`75c2017`); Gate 2 sensitivity S3 |
| FPS target 90, candidate levers, no measured result | Same state: **open** | D001, D004 |

## C. Remaining-work steps in the old report (section 11)

| Step | State | Evidence |
|---|---|---|
| 1 Freeze decision definition | Done | D065, D066 |
| 2 Recompute labels | Done | D065 |
| 3 Leakage and timing audit | Done as a documented limitation (see above) | Gate 0 audit |
| 4 Clean behaviour + gaze dataset | Done | `2c9f1c9` |
| 5 Primary B vs B+G | Done, negative | `11bcb2c` |
| 6 Mixed-effects | Done | `dd95ace` |
| 7 EEG on matched subset | Done, exploratory | D069 |
| 8 SLM benchmark | Done | D080, D083 |
| 9 FPS measurements | **Open** | none |
| 10 Error analysis, calibration, robustness | Done (descriptive, reduced Gate 6) | `a6e91c6` (D072), `4360610` (D073 to D075) |
| 11 Manuscript and reproducibility package | Partial: registry, generated report, `docs/REPRODUCE.md`, supervisor brief done; results chapter and manuscript open | D082, D085 |

## D. Statements in the old report that are now wrong or need a caveat

- "Actual scientific analysis 20 to 30%", "ML prediction experiments 10 to 20%", "AI/SLM evaluation 10 to 20%": superseded. The analyses in the protocol have been run.
- "Primary metric AUROC, PR-AUC depending on class distribution": the protocol fixes AUROC as primary and lists PR-AUC, balanced accuracy, Brier score and calibration as secondary (`PROTOCOL_v1.md`).
- "We have verified that behaviour and gaze are the strongest existing dataset": the results do not show that gaze adds predictive value on the redefined target.
- "Eye tracking is the stronger primary physiological modality": not supported by the results (H1 not supported).
- The reproducibility claim in section 11, step 11 is only partly met: 31 lines in 13 files still hold machine-specific paths (`HARDCODED_PATHS.md`).

## E. Critical review

- **What changed:** one new document; the old report and everything else untouched.
- **What could still be wrong:** the literature review and novelty rows are marked "not re-checked" because their content is not in the repo; "leakage audit: done" rests on the Gate 0 audit and the protocol, not on a per-feature timing table I verified here.
- **Not done:** the FPS measurement, the manuscript, the EEG cohort question (next step), the supervisor decision on the participant-code and session-folder linkage.
