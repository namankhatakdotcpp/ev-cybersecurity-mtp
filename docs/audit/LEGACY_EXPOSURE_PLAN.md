# Legacy exposure plan (plan only; nothing in this document has been executed)

Date: 2026-10-29. Status: awaiting the user's decision and the supervisor's view on the consent terms.

## What is still in the tracked tree

Session folder names (they embed the session's local date and time and the participant code) remain in four tracked places. They were public on `origin/main` before the cleanup of D077; the cleanup removed only the unpushed additions.

| File | What it holds | Count |
|---|---|---|
| `backend/pipeline/feature_table.csv` | `participant_id` and `session_dir` on every row, so participant code is linked to session folder (date and time) | 1,123 rows |
| `Decision.md` | session folder names in older entries (prose) | 4 lines |
| `backend/gaze/aoi_free_pilot.py` | a dictionary of three participants to session folder and file names | 3 lines |
| `backend/test_warning_system.py` | one absolute path ending in a session folder name | 1 line |

Related older exposure (not session names, same cause): mentor and supervisor names in `README.md` and older `Decision.md` entries; a Windows account name in `backend/main.py` and `backend/receive_ui.py`.

The session map (`video_gaze_session_map.csv`) is not in pushed history, and the local backups that held it were deleted (D084).

## Who reads `session_dir` (what would break if it changed)

`session_dir` is not only a label. It is a join key, a date source and a path into the raw data:

- Join key: `gate2/build_t1_table.py` (groups and merges on `session_dir`, row-count assertion), `gate2/matched.py`, `gate2/early_window.py`, `gate5/build_scenarios.py` (per-session cap, scenario source map), `mixed_effects_model.py`.
- Date source: `check_time_confound*.py`, `check_cutoff_sensitivity.py`, `check_seed_sensitivity.py` and `final_ablation_table.py` call `parse_date()` with the pattern `session_(\d{8})_(\d{6})_`; `gate2/build_t1_table.py` reads the period from `sd[8:16]`. A pseudonymous key would have to carry the date separately.
- Path into raw data: `gate2/selection_bias.py` opens `<raw>/<session_dir>/demographics.json`; `build_feature_table.py` and `session_qc.py` glob the folders; `cleanup_raw_data_references.py` joins on the name.
- Frozen results: the registry and the Gate 2 to Gate 6 reports record checksums of the committed feature table and the analysis tables built from it. Any change to `feature_table.csv` changes those hashes. It would need a new, versioned file and a note in the registry, not an overwrite.

## Options per file

### Option A: redact in a new forward commit (no history rewrite)

| File | Change | Effect |
|---|---|---|
| `Decision.md` | append-only rule: do not edit old entries. Add an erratum entry only; the old text stays | does not remove anything; Decision.md is not changed under this option |
| `aoi_free_pilot.py` | read the three tuples from `private/pilot_sessions.json` like the video-pilot scripts (`paths.py` already has `EV_PRIVATE_DIR`) | nothing downstream depends on it; the pilot is closed (D060 to D062) |
| `test_warning_system.py` | replace the absolute path by a placeholder | none; it is a manual test |
| `feature_table.csv` | drop `session_dir`, keep `participant_id` | breaks every reader listed above |

The forward commit removes the strings from the latest tree only. Every earlier commit on `origin/main` still contains them.

### Option B: pseudonymous keys held in `private/`

Replace `session_dir` by a key such as `S001`, and keep `private/session_key_map.csv` (key, folder name, date, time). Required changes:

1. a helper in `backend/pipeline/paths.py` that loads the map;
2. `build_feature_table.py` writes the key; the date columns (`session_date`, period) are either stored as a coarse field (week or period) or looked up from the private map;
3. every reader above switches from `parse_date(session_dir)` and `sd[8:16]` to the stored field;
4. `selection_bias.py` and `cleanup_raw_data_references.py` resolve key to folder through the private map;
5. regenerate the analysis tables and verify that every registry result is reproduced to the recorded checksums apart from the renamed key column.

Cost: a new versioned feature table and a large re-verification; participant codes would still be present unless they are pseudonymised too. Risk: a silent mis-join would change results, so the acceptance test is "every Gate 2 to Gate 6 headline number identical after the change". Do not start without the user's approval.

### Option C: leave as is, repository private

No code change. Exposure is limited to the people with access to the repository. The cheapest control, and the one already taken (the user reports the repository was set to private on 2026-10-29).

## What none of this achieves

None of the options removes copies that already exist in forks, clones, caches or search indexes made while the repository was public. Option A and B change only the current tree; the old commits keep the strings. Removing them from history would need a rewrite of already-pushed `main` with a force-push, which is outside the agreed rules and still would not recall existing copies.

## Recommendation

1. Keep the repository private (done, per the user).
2. Obtain the supervisor's decision on whether linking participant codes to session folder names (date and time) is acceptable under the consent terms, and for how long the repository may be shared.
3. Only if the answer is "not acceptable": do Option A for the two scripts first (low risk), then plan Option B as a separate, approved task with the identical-results acceptance test. Do not touch `feature_table.csv` or any pipeline input before that.
