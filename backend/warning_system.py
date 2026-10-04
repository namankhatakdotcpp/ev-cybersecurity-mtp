"""
warning_system.py - Step 12 of the mid-sem report's pipeline ("AI Warning
System"), as a scaffold for the next phase, not a live-wired system.

Per the report's own description of this step: "The trained model's risk
estimate decides WHEN a warning is shown... A Small Language Model may be
used as a separate layer that converts structured context (risk level,
reason, kiosk) into a short natural-language warning... The language model
never processes raw EEG or video and does not make the risk decision."

This file implements exactly that division of labor:
  1. risk_model.RiskModel makes the risk decision (a probability, from
     behaviour+gaze features only - see that file).
  2. WarningSystem.decide() applies a threshold to that probability to decide
     WHETHER to warn - still not LLM involvement.
  3. Only once both of those are settled does an LLM (local SLM by default,
     D038/D042 - the validated, no-quota path) get called, and only with the
     already-decided risk_level/reason/kiosk as structured input - never the
     underlying gaze/EEG/behavioural features themselves.

====================================================================
WHY THIS IS A SCAFFOLD, NOT A LIVE SYSTEM - READ BEFORE WIRING THIS IN
====================================================================
This cannot be connected to receive_ui.py's live gameplay loop yet, for a
concrete, checked reason, not a vague caveat:

  The risk model's features (window_duration_s, gaze_n_clusters,
  gaze_transitions_per_fixation, gaze_dispersion, gaze_entropy_bits, etc.)
  are computed POST-HOC by build_feature_table.py, reading an entire
  session's already-logged gaze CSV after the session is over. There is no
  code anywhere in this project (checked: grepped receive_ui.py and the gaze
  pipeline directory) that computes a gaze-cluster feature DURING an
  in-progress decision window from a live stream - because (D027) gaze
  capture is a wholly separate external application that was never found to
  feed anything into BeamNG's Python backend in real time at all, batch or
  streaming.

  Building that live feature-computation path is new infrastructure work,
  not a config change - it needs a live gaze-ingestion connection (the same
  missing piece D027/D031 already identified for head-pose), a decision on
  what "decision window so far" means for a feature like gaze_entropy_bits
  that's currently computed over a COMPLETE window, and probably a
  simplified/incremental version of the AOI-free clustering method (D025)
  that can update sample-by-sample rather than only after the fact.

  Until that exists, this module is usable in exactly one way: scored
  AFTER a session, on its own post-hoc features (see `score_session_offline`
  below) - useful for research/retrospective analysis of what a warning
  system WOULD have said, not for showing a participant a warning live.
====================================================================

Risk thresholds below are UPDATED (D057) from held-out, Platt-calibrated
probabilities (5-fold participant-level GroupKFold OOF, nested CV for the
calibration itself) - a real improvement over D055's original thresholds,
which came from the model's own overfit in-sample distribution. They are
still NOT validated against any real user-response data, because none
exists yet (that's precisely mid-sem report Step 13, "User Response and
Trust" - not started). At these thresholds, measured on held-out data: ~23%
of decisions score "low" (no warning), ~10% score "high", ~77% would trigger
should_warn (medium+high) - a real, measured consequence of this model's
current discriminative power (AUROC~0.6-0.7), not a bug. Recalibrate the
OPERATING POINT (not just refit the probabilities) against real data once
Step 13 is actually run, if a lower warning rate is wanted.
"""
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from risk_model import RiskModel

# D057: on the Platt-calibrated scale now (RiskModel applies the calibrator
# automatically when one is attached - see risk_model.py). Picked after
# inspecting the held-out calibrated distribution (deciles ~0.19-0.50+), not
# hardcoded in advance - see backend/pipeline/calibrate_risk_model.py and
# Decision.md D057 for the full comparison against isotonic calibration.
RISK_THRESHOLD_LOW = 0.25
RISK_THRESHOLD_HIGH = 0.50

DEFAULT_WARNING_MESSAGE = "This kiosk looks unusual - please double-check before charging here."


def _risk_level(risk_score: float) -> str:
    if risk_score < RISK_THRESHOLD_LOW:
        return "low"
    if risk_score < RISK_THRESHOLD_HIGH:
        return "medium"
    return "high"


