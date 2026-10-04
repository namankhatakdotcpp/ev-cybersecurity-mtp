# Confirm local-SLM compliance on the actual RTX 4090 workstation

**Why this is needed:** D038's compliance numbers (baseline wording 60%, stronger
wording 100%) were measured on this session's Mac (Apple Silicon, Metal backend via
Ollama) - not the Windows/RTX 4090 workstation the real experiment will run on. Same
category of environment gap as the FPS objective (D004): this session cannot reach
that machine. The model weights are identical either way, but Ollama's default
quantization level, context handling, or a CUDA-vs-Metal numerical difference could
in principle shift the compliance rate. This is a **confirmation run**, not a full
re-measurement - 10 trials on the one condition that matters operationally (the
stronger wording, now the production default per D039/Task 4), not the full 40-trial
battery.

**You only need to do this once**, before treating the local-SLM path as the final
automation-bias design decision for new data collection.

## Steps

1. **Install Ollama on the Windows workstation** (skip if already installed - check
   with `ollama --version` in a terminal):
   - Download from https://ollama.com/download/windows and run the installer, or
   - If you prefer winget: `winget install Ollama.Ollama`

2. **Pull the same model used in D038**, so the comparison is apples-to-apples:
   ```
   ollama pull mistral:7b-instruct
   ```
   This downloads ~4.4GB - same model, same tag, as this session used.

3. **Copy these two files from this project onto the workstation** (same repo, just
   needs to be present wherever you run the confirmation):
   - `backend/ai_assistant.py` (has the `llm_backend="local_slm"` option, D036/D039)
   - `backend/test_automation_bias_slm.py` (the test harness, D038)

4. **Confirm Ollama is reachable** (it listens on `localhost:11434` by default - no
   separate "start the server" step needed on Windows, the installer sets it up as a
   background service):
   ```
   curl http://localhost:11434/api/version
   ```
   Should return a small JSON blob with a version string. If it doesn't, check
   Ollama is actually running (Windows system tray icon, or `ollama serve` manually).

5. **Run a 10-trial confirmation batch, stronger wording only** - the full
   `test_automation_bias_slm.py` runs both wordings at N_TRIALS (20 each, imported
   from `test_automation_bias_reliability.py`); for this confirmation, override just
   the stronger-wording batch at n=10 from a Python shell in `backend/`:
   ```python
   from test_automation_bias_slm import run_batch, STRONGER_INSTRUCTION
   results, complied, n = run_batch("CONFIRMATION on RTX 4090", STRONGER_INSTRUCTION, n=10)
   ```
   This reuses the exact same prompt-construction and compliance-checking code as
   D038 - only the machine it runs on differs.

6. **Report back**: compliance count out of 10, and whether it's consistent with
   D038's Mac result (20/20 = 100%, 95% CI [83.9%, 100%]). A result anywhere in the
   8-10/10 range is consistent with that CI and confirms the Mac result transfers.
   Anything meaningfully lower (e.g. 5/10 or below) would mean the Mac/Metal numbers
   do **not** transfer to the CUDA/Windows deployment as-is, and the automation-bias
   design decision in D039/Task 4 would need revisiting before being treated as final.

## What this does NOT need to check

- VRAM headroom - D038 already established this is not a binding constraint for a
  7B model on a 24GB card (desk reasoning, not measured, but not in question here).
- The baseline wording - it's no longer the production setting (D039/Task 4 promoted
  the stronger wording to be the only production override text), so re-confirming
  its weaker 60% rate isn't operationally necessary right now.
- Fine-tuning anything - out of scope per the standing instruction not to fine-tune
  this round.
