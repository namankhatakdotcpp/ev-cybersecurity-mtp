# FPS measurement protocol (to be run on the lab workstation)

Status: protocol only. **No frame-rate measurement exists in the repository and none is reported here.** This document turns `FPS_Update_Measurement_TODO.docx` and Decision D001 and D004 into a protocol that can be executed and analysed without further decisions. The analysis script is `backend/fps/analyze_frametimes.py`; the results template is `docs/fps/FPS_RESULTS_TEMPLATE.md`.

## 1. Question and target

- **Question.** Is the frame rate in the VR session higher and steadier with the changed graphics settings than with the original ones?
- **Target.** A stable 90 FPS, matching the 90 Hz refresh rate of the Varjo XR-4 (D001). Frame rates above 90 are not a goal. A pass means that few frames take longer than the 90 Hz budget of 11.11 ms, not that the average is high.
- **Not claimed.** Nothing about FPS improvement may be stated before the numbers in section 8 are filled in from real logs. The result applies to this workstation, this build, this route and this headset.

## 2. Conditions

Labelled conditions. The settings file is `settings/game-settings-default.cs` under the BeamNG.tech.v0.38.3.0 install; the file only provides defaults for a new settings profile, so each change needs **Options, Graphics, Reset to Defaults** in the game after the file is edited.

| Label | Shadows::textureScalar | Shadows::disable | Reflect::refractTexScale | 2D screen view (OpenXR debug window) |
|---|---|---|---|---|
| **C0 baseline** | original value (record it) | original value (record it) | 1.0 | original value (record it) |
| C1 | 0.5 | original | 1.0 | original |
| C2 | original | 1 | 1.0 | original |
| C3 | original | original | 0.5 | original |
| C4 | original | original | 1.0 | Empty (fastest) |
| **C5 all changes** | 0.5 | 1 | 0.5 | Empty (fastest) |

- **Primary comparison: C0 against C5.** This is the before/after of the TODO document and the only comparison needed to answer the question above.
- **Attribution runs: C1 to C4 are optional**, exploratory, and only worth doing if C5 differs from C0. Note that with shadows disabled (C2, C5) the shadow texture scalar has no effect, so C1 is interpretable only against a baseline in which shadows are enabled; do not infer an individual share of the C0 to C5 difference by subtraction.
- In every condition: "Enable debug mode" in the OpenXR debug window is **off**; the headset is worn or mounted and active exactly as in the data-collection sessions (D004); no other program is running except the capture tool.
- Before the first run, record the original values of the settings above and the SHA-256 of the original `game-settings-default.cs` and of the changed file. Keep a backup copy of the original file (`.bak`) so C0 can be restored.

## 3. Fixed scenario and timing

1. Start the simulation, load the scenario, spawn.
2. Drive to station 1 along the same route every time and stop at the kiosk. Do not drive during capture (stationary capture removes physics noise, as in the TODO document).
3. **Settle for 20 s** at the kiosk (shaders and streaming finish).
4. **Capture for 120 s.** The TODO document suggests about 30 s; 120 s is used here because the 0.1% low needs a few thousand frames (at 90 FPS, 30 s gives about 2,700 frames and the 0.1% low rests on about 3 of them; 120 s gives about 10,800). If only 30 s is feasible, report the 0.1% low as unreliable.
5. The analysis script discards the first 10 s of the capture window (`--warmup-s 10`) and analyses the remaining time.

## 4. Repeats and order

- **Repeats: 5 per condition** (the TODO document asks for 3; 3 is the minimum and gives only a range, not an interval). The primary comparison therefore needs 10 runs.
- **Order: randomised in blocks**, so that a slow drift (GPU temperature, driver, background tasks) does not line up with one condition. Generate the order with `python -m backend.fps.analyze_frametimes schedule --conditions C0,C5 --repeats 5 --seed 1`; write the seed in the run sheet. Restart the simulation between runs of different conditions, because the settings need a reset.
- Let the machine cool or idle for 2 minutes between runs. Close the capture file and start a fresh one per run.

## 5. What to log

**Per frame (required).** One CSV per run with the time between consecutive presented frames in milliseconds.

