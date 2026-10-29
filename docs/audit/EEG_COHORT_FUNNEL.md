# EEG cohort funnel (read-only)

Date: 2026-10-29. No inclusion rule, matched-set definition or committed result was changed, and S6 was not re-run. Every count below is printed by `python -m backend.pipeline.gate2.eeg_funnel`, which reads `decode_summary_resynced.csv`, `feature_table.csv` and the Gate 2/4 tables, and repeats (does not redefine) the screening rule that `build_feature_table.load_eeg_qualified` applies (D019, D034).

## 1. Funnel

| Stage | Participants |
|---|---|
| Participants with a session folder in raw data | 133 |
| Participants with at least one decision row in the feature table | 126 |
| Participants in the primary set (T1 rows with gaze) | 112 |
| EEG recordings found (rows of the decode summary) | 76 |
| Decoded | 76 |
| Session timestamps verified (`best_sync` = `overlap_confirmed`) | 69 |
| Quality-screened (verified, samples > 0, per-channel flatline < 0.15, gap share < 0.5) | **67** |
| ... with any decision row in the feature table | 65 |
| ... with at least one decision window that has EEG features | 58 |
| ... with a primary-set (T1) row | 52 |
| **Matched set (primary rows that have EEG features)** | **49** (150 rows, 70 events) |

The first four rows are a separate chain (all participants) and are not nested in the EEG chain; "recordings found" counts rows in the decode summary, not the raw packet files, which D008 and D012 counted as 76.

## 2. Reconciling "67" and "49"

- The old report's "67 verified/session-linked" is the **quality-screened** count (stage 7). The number with verified session timestamps is 69; two of them (065, 084) fail the quality screen (065: highest per-channel flatline fraction 0.168 against the 0.15 limit; 084: about 67% of the recording span is gap, above the 0.5 limit). Arithmetic: 76 decoded - 7 unverified = 69 verified; 69 - 2 screen failures = 67.
- The 18 screened participants that are not in the matched set stop at these places:

| Where each stops | Participants |
|---|---|
| no decision row in the feature table (040, 071) | 2 |
| decision rows exist but no window with EEG features | 7 |
| windows with EEG exist but no primary-set (T1) row | 6 |
| primary rows exist but none of them has EEG | 3 |

- The main mechanism is timing, not screening. Among decision windows of the 67 screened participants, **324 have EEG features, 235 start after the participant's EEG recording ended, 5 fall inside the recording but have no usable EEG, and 0 start before it**. Many recordings end before the participant's session does. This is the selection issue already reported in the Gate 4 selection-bias report (earlier stations are over-represented in the matched set).
- Nobody outside the screened 67 is in the matched set.

## 3. Participants 012, 053, 054, 058 (and the other three decoded-but-unverified files)

All seven decoded files that fail verification are excluded at the same stage (timestamps not confirmed). For the four the old report names:

| Participant | What the data show | Feature rows / primary rows / matched rows |
|---|---|---|
| 012 | A 15 s recording that ends about 3 minutes before the logged start of the only session folder (331 log lines). Consistent with a short pre-session headset check, as D019 concluded. | 7 / 4 / 0 |
| 053 | A 199 s recording that ends about 11 minutes before the logged session start (47 log lines). Same reading. | 1 / 0 / 0 |
| 054 | A 117 s recording that ends about 1.5 minutes before the logged session start (226 log lines). Same reading. | 5 / 2 / 0 |
| 058 | A 610 s recording at about 16:43 to 16:53 on its day, while the only session folder has a 2-line log whose single event is at about 13:03, roughly 3.7 hours earlier. The recording may belong to a played session whose log is missing or stored under another folder; the data cannot settle it. | 0 / 0 / 0 |
| 013 (not named in the old report) | zero decoded EEG samples, so nothing to compare | 9 / 3 / 0 |
| 059, 072 (not named) | the session has no readable interactions file, so no comparison is possible; 072 also has a recording that is about 88% gap | 0 / 0 / 0 |

Clock comparisons use the decode summary's estimated local times (`*_ist_est`), so "consistent with" is the strongest honest wording. 012, 053 and 054 contribute behaviour and gaze rows to the primary analysis as normal participants; they only lack EEG. 058 contributes no rows to any analysis.

## 4. What would be a deviation (not applied)

- **058:** if the lab finds the missing session log for the 16:43 recording, the participant could be re-checked under the existing rule. Asking the person who ran the session is the only route; the rule does not change.
- **Window rule:** the dominant loss (235 of 564 windows) is that EEG recordings end before the session. Extending coverage would need the EEG to exist, not a different rule. No relaxation is proposed.
- Nothing in this funnel contradicts the committed matched set (150 rows, 49 participants, 70 events); the Gate 4 assertion on those counts still holds.

## 5. Critical review

- **What changed:** this document and `backend/pipeline/gate2/eeg_funnel.py` (read-only, prints Markdown).
- **What could still be wrong:** the "recordings found = 76" figure is the decode summary, not an independent count of raw files; participant-to-recording identity relies on the file naming, as in D013; the "ended before the session" reading for 012, 053 and 054 depends on estimated clock offsets; 058 cannot be resolved from the repository. The script has no unit test because it reads the real data; its output depends on the raw files being present on this machine.
- **Not done:** no check with the lab about 058; no change to any rule; S6 not re-run; the old status report is not corrected yet (that is step 2).
