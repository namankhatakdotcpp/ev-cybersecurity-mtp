"""
risk_model.py - loads the persisted RandomForest artifact
(backend/pipeline/model/risk_model.joblib, from train_production_model.py) and
exposes a single `predict_risk(features)` call.

This is Step 9/10's deployable output and the input `warning_system.py` (Step
12) consumes - the model itself makes the risk decision; nothing downstream
of this file re-derives or overrides it from raw signals (mid-sem report
Step 12's own constraint: "the language model... does not make the risk
decision").

Feature contract (must match train_production_model.py's FEATURE_COLS
exactly - checked at load time, not assumed): window_duration_s,
ai_help_used, gaze_n_fixations, gaze_n_clusters, gaze_n_transitions,
gaze_transitions_per_fixation, gaze_dispersion, gaze_entropy_bits. All gaze
features are the D025/D030-validated AOI-free set - never the AOI-anchored
dwell/TTFF features, which remain unrecoverable on this project's existing
data (D021/D026/D030).
"""
import os
from typing import Any, Dict, Optional

import joblib

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_PATH = os.path.join(_THIS_DIR, "pipeline", "model", "risk_model.joblib")


class RiskModel:
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"No trained risk model at {model_path} - run "
                f"backend/pipeline/train_production_model.py first."
            )
        artifact = joblib.load(model_path)
        self.model = artifact["model"]
        self.imputer = artifact["imputer"]
        self.scaler = artifact["scaler"]
        self.feature_cols = artifact["feature_cols"]

    def predict_risk(self, features: Dict[str, Optional[float]]) -> float:
        """Returns P(risky decision) in [0, 1]. `features` must have a key
        for every column in self.feature_cols - missing/None values are
        imputed (median, fit at training time), not silently zero-filled, per
        the project's standing missingness rule (Phase 1 schema,
        backend/pipeline/SCHEMA.md)."""
        missing = [c for c in self.feature_cols if c not in features]
        if missing:
            raise ValueError(f"predict_risk: missing required features: {missing}")
        row = [[features[c] for c in self.feature_cols]]
        imputed = self.imputer.transform(row)
        scaled = self.scaler.transform(imputed)
        proba = self.model.predict_proba(scaled)[0]
        # predict_proba's column order follows self.model.classes_, not
        # assumed to be [0, 1] - looked up explicitly so this is correct even
        # if sklearn ever changes that convention.
        classes = list(self.model.classes_)
        return float(proba[classes.index(1)])

    def predict_risk_batch(self, rows: list) -> list:
        """Same as predict_risk but for a list of feature dicts - avoids
        re-transforming one row at a time when scoring many at once."""
        for i, features in enumerate(rows):
            missing = [c for c in self.feature_cols if c not in features]
            if missing:
                raise ValueError(f"predict_risk_batch: row {i} missing features: {missing}")
        import numpy as np
        matrix = [[r[c] for c in self.feature_cols] for r in rows]
        imputed = self.imputer.transform(matrix)
        scaled = self.scaler.transform(imputed)
        proba = self.model.predict_proba(scaled)
        classes = list(self.model.classes_)
        idx = classes.index(1)
        return [float(p[idx]) for p in proba]