class WarningSystem:
    def __init__(self, model_path: Optional[str] = None,
                 llm_backend: str = "local_slm",
                 local_slm_model: str = "mistral:7b-instruct",
                 local_slm_url: str = "http://localhost:11434/api/generate"):
        """
        llm_backend: "local_slm" (default - the validated, no-daily-quota path,
        D038/D042) or "gemini" (requires GEMINI_API_KEY in backend/.env, same
        as ai_assistant.py, and shares its 20-request/day free-tier cap,
        D028/D032/D038 - do not default to this for anything that might run
        many trials). "none" skips LLM phrasing entirely and returns
        DEFAULT_WARNING_MESSAGE - useful for testing the risk-decision logic
        without needing any LLM backend available at all.
        """
        self.risk_model = RiskModel(model_path) if model_path else RiskModel()
        if llm_backend not in ("local_slm", "gemini", "none"):
            raise ValueError(f"Unknown llm_backend: {llm_backend!r}")
        self.llm_backend = llm_backend
        self.local_slm_model = local_slm_model
        self.local_slm_url = local_slm_url
        self._gemini_client = None
        if llm_backend == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                try:
                    from google import genai
                    self._gemini_client = genai.Client(api_key=api_key)
                except Exception as e:
                    print(f"[WarningSystem] Gemini init failed, falling back to default message: {e}")

    def decide(self, features: Dict[str, Optional[float]], kiosk_label: str = "this kiosk",
               reason: Optional[str] = None) -> Dict[str, Any]:
        """Makes the risk decision (step 1-2 above) and, if warranted, phrases
        a warning (step 3). Returns a dict with the risk score, level,
        whether to warn, and the message - every field auditable, nothing
        hidden inside an opaque "warning or not" boolean."""
        risk_score = self.risk_model.predict_risk(features)
        level = _risk_level(risk_score)
        should_warn = level in ("medium", "high")

        message = None
        if should_warn:
            message = self._phrase_warning(level, kiosk_label, reason)

        return {
            "risk_score": round(risk_score, 4),
            "risk_level": level,
            "should_warn": should_warn,
            "message": message,
            "feature_cols_used": self.risk_model.feature_cols,
        }

    def _phrase_warning(self, risk_level: str, kiosk_label: str, reason: Optional[str]) -> str:
        """The ONLY function in this file that calls an LLM. Receives
        risk_level/kiosk_label/reason only - never the raw feature values,
        never gaze/EEG data, per the mid-sem report's own Step 12 constraint."""
        if self.llm_backend == "none":
            return DEFAULT_WARNING_MESSAGE

        reason_clause = f" ({reason})" if reason else ""
        prompt = (
            "You are generating a brief in-VR safety nudge for a driving simulation about EV "
            "charging kiosk safety. A risk-assessment system (not you) has already determined the "
            f"risk level is '{risk_level}' for {kiosk_label}{reason_clause}. Write ONE short sentence "
            "(under 20 words) suggesting the user pause and reconsider before charging here. Do not "
            "invent specific anomalies or reasons beyond what was given. Do not mention 'AI', 'model', "
            "'risk score', or that this is automated - phrase it as a simple in-game safety prompt."
        )

        if self.llm_backend == "local_slm":
            return self._invoke_local_slm(prompt)
        if self.llm_backend == "gemini" and self._gemini_client:
            try:
                resp = self._gemini_client.models.generate_content(
                    model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite"), contents=prompt)
                text = (getattr(resp, "text", None) or "").strip()
                return text or DEFAULT_WARNING_MESSAGE
            except Exception as e:
                print(f"[WarningSystem] Gemini call failed: {e}")
                return DEFAULT_WARNING_MESSAGE
        return DEFAULT_WARNING_MESSAGE

    def _invoke_local_slm(self, prompt: str) -> str:
        payload = json.dumps({
            "model": self.local_slm_model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.7},
        }).encode("utf-8")
        try:
            req = urllib.request.Request(self.local_slm_url, data=payload,
                                          headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                text = (body.get("response") or "").strip()
                return text or DEFAULT_WARNING_MESSAGE
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"[WarningSystem] Local SLM call failed, using default message: {e}")
            return DEFAULT_WARNING_MESSAGE


def score_session_offline(session_dir: str) -> list:
    """Research/retrospective use only (see module docstring): runs the
    warning decision over an ALREADY-COMPLETED session's post-hoc features,
    one row per station-decision - what the warning system WOULD have said,
    not a live capability. Reuses build_feature_table.py's own extraction
    logic rather than duplicating it."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline"))
    from build_feature_table import (
        build_station_events, load_gaze, fixations_in_window, gaze_features,
    )
    import glob

    inter_files = glob.glob(os.path.join(session_dir, "interactions_*.csv"))
    if not inter_files:
        raise FileNotFoundError(f"No interactions_*.csv found in {session_dir}")
    stations = build_station_events(inter_files[0])

    gaze_files = [f for f in glob.glob(os.path.join(session_dir, "*.csv"))
                  if not os.path.basename(f).startswith("interactions")]
    gaze_df = load_gaze(gaze_files[0]) if gaze_files else None

    ws = WarningSystem(llm_backend="none")  # offline scoring - no LLM calls by default
    results = []
    for st in stations:
        features = {
            "window_duration_s": st["window_duration_s"],
            "ai_help_used": float(st["ai_help_used"]),
        }
        gf = None
        if gaze_df is not None and len(gaze_df) > 0:
            fixations = fixations_in_window(gaze_df, st["window_start_ms"], st["window_end_ms"])
            gf = gaze_features(fixations)
        for col in ("gaze_n_fixations", "gaze_n_clusters", "gaze_n_transitions",
                    "gaze_transitions_per_fixation", "gaze_dispersion", "gaze_entropy_bits"):
            features[col] = gf[col] if gf else None

        decision = ws.decide(features, kiosk_label=f"Kiosk {st['kiosk_used']}" if st["kiosk_used"] else "this station")
        decision["trial"] = st["trial"]
        decision["actual_decision"] = st["decision"]
        results.append(decision)
    return results
