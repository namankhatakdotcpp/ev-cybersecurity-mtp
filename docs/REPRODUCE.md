# Reproducing the results

Scope: regenerating the registry-based tables and reports from the committed code, configs and registry. Everything here was checked on the machine that produced the results (Windows 11, Python 3.10.0rc2 in `venv_win`). Nothing below has been run on a clean clone.

## Environment

Python 3.10.0rc2. Packages in the working environment: numpy 2.2.6, pandas 2.3.3, scipy 1.15.3, scikit-learn 1.7.2, statsmodels 0.15.0, joblib 1.6.0, PyYAML 6.0.3, pytest 8.4.2. There is no `requirements.txt` in the repository; the list above was read from the environment, not from a lock file. The SLM track also needs a local Ollama server with the five models pulled (`mistral:7b-instruct`, `llama3.1:8b`, `phi3:3.8b`, `gemma2:9b`, `qwen2.5:7b`); the exact Ollama version and model digests are written to a provenance file for each run in `results/_slm/`.

Run every command from the repository root (`MTP/`).

## Environment variables

All optional; the default is relative to the repository root.

| Variable | Default | Used for |
|---|---|---|
| `EV_PROJECT_ROOT` | derived from `backend/pipeline/paths.py` | repository root |
| `EV_RAW_DATA_DIR` | `backend/raw_data` | participant session folders (not in the repository) |
| `EV_VARJO_DIR` | `Varjo` (gitignored) | Varjo gaze CSVs and mp4 files (video pilot only) |
| `EV_PRIVATE_DIR` | `private` (gitignored) | participant-linked tables: session map, pilot session list; layout example in `private_example/` |
| `EV_FEATURE_TABLE`, `EV_RESULTS_DIR` | `backend/pipeline/feature_table.csv`, `results` | Gate 2 to Gate 4 configs (`configs/gate2_h1.yaml` and others) |

## What can be rebuilt from what

| Needs | Can rebuild |
|---|---|
| committed files only | every generated table and the final report from `results/registry.csv` and the run folders; the unit and guard tests |
| committed `feature_table.csv` | Gate 2 to Gate 4 and Gate 6 analyses (new run folders and registry rows) |
| raw sessions and decoded EEG | `feature_table.csv` itself (`build_feature_table.py`); see the limits below |
| a local Ollama server and GPU | the Gate 5 language-model replies |
| `private/` and the Varjo data | the video pilot only (closed; not used for any registered result) |

## Order of commands

Existing run folders are never overwritten: each run writes a new timestamped folder and a registry row. Re-running an analysis therefore adds rows. To reproduce only the documents, run steps 7 and 8.

1. Tests: `python -m pytest backend/pipeline -q` (47 tests; the older manual scripts directly under `backend/` are not pytest tests and fail at collection)
2. Gate 2 (H1): `python -m backend.pipeline.gate2.run_h1 claim_a`, then `claim_b`
3. Gate 3: `python -m backend.pipeline.gate2.run_gate3 grid`, then `secondary`; table: `python -m backend.pipeline.gate2.master_table`
4. Gate 4: `python -m backend.pipeline.gate2.run_gate4 selection`, then `s6`
5. Gate 5. The scenario set is committed under `scenarios/slm_v1/`; to rebuild it: `python -m backend.pipeline.gate5.build_scenarios` and `python -m backend.pipeline.gate5.scenario_report`. Replies: `python -m backend.pipeline.gate5.run_slm pilot|accuracy|consistency [models] [workers]`; override condition: `python -m backend.pipeline.gate5.run_slm malicious all 1 malicious_rerun`. Scoring: `python -m backend.pipeline.gate5.master_table5 register`, then `table`; override scoring (Amendment A2): `python -m backend.pipeline.gate5.malicious register`, then `table`. The raw reply logs are gitignored (`results/_slm/`), so scoring needs them locally.
6. Gate 6: `python -m backend.pipeline.gate6.descriptive_b0`; `python -m backend.pipeline.gate6.extra s5`, then `grid`, then `eeg`
7. Final report: `python -m backend.pipeline.gate7.build_final_report` writes `docs/report/FINAL_REPORT.md` from the registry only. Its test uses a frozen registry fixture: `python -m pytest backend/pipeline/gate7 -q`.
8. The reports in `docs/analysis/GATE*_report.md` and `docs/report/MTP_results_outline.md` are written text built from the registry and the generated tables; there is no generator for them.
9. The Word progress report (`docs/report/MTP_progress_report_2026-10-29.docx`) was written once and is kept local and uncommitted. The repository has no script that regenerates it.

## Known limits

- **Hashes.** The registry and `configs/gate2_h1.yaml` record pre-rewrite commit hashes. `docs/audit/HASH_MAP.md` maps them to the pushed hashes; the protocol file itself is byte-identical (blob `552107de...`).
- **Raw data.** `backend/pipeline/feature_table.csv` was built from raw sessions that are not in the repository, and the selection-bias report also reads `demographics.json` from them. Without the raw data you can re-run the analyses on the committed feature table but cannot rebuild the table.
- **Feature table.** `python -m backend.pipeline.build_feature_table` (with `EV_FEATURE_TABLE` pointing at a scratch file) reproduces the committed `backend/pipeline/feature_table.csv` in every value; the only differences are 66 cells where the committed file has `-0.0` and a rebuild writes `0.0` (D089, `docs/audit/FEATURE_TABLE_REBUILD_CHECK.md`). Before D089 the script gave different EEG columns under pandas 2.x.
- **Hardcoded paths.** `build_feature_table.py` is now configurable; 12 other Python files still hold machine-specific paths (26 lines; full list and proposed fix in `docs/audit/HARDCODED_PATHS.md`). Until that is fixed, those scripts only run with the original machine layout or after editing the paths.
- **Session folder names.** Older public files still contain session folder names; see `docs/audit/LEGACY_EXPOSURE_PLAN.md`.
- **Language-model runs** depend on GPU state, the Ollama version and the order of concurrent workers; replies are not bit-reproducible. The scored replies are the registered result, and latency from concurrent passes is not reported.
- **Numerical differences.** Seeds are fixed in the configs; results were produced with the package versions above and may differ in the last digits with other versions.
