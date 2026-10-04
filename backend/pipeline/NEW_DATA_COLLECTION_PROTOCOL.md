# New data collection protocol (Objective 3 prep)

One page, built directly from this project's own already-established findings
(D001-D053) - not a generic template. Everything here has a specific reason
cited; nothing is a best-practice default without a project-specific cause.

## Schema (per session)

Minimum files per participant, extending the existing convention
(`backend/raw_data/session_<timestamp>_<pid>/`):

| File | Format | Source | Notes |
|---|---|---|---|
| `<pid>.csv` | Varjo gaze CSV | existing capture app | unchanged - 46-column schema already in use |
| `interactions_<ts>.csv` | existing interaction log | `receive_ui.py` | unchanged - keep `Flowgraph`/`Reached`, `StationGenerated`, charging events exactly as today |
| **`headpose_<ts>.csv`** | **new** | `evHeadPoseLogger.lua` drained by a **not-yet-written** Python consumer | columns: `timestamp_unix_ms, pos_x, pos_y, pos_z, quat_x, quat_y, quat_z, quat_w, marker` (`marker` empty except for the one `calibration_nod` row per session, D031/Task 2) |
| `<pid>_muse.txt` | raw Muse packets | `collect_data.py`/`OpenMuse` (**not** `muse.py`/LSL - D009) | only if EEG is being collected for this session |
| `system_config.json`, `demographics.json`, `consent.json` | existing | unchanged | **also record `incident_mode` explicitly for this session** - D045 found this flag changes `kiosk_attack`'s label vocabulary (`"Cyber Attack"` vs `"System Anomaly"`) for the identical underlying attack mechanic; keep it fixed across a collection batch unless deliberately varying it as a manipulation, and never let the label-merge (`COMPROMISED_LABELS` in `train_baselines.py`) be the only place this is accounted for |
| **kiosk world-position export** | one-time static table or per-session JSON | the real flowgraph scenario file (**still not located in this install** - D021/D027) | required before head-pose data is usable for raycasting; blocks AOI-level analysis even with head-pose logged, not a nice-to-have |

## Synchronization

1. **Head-pose timestamps stay on the backend wall-clock domain**, not a BeamNG Lua clock (D031) - the Python consumer stamps each drained batch with `datetime.now()`, same convention `interactions_*.csv` already uses. This is a **deliberate choice to reuse an already-proven clock relationship** (D020/D026/D045 already compose gaze and interaction timestamps correctly via simple epoch alignment), not a default.
2. **Run the calibration-nod protocol at the start of every session, not just once for the study**: a distinctive, sharp head motion on command (`evHeadPoseLogger.markCalibrationNod()`), logged by both this new head-pose stream and whatever the external gaze-capture application's own motion/event log shows at the same moment. This is how the real cross-process clock offset gets *measured*, not assumed (D031) - skipping it for "just this one session" defeats the entire reason it exists.
3. **Locate the actual gaze-capture application's source before trusting its timestamp semantics at the fixation level.** D031 confirmed it is not in this codebase; its `relative_to_unix_epoch_timestamp` field is internally consistent (anchor-once, not re-sampled per frame - checked directly) but its absolute accuracy against a true wall clock has never been independently verified. Session-level analysis has been fine for 140 sessions; do not assume fixation-level claims are automatically fine too without this check.

## Calibration step (per session, before the driving task starts)

1. Varjo eye-tracking calibration (existing procedure, unchanged).
2. Muse EEG baseline/contact-quality check, if EEG is being collected this session (existing procedure).
3. **New**: the head-pose calibration nod (one sharp, recognizable motion, held 1-2 seconds) - call `evHeadPoseLogger.markCalibrationNod()` and note the wall-clock time the experimenter triggered it, independent of the logged data, as a manual cross-check for the first several sessions until the automated offset-recovery is trusted.
4. Confirm `evHeadPoseLogger.getStatus()` reports `enabled=true` and a non-zero `bufferedSamples` before the participant starts driving - **this extension is UNTESTED** (Task 2) and defaults to disabled; do not assume it is capturing without checking this explicitly on the first session of any new collection day.

## Quality control (run after every session, before the participant leaves if possible)

Run `backend/pipeline/session_qc.py --session <new session dir>` immediately. A `fail` on `gaze` or `events` should prompt an immediate decision (re-run vs. accept-and-flag) while the participant is still available - waiting until after the whole batch is collected to discover a bad session wastes the chance to fix it. `eeg`/`head_pose` showing `not_available` is expected and fine if that modality wasn't being collected this session; `fail` on either (file present but broken) is not.

## What this protocol deliberately does not cover

Scenario/attack-type design (already specified in the mid-sem report's Table 3)
and the automation-bias three-condition wiring (already implemented, D036/D042
- use `override_strength="strong"` as the production setting) are unchanged by
this document; this is the data-plumbing layer underneath those, not a redesign
of either.
