# Remaining machine-specific paths (inventory and proposed fix; no code changed)

Date: 2026-10-29. Method: `git grep` over tracked `*.py` for home-directory prefixes of the original machines (a macOS home and a Windows home) and for the scratch drive `D:\MTP_scratch`, excluding the guard test and test fixtures. Result: **31 lines in 13 Python files**. The Gate 0 audit counted 25 occurrences in 13 files with a different counting rule (it counted occurrences of one prefix); the 13 files match, and the seven video-pilot scripts and `paths.py` have since been fixed. Treat the two numbers as "same files, different counting", not as 6 new paths.

`<mac-home>` below stands for the macOS home directory of the machine that collected the data; the folder under it is `Documents/MTP`.

## Inventory

| File | Lines | What is hardcoded |
|---|---|---|
| `backend/pipeline/build_feature_table.py` | 29 to 33 | raw data dir, decoded EEG dir, contaminated-sessions JSON, EEG summary CSV, output CSV (all under `<mac-home>/Documents/MTP`) |
| `backend/pipeline/session_qc.py` | 49, 50, 195 | raw data dir, decoded EEG dir, default `--out-csv` |
| `backend/pipeline/mixed_effects_model.py` | 36 | raw data dir |
| `backend/pipeline/calibrate_risk_model.py` | 57, 58 | model and metadata paths |
| `backend/pipeline/train_production_model.py` | 41 | model dir |
| `backend/pipeline/check_cutoff_sensitivity.py` | 112 | output CSV |
| `backend/pipeline/final_ablation_table.py` | 210 | output CSV |
| `backend/Muse/decode_all.py` | 26, 27 | decoded dir, raw data dir |
| `backend/gaze/gaze_pilot.py` | 24, 25, 26 | raw data dir, output dir (line 25 is a dead placeholder overwritten by line 26) |
| `backend/gaze/aoi_free_pilot.py` | 25, 26 | raw data dir, output dir (the session dictionary below them is the separate item in `LEGACY_EXPOSURE_PLAN.md`) |
| `backend/gaze_online.py` | 46 | `sys.path.insert` of the pipeline dir |
| `backend/test_gaze_online.py` | 37, 40 | same `sys.path.insert`, raw data dir |
| `backend/test_warning_system.py` | 144 | a raw-data session path in a manual test |
| `backend/main.py` | 39 | Windows path to the BeamNG install (also carries a Windows account name) |
| `backend/pipeline/video_pilot/p3_*.py`, `p4_*.py`, `p5_*.py`, `q1_*.py`, `q2_*.py` | 1 line each (p3 line 3, p4 line 2, p5 line 5, q1 line 21, q2 line 12) | `D:\MTP_scratch\video_pilot[...]` scratch output directory |

(The video-pilot rows are the 5 remaining lines on the scratch drive: 26 lines elsewhere plus these 5 make 31; they hold outputs, not inputs, and do not affect any registered result. The count of 31 includes them.)

## Proposed fix (through `backend/pipeline/paths.py`)

`paths.py` already exposes `ROOT`, `RAW`, `VARJO` and `PRIVATE`, each overridable by an environment variable. Add, with defaults relative to `ROOT` so a fresh clone works without configuration:

| Constant | Default | Environment variable |
|---|---|---|
| `PIPELINE` | `ROOT/backend/pipeline` | none |
| `EEG_DECODED` | `ROOT/backend/Muse/decoded` | `EV_EEG_DECODED_DIR` |
| `CONTAMINATED_JSON` | `ROOT/backend/rag_contaminated_sessions.json` | none |
| `MODEL_DIR` | `PIPELINE/model` | none |
| `SCRATCH` | `ROOT/scratch` (gitignored) | `EV_SCRATCH_DIR` |
| `BEAMNG_HOME` (main.py only) | read from an environment variable, no default account path | `EV_BEAMNG_HOME` |

Then, in this order (smallest risk first):

1. `build_feature_table.py`: replace lines 29 to 33 by imports from `paths.py`, keeping `OUT_CSV = PIPELINE / "feature_table.csv"`. Behaviour is unchanged on any machine where the old paths resolved to the same files.
2. `session_qc.py`, `mixed_effects_model.py`, `calibrate_risk_model.py`, `train_production_model.py`, `check_cutoff_sensitivity.py`, `final_ablation_table.py`: same substitution.
3. `Muse/decode_all.py`, `gaze/gaze_pilot.py`, `gaze/aoi_free_pilot.py`: import from `paths.py`; delete the dead placeholder line in `gaze_pilot.py`.
4. `gaze_online.py`, `test_gaze_online.py`: replace the hardcoded `sys.path.insert` by a path relative to the file.
5. `test_warning_system.py`: take the session folder from an environment variable or skip the test when it is unset.
6. `main.py`: `BEAMNG_HOME` from an environment variable (this removes the Windows account name from the tracked tree).
7. Video-pilot scripts: output to `paths.SCRATCH / "video_pilot"`.
8. Extend `test_no_private_strings.py` so the home-path check covers every tracked `*.py` instead of only the Gate work paths, and remove the paths it currently exempts as legacy once they are fixed.

## Acceptance test (to run only after approval of the code change)

1. Record the SHA-256 of the committed `backend/pipeline/feature_table.csv`.
2. Set `EV_RAW_DATA_DIR` to this machine's copy of the raw sessions and `EV_EEG_DECODED_DIR` to the decoded EEG, then run `build_feature_table.py` writing to a temporary file.
3. Compare checksums. Equal: the refactor is behaviour-preserving. Different: diff the two tables before touching anything else; a mismatch can come from library versions or file ordering rather than from the paths, and must be explained, not overwritten.

Limit: this needs the raw sessions and decoded EEG. On this machine `backend/raw_data` and `backend/Muse/decoded` are present, so the test can be run; on a clone without them only the static steps 1 to 8 can be verified.
