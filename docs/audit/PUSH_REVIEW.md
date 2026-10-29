# Pre-push safety review

Read-only. Nothing was changed, rewritten or pushed. Scope: the 48 commits on `main` that are not on `origin/main` (98 files: 94 added, 4 modified), checked against `https://github.com/namankhatakdotcpp/ev-cybersecurity-mtp.git`. You said the repo is public; I could not verify that (`gh` is not installed here). I also cannot see your consent form or IRB terms, so "may this be public" below is a judgement for you, not a finding. All 48 commits carry the GitHub no-reply author address (no personal email); no commit message names a mentor or participant.

Method: every file in the unpushed diff was read at `HEAD` and pattern-scanned for session folder names, participant codes, timestamps, demographic variable names, mentor/lab names, absolute paths, e-mail addresses and secret-like strings. Hits were then read in context. Untracked outputs under `results/_slm/` and `results/_tables/` are gitignored and are not part of the push.

## 1. Must fix before pushing

| # | Item | What it contains | Risk | Recommendation |
|---|---|---|---|---|
| 1 | `backend/pipeline/video_gaze_session_map.csv` (added in `6e61b8d`, 169 rows) | One row per participant: participant code, session folder name (which embeds the session's local date and time), gaze-recording epoch start and end, first-frame UTC time, offset against the video filename | Highest. It is a participant-level table linking codes, session folders and exact timestamps, which is what allows a recording to be tied to a person | **Remove from the commit and keep it private.** Move it behind an ignored path (for example `private/` plus a `.gitignore` entry); keep `build_video_gaze_map.py` so the file can be regenerated locally. Because the file is already in a local commit, a later `git rm` is not enough: the content stays in the pushed history, so the commit has to be rewritten (see section 5). |
| 2 | Hardcoded lab-folder root in 7 scripts: `backend/pipeline/build_video_gaze_map.py` (1), `video_pilot/p1_gaze_video_alignment.py` (3), `p3_cursor_vs_gaze.py`, `p4_click_window_and_vergence.py`, `p5_panel_localisation_hit_rate.py`, `q1_click_events.py` (1 each), `q2_pinhole_gaze_forward.py` (3) | `<drive>:\<lab folder name>\MTP\...` (names both students, the mentor and the supervisor in the folder name) | The folder name publishes who is under whom; it also breaks reproducibility | **Replace with a configurable root** (section 4). Rewrite the unpushed commits so the old string is not in the pushed history either. |
| 3 | Same string in generated provenance: `results/g3_grid_{ridge,rf,hgb}_*/summary.json`, `g3_secondary_S1_*/summary.json`, `g3_secondary_S2_*/summary.json` (one `config` path each) and 5 rows of `results/registry.csv` | Absolute path to `configs/gate3_grid.yaml` | Same as 2 | **Anonymise**: replace the prefix with a repo-relative `configs/gate3_grid.yaml`. This is a metadata-only edit; none of the hashes in the registry (dataset, feature table, protocol) cover these fields. Fix the writer so new rows store relative paths (`gate2/benchmark.py`, `registry.py` callers pass `cfg["g3"]["_path"]`). |
| 4 | Participant-code and session-folder strings in the pilot scripts: `video_pilot/p3_*.py`, `p4_*.py`, `p5_*.py`, `q1_*.py`, `q2_*.py` | Dictionaries such as `{"021": ("session_<date>_<time>_<code>", ...), "041": (...), "100": (...)}`, video filenames `varjo_capture_<timestamp>.mp4`, per-session offsets | Three participants' session folder names and exact video capture times | **Anonymise**: read the three (code, session, offset) tuples from a local, ignored `private/pilot_sessions.json`; ship an example file with placeholder values. |

## 2. Review and decide

| # | Item | What it contains | Recommendation |
|---|---|---|---|
| 5 | `Decision.md`, 485 added lines | Checked on the added lines only: no session folder names, no `/Users/...` paths, no mentor or student names. It does contain participant study codes in prose (021, 041, 100 in the video-pilot entries; 001/002 in one cross-reference), one video capture filename with a timestamp, and the Varjo folder inventory (158 mp4s, 169 CSVs, capture date range 2026-03-30 to 2026-08-03) | **Keep** the participant codes (they are study codes, and the earlier public entries already use them). **Anonymise** the one capture filename. Decide whether the capture date range matters under your consent terms. The older entries that do contain session names and Mac paths are already public (section 3). |
| 6 | `docs/audit/GATE0_audit.md` | One session folder name (with a duplicated id suffix and a trailing note), participant counts, `/Users/<user>/` path counts | **Anonymise** the folder name and paths, keep the counts. |
| 7 | `docs/analysis/GATE4_report.md`, `results/selection_bias_gate4.md`, `results/g4_selection_bias_*/summary.json`, `configs/gate4_eeg.yaml`, `results/registry.csv` | Aggregate demographics only (matched vs other participants: mean age, percentage male, largest education, specialisation and experience category, effect sizes). No individual rows. Group sizes are 49 and 63 | **Keep**, subject to your consent terms. Group-level shares from groups of that size are not individual data; if the consent restricts publishing demographics at all, drop the participant-level table (it is the only place they appear). |
| 8 | Mentor or supervisor names in text | None in the unpushed lines. `origin/main` already has two lines in `Decision.md` naming the student authors, the supervisor and the mentor (the MidSem report entry) | Your call: keep as acknowledgement or anonymise. It is outside this push (see section 3). |

## 3. Already on `origin/main` (not part of this push)

Listed so you can decide if the problem is wider than the push:
- `backend/pipeline/feature_table.csv`: one row per station visit with participant code, session folder name, decision, kiosk and charge amounts, window length and gaze/EEG summaries. This already links participant codes to session folders, so the exposure in item 1 is partly present already.
- `Decision.md` earlier entries (D001 to D063): participant codes, session names, `/Users/<user>/...` paths, the supervisor and mentor names (2 lines), and `EV Charging VR Research Audit*.pdf`, `FPS_Update_Measurement_TODO.docx`, `Research_Gap_Novelty_Documentation.docx` and `backend/pipeline/model/risk_model.joblib` are tracked.
- `backend/main.py` and `backend/receive_ui.py` contain `C:\Users\<user>\Desktop\BeamNG\...` (a Windows account name; the real one is in the code).
Removing these from the public repo would need a force-push and cannot undo copies or caches. I did not touch them.

## 4. Proposed configurable root

The Gate 2 configuration already has a pattern: repo-relative paths with environment overrides (`EV_RAW_DATA_DIR`, `EV_FEATURE_TABLE`, `EV_RESULTS_DIR`, `EV_SCREENSHOT_ANALYSIS`). Extend it to the 7 scripts:
- `EV_PROJECT_ROOT`: defaults to the repository root derived from `__file__` (so a fresh clone works without any setting).
- `EV_VARJO_DIR`: defaults to `<root>/Varjo` (already gitignored).
- `EV_PRIVATE_DIR`: defaults to `<root>/private` (gitignored); holds `video_gaze_session_map.csv` and `pilot_sessions.json`.
A shared helper (for example `backend/pipeline/paths.py`) returns these three paths; the scripts import it instead of embedding strings. Add a test that fails if any tracked file contains the lab-folder name, `/Users/`, `C:\Users\` or a `session_2026` pattern. Registry rows should store config paths relative to the root.

## 5. Plan (not executed)

1. Make a backup first: `git branch backup/pre-push-20261029` (so nothing is lost).
2. Fix on top of `HEAD` in a normal commit: add `paths.py`, change the 7 scripts, `.gitignore` `private/`, make the registry write relative paths, add the guard test, anonymise items 4 to 6 (item 5 only for the one capture filename).
3. Because the pushed history would otherwise still contain the old content, rewrite only the 48 unpushed commits (`origin/main..HEAD`, never published): `git-filter-repo` is not installed here, so use `git filter-branch` over that range with an index filter that drops `video_gaze_session_map.csv` and a tree filter that substitutes the lab-folder string in the scripts, the 5 summary files and `registry.csv`. This changes commit hashes; the registry's `git_commit` fields refer to the old hashes. They would need a mapping note in the report, because the Gate 3 to Gate 6 runs record the commits they ran at.
4. Verify on the rewritten range: `git grep` for the four patterns over every commit, `git diff` against the pre-rewrite tree to confirm only the intended lines changed, run the test suite.
5. Only then push, after your explicit go-ahead.

Cheaper alternative: skip the rewrite and instead squash nothing; open a fresh public repo from the cleaned tree (single "initial import" commit) and keep this local history private. That loses the 48-commit history on the public side but avoids the hash problem.

## Critical review

- **What we found.** One high-risk file (the session map), one systematic string (lab folder name) in 7 scripts plus 6 generated files, three participants' session folders and capture times in the pilot scripts, and lighter identifiers in `Decision.md` and the Gate 0 report. No secrets, no e-mail addresses, no raw data, no row-level demographics in the unpushed commits.
- **What we cannot judge.** Whether your consent and IRB terms allow session dates, participant codes or aggregate demographics to be public; whether the repo is actually public; what is cached or forked already from earlier pushes.
- **Defensible.** The statement that the unpushed commits contain no raw sensor or participant-level demographic data; the list above is complete for the patterns scanned.
- **Not defensible.** "Safe to push as is", or any claim that removing items from the new commits removes them from the public record (section 3).
- **Do not do next.** Push before steps 2 to 4 of the plan; edit `origin/main` history without a separate explicit decision.
