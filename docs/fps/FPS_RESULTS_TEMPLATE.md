# FPS results (template; every cell is empty on purpose)

Fill this in only from real logs analysed with `python -m backend.fps.analyze_frametimes analyze ...`. Do not enter estimates, remembered values or numbers from another machine. Protocol: `docs/fps/FPS_MEASUREMENT_PROTOCOL.md`.

## Session record

| Item | Value |
|---|---|
| Date and operator | |
| Workstation, GPU, driver version | |
| Varjo Base and runtime version | |
| BeamNG.tech build | |
| Windows version | |
| Headset and refresh setting | |
| Capture tool and version | |
| Original values: Shadows::textureScalar / Shadows::disable / Reflect::refractTexScale / 2D screen view | |
| SHA-256 of the original and of the changed `game-settings-default.cs` | |
| Schedule seed | |
| Warm-up and window used in the analysis (s) | |
| Threshold agreed for "meets the target" (set before looking at the results), and by whom | |

## Run table (one row per run)

| Run id | Condition | Repeat | Frames | Mean FPS | 1% low FPS | 0.1% low FPS | fps_min | p95 ms | p99 ms | p99.9 ms | Over-budget share | Severe-late share | Dropped frames | OpenXR current / target rate (start, middle, end) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | C0 | 1 | | | | | | | | | | | | | |
| | C0 | 2 | | | | | | | | | | | | | |
| | C0 | 3 | | | | | | | | | | | | | |
| | C0 | 4 | | | | | | | | | | | | | |
| | C0 | 5 | | | | | | | | | | | | | |
| | C5 | 1 | | | | | | | | | | | | | |
| | C5 | 2 | | | | | | | | | | | | | |
| | C5 | 3 | | | | | | | | | | | | | |
| | C5 | 4 | | | | | | | | | | | | | |
| | C5 | 5 | | | | | | | | | | | | | |

Optional attribution conditions C1 to C4 use the same columns (one block of five rows each).

## Condition summary (mean, with the range over repeats in brackets; copy from `condition_summary.csv`)

| Condition | Runs | Mean FPS | 1% low FPS | Over-budget share | Severe-late share | Difference to C0 in mean FPS | Difference to C0 in over-budget share |
|---|---|---|---|---|---|---|---|
| C0 baseline | | | | | | not applicable | not applicable |
| C5 all changes | | | | | | | |

## Reading (fill in after the numbers; descriptive wording only)

| Question | Answer |
|---|---|
| Do the run ranges of C0 and C5 overlap on the over-budget share? | |
| Did the OpenXR current rate stay at the target in every C5 repeat? | |
| Does C5 meet the agreed threshold in every repeat? | |
| Anything that limits the comparison (drift, crash, tool problems, changes between runs) | |

## What may be stated

Only what the filled tables show, for this workstation, route, build and headset. Until the tables are filled, no FPS improvement is claimed.
