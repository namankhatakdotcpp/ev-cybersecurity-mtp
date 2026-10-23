# EV Cybersecurity using Eye-Tracking

**EV Energy Cybersecurity Resilience Test for the Infrastructure Using Eye Tracking and AI**

Major Technical Project (MTP), Indian Institute of Technology Mandi.

| | |
|---|---|
| **Students** | Arpita Kumari (B23249, B.Tech. Electrical Engineering), Naman Khatak (B23217, B.Tech. Data Science and Engineering) |
| **Mentor** | Ranik Goyal |
| **Supervisor** | Prof. Varun Dutt |

---

## Problem statement

> How do people make decisions at compromised EV charging kiosks, and can behavioural, eye-tracking and EEG signals identify vulnerable decision-making?

Public EV chargers are networked computers that authorise users, process payments, and display information the user is expected to trust. A malicious kiosk doesn't need to compromise the vehicle — it can advertise a fraudulent discount, under-credit a payment, or fail the vehicle after charging, and the attack succeeds or fails entirely on the human decision in front of it. This project studies that decision inside an immersive VR driving simulation (BeamNG.tech), recording eye movements (Varjo XR-4) and EEG (Muse S Athena) while participants choose among real and compromised charging kiosks.

Three research questions drive the work:

1. Which information do users inspect, and in what order, before accepting or rejecting a potentially malicious kiosk?
2. Do gaze, EEG and behavioural patterns distinguish risky decisions from safe ones, evaluated on participants not seen during training?
3. Can a risk estimate derived from these patterns drive an AI warning that improves decisions, without producing blind reliance on the warning itself?

## Current status vs. the proposed pipeline

The originally proposed pipeline (mid-sem report, Section 10) fuses **video + eye-tracking + EEG** features and trains a phased deep-learning model — MLP baseline → LSTM/GRU (temporal) → Transformer (multimodal attention) — gated so each phase is kept only if it beats the one before it. What has actually been built and run, as of this writing:

| Component | Status |
|---|---|
| Classical ML baselines (logistic regression, random forest, XGBoost) | **Run for real**, participant-level cross-validation, full modality ablation |
| MLP (Phase 1) | **Run for real** — did not beat the classical baseline on either metric, so later phases were correctly gated off |
| LSTM/GRU, Transformer (Phases 2–3) | Not attempted — never cleared the gate required to proceed to them |
| Video-feature extraction | Not implemented — the deployed model uses **behaviour + gaze only**, no video, no EEG |
| EEG fusion | Evaluated in the ablation (does not detectably add signal over gaze+behaviour at this sample size, see Results) |
| Risk-decision model → threshold → AI-warning phrasing (Step 12) | **Built and deployed** — one RandomForest makes the risk decision, a local SLM only phrases the resulting warning, never the reverse |
| New data collection (Objective 3) | Infrastructure prepped (RAG auto-clear, head-pose logging hook, QC script, collection protocol); physical data collection not yet started |

This gap is tracked explicitly rather than glossed over — see `Decision.md` D058 and the Research Audit documents for the full reasoning behind each deviation.

## Results (citable numbers only)

All numbers below come from real runs with participant-level train/test splits (no participant ever appears in both). Full detail, every ablation cell, and every confidence interval live in `Decision.md`.

**Deployed model's final configuration** — behaviour (minus the RAG-contamination flag) + the six AOI-free gaze features, RandomForest, time-ordered holdout (D050):

| Metric | Value [95% CI] |
|---|---|
| Balanced accuracy | 0.620 [0.556, 0.682] |
| AUROC | 0.695 [0.623, 0.759] |

Adding EEG does not detectably improve on this: the behaviour+gaze+EEG AUROC [0.628, 0.749] overlaps almost completely with behaviour+gaze alone — both are genuinely above chance, but EEG's incremental contribution is not resolvable at this sample size (D050).

**Confirmatory mixed-effects model** (`BinomialBayesMixedGLM`, crossed random effects for participant and station, D052). Two of three AOI-free gaze features survive FDR correction:

| Gaze feature | Odds ratio | 95% CI |
|---|---|---|
| `gaze_n_clusters` | 1.66 | [1.44, 1.92] |
| `gaze_entropy_bits` | 1.32 | [1.14, 1.52] |

(A much larger station-level attack-presence effect was also found in that same model, but it is a near-tautology — a station with no compromised kiosk cannot produce a risky outcome — so it is reported as a sanity check, not a headline result.)

**Risk-score calibration** (D057): the deployed model's raw probability output was not well-calibrated on held-out data. Platt scaling is applied before thresholding (chosen over isotonic regression, which scored a better Brier score but compressed almost all of its output into an unusable range). At the current thresholds, ~77% of decisions fall at or above the "warn" level on held-out data — a direct, honest consequence of the model's AUROC, not a tuning bug.

## Repository layout

```
backend/
  pipeline/            Feature extraction, baselines, ablations, GLMM, calibration, model artifacts
  risk_model.py         Loads the deployed model, applies calibration if present
  warning_system.py     Risk decision -> threshold -> optional SLM-phrased warning (never the reverse)
  gaze_online.py         Streaming (online) version of the gaze-feature computation
  receive_ui.py / main.py / ai_assistant.py / rag.py   Simulation backend, RAG-based in-game assistant
  BeamNG.tech.../lua/ge/extensions/   Project-authored Lua hooks (e.g. head-pose logging)
Decision.md             Authoritative, append-only decision log — every finding, every run, every reversal
*.pdf / *.docx           Research audit and supporting documentation
```

Large/derived data (`raw_data/`, decoded EEG, the RAG index, the BeamNG engine install, Python virtual environments) is intentionally excluded from version control — see `.gitignore`. Data lives alongside this repository on whichever machine runs the pipeline, not inside it.

## Running the pipeline

```bash
cd backend/pipeline
python3 train_baselines.py          # classical ML baselines + modality ablation
python3 train_mlp.py                # MLP, gated against the baseline above
python3 final_ablation_table.py     # the consolidated, CI-backed ablation table (D050)
python3 mixed_effects_model.py      # confirmatory GLMM (D052)
python3 calibrate_risk_model.py     # risk-score calibration check (D057)
```

Tests:

```bash
cd backend
python3 -m unittest test_warning_system -v
python3 -m unittest test_gaze_online -v
```

The local SLM warning-phrasing path (`llm_backend="local_slm"`) expects [Ollama](https://ollama.com) running locally with the relevant model pulled (e.g. `ollama pull mistral:7b-instruct`); it falls back to a default message if unavailable, so nothing else depends on it being present.

## Decision log

Every finding, every run, every reversal in this project is logged in [`Decision.md`](Decision.md) as a sequential, append-only entry (Date / Decision / Context / Evidence / Reason / Alternatives Considered / Implementation / Status / Impact / Remarks). It is the single source of truth across every machine this project runs on — read its tail before picking up any task here.
