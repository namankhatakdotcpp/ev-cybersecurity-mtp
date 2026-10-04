# Feature table schema (Phase 1, D034+)

One row per (participant, station/scenario-event). Produced by
`build_feature_table.py` into `feature_table.csv`. Consolidates D001-D033's
findings into one real, machine-usable schema - not a placeholder.

## Availability per participant, stated explicitly (not assumed)

| Modality | Available for | Missingness signal |
|---|---|---|
| Behavioural / event logs | 132/140 raw_data participants (138 session folders minus 6 duplicate-folder collisions resolved to one canonical session each, per D019 - see `build_feature_table.py`'s `discover_sessions()`) | A participant absent from the table entirely |
| Gaze (AOI-free cluster features) | Participants with a readable gaze CSV in their canonical session folder - 3 confirmed absent (069, 082, 132) as of this pipeline run | `gaze_missing = True`, all `gaze_*` columns empty |
| EEG (band power) | Exactly the 67 participants D019 qualified (session-overlap confirmed via `best_sync`, flatline fraction &lt;15%, no dominant dropout gap) - recomputed directly from `backend/Muse/decoded/decode_summary_resynced.csv` in this pipeline, matching D019's number exactly | `eeg_missing = True`, all `eeg_*` columns empty |
| AI-assistant use / RAG contamination | All 140 sessions have a `rag_contaminated` flag; `True` only for the 38 sessions in D029's exclusion list | N/A - this is itself a boolean feature, not a missingness case |

**Never zero-filled, never imputed.** A model consuming this table must handle
`*_missing` flags explicitly (e.g. train gaze-only and EEG-only models on their own
non-missing subsets, per Phase 4's ablation requirement) rather than silently
treating a missing modality as a zero signal.

## Columns

### Identity / windowing
| Column | Type | Source |
|---|---|---|
| `participant_id` | str | session folder name |
| `session_dir` | str | session folder name (unique; use this, not `participant_id`, to key against D029's exclusion list) |
| `trial` | int | station number, from the `Flowgraph Reached` event |
| `window_duration_s` | float | decision-window length (station reached -> charging/disabled_charging/driving) |

### Behavioural (game logs only - never gaze/EEG, standing rule unchanged)
| Column | Type | Source |
|---|---|---|
| `decision` | `"charge"` \| `"skip"` | presence/absence of a `charging`/`disabled_charging` event before the next `driving` event |
| `kiosk_used` | int or empty | from the charging event payload; empty when `decision=="skip"` |
| `kiosk_attack` | `"Safe"` \| `"Cyber Attack"` or empty | from the charging event payload; empty when skipped (the station layout logs all 3 kiosks' attack status separately, but this table only labels the kiosk actually chosen, per the "labels from observable outcomes only" rule) |
| `charge_amount` | float or empty | from the charging event payload |
| `points_lost` | float or empty | points_before (from the `station` page event) minus points_after (from the charging event) |
| `ai_help_used` | bool | whether an `assistant_chat` page event occurred inside this station's window |
| `rag_contaminated` | bool | session membership in `backend/rag_contaminated_sessions.json` (D023/D029) |

### Gaze - AOI-free cluster features (D025/D030-validated method; NOT the old AOI-anchored dwell/TTFF, which D021/D026/D030 confirmed unrecoverable on this dataset)
| Column | Type | Meaning |
|---|---|---|
| `gaze_missing` | bool | true if no gaze file, or &lt;3 valid samples in this window |
| `gaze_n_fixations` | int | I-VT fixation count in the window |
| `gaze_n_clusters` | int | unlabeled DBSCAN clusters over fixation mean gaze-direction (anonymous regions, no AOI identity - D025) |
| `gaze_n_transitions` | int | cluster-to-cluster switches across the fixation sequence |
| `gaze_transitions_per_fixation` | float | switching rate, normalized by fixation count |
| `gaze_dispersion` | float | 1 - resultant vector length of duration-weighted mean gaze direction (0 = all fixations identical direction) |
| `gaze_entropy_bits` | float | Shannon entropy over per-cluster dwell-time occupancy |

### EEG - relative band power in low-motion windows (67/140-qualified participants only)
16 columns: `eeg_{tp9,af7,af8,tp10}_{delta,theta,alpha,beta}_rel` (relative power per
channel per band, band power / total power via Welch PSD), plus:
| Column | Type | Meaning |
|---|---|---|
| `eeg_missing` | bool | true if participant not EEG-qualified, or window has &lt;2s of EEG samples |
| `eeg_low_motion_fraction` | float | fraction of the window's EEG samples retained after excluding above-median accelerometer-magnitude periods (motion-artifact mitigation, not full ICA/artifact rejection - a scoped, stated limitation) |

## What this schema deliberately excludes

- **AOI-anchored gaze features** (dwell time on coupon/price/kiosk-screen, TTFF)
  - closed off twice over for the existing 140 sessions (D021: no head pose;
  D026/D030: `aoi_mapper.py` falsified, vergence/depth issue). Would need new data
  collected with head-pose logging (D021/D027/D031) to ever populate these columns.
- **Video** - confirmed absent from the dataset entirely (prior Research Audit
  revisions).
- **Full EEG artifact rejection (ICA, eye-blink regression)** - the
  `eeg_low_motion_fraction` gate is a scoped, cheap mitigation, not a substitute for
  proper EEG preprocessing; flagged here so it isn't silently assumed to be more
  rigorous than it is.