- Preferred tool: **PresentMon** (or CapFrameX, which wraps it) capturing the BeamNG process for the capture window. Its CSV has one row per presented frame; the script reads the frame-time column (`msBetweenPresents`, `FrameTime` or `frametime_ms`, case-insensitive) and, if present, a `Dropped` column.
- If the Varjo runtime reports compositor frame statistics (frames submitted late or missed), save that log or a screenshot too; it is the closest measure of what the headset showed, and PresentMon measures what the application presented.
- The TODO document names BeamNG's own profiler (`perfProfiler.lua`, CameraProfiler, `.perfRecording.json`) but notes that the recorder was not found in the install. If a `.perfRecording.json` can be produced, keep it as a secondary record; do not mix its numbers with PresentMon numbers in one table.
- Fallback when no per-frame log is possible: MSI Afterburner or the Windows Game Bar overlay with average and minimum FPS written down. Such runs can fill `fps_average` and `fps_min` only and **cannot** support percentile or budget metrics; mark them as `overlay-only` in the run sheet.

**Per run (run sheet, by hand).** Run id, condition, repeat number, date and time, schedule seed, capture file name, the OpenXR `currentRefreshRate` and `targetRefreshRate` read at the start, middle and end of capture (a current rate at half of the target means the headset is reprojecting), anything unusual (notifications, a crash, a stutter you noticed).

**Once per session.** Workstation model, GPU and driver version, Varjo Base and runtime version, BeamNG.tech build, Windows version, headset model and refresh setting, capture tool and version, hashes of the two settings files, who ran it.

## 6. Run manifest

The script reads `runs.csv` with one row per run and the columns `run_id,condition,repeat,file`, where `file` is the per-frame CSV path relative to the manifest. Optional column: `kind` (`frametime` by default, or `overlay-only` rows are skipped for percentile metrics). Real measurement files go in `docs/fps/data/` (not created; do not commit raw data unless the supervisor agrees).

## 7. Metrics (all computed by the script from the per-frame times)

Frame time is the time between consecutive presented frames; the budget is 1000/90 = 11.11 ms.

| Metric | Definition |
|---|---|
| mean FPS | number of frames divided by the analysed duration (the sum of frame times) |
| 1% low FPS | 1000 divided by the mean frame time of the slowest 1% of frames |
| 0.1% low FPS | the same for the slowest 0.1% of frames (needs at least 1,000 frames) |
| frame-time percentiles | 50th, 95th, 99th and 99.9th percentile of frame time in ms |
| over-budget share | share of frames with frame time above 11.11 ms |
| severe-late share | share of frames above twice the budget (22.22 ms), i.e. at least one refresh missed |
| dropped frames | count of rows flagged in a `Dropped` column if the tool provides one, otherwise not reported |
| fps_min (TODO table) | 1000 divided by the largest frame time; shown for continuity with the TODO table, but a single frame can set it, so the percentile metrics are the ones to read |

Summaries per condition are the mean, minimum and maximum of each run-level metric over the repeats, and the difference between the condition mean and the C0 mean. With 3 to 5 repeats the numbers are descriptive: report the run range, do not report p-values or confidence intervals, and say that the result is for one workstation.

## 8. Reading the result

- A condition **meets the target** only if the over-budget share and the severe-late share are small in every repeat and the OpenXR current rate stays at the target rate; the mean FPS alone is not sufficient. "Small" is not defined here on purpose: decide the threshold with the supervisor before looking at the numbers, and write it in the results file.
- If C5 is not better than C0 in the run ranges, report that. Do not select repeats.
- Any change of the route, the scene, the headset, the driver or the build between runs invalidates the comparison; start the affected conditions again.

## 9. Checklist (from the TODO document, extended)

- [ ] Original `game-settings-default.cs` backed up, hashes recorded
- [ ] Original values of the three file settings and the 2D view recorded
- [ ] Schedule generated, seed recorded
- [ ] For each run: settings applied, **Reset to Defaults** done, debug mode off, 2D view set as the condition requires
- [ ] 20 s settle, 120 s capture, per-frame log saved, refresh rates noted three times
- [ ] Manifest `runs.csv` written; script run; results copied into the template
- [ ] Threshold for "meets the target" agreed before looking at results

## 10. Critical review

- **What could be wrong:** the PresentMon column names depend on the tool version (the script accepts the common ones and fails loudly otherwise); presented-frame times are not the same as what the Varjo compositor showed; 5 repeats on one machine say little about other machines; the 120 s window and the 10 s warm-up are my choices, not the supervisor's.
- **Not done:** no measurement, no choice of the "small" threshold, no check that PresentMon can attach to the BeamNG process in VR mode on the lab PC, no decision on where raw logs may be stored.
