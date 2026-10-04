"""
Unit tests for risk_model.py / warning_system.py (the Step 12 "AI Warning
System" scaffold). Uses llm_backend="none" throughout except one explicit
real-SLM test, so these pass without needing Ollama running - the risk
decision logic (the part that matters for correctness) is independent of
which LLM backend phrases the message.

Requires backend/pipeline/model/risk_model.joblib to exist
(train_production_model.py) - these are integration tests against the real
trained artifact, not a mocked model, since the whole point is to check the
actual deployed artifact loads and behaves sensibly.
"""
import os
import unittest

from risk_model import RiskModel
from warning_system import WarningSystem, _risk_level, RISK_THRESHOLD_LOW, RISK_THRESHOLD_HIGH, DEFAULT_WARNING_MESSAGE

ALL_FEATURE_COLS = [
    "window_duration_s", "ai_help_used", "gaze_n_fixations", "gaze_n_clusters",
    "gaze_n_transitions", "gaze_transitions_per_fixation", "gaze_dispersion", "gaze_entropy_bits",
]

LOW_RISK_FEATURES = {
    "window_duration_s": 5.0, "ai_help_used": 0.0, "gaze_n_fixations": 3, "gaze_n_clusters": 1,
    "gaze_n_transitions": 0, "gaze_transitions_per_fixation": 0.0, "gaze_dispersion": 0.01,
    "gaze_entropy_bits": 0.1,
}
HIGH_RISK_FEATURES = {
    "window_duration_s": 40.0, "ai_help_used": 1.0, "gaze_n_fixations": 60, "gaze_n_clusters": 8,
    "gaze_n_transitions": 30, "gaze_transitions_per_fixation": 0.6, "gaze_dispersion": 0.08,
    "gaze_entropy_bits": 2.0,
}


class RiskLevelThresholdTest(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(_risk_level(0.0), "low")
        self.assertEqual(_risk_level(RISK_THRESHOLD_LOW - 0.01), "low")
        self.assertEqual(_risk_level(RISK_THRESHOLD_LOW), "medium")
        self.assertEqual(_risk_level(RISK_THRESHOLD_HIGH - 0.01), "medium")
        self.assertEqual(_risk_level(RISK_THRESHOLD_HIGH), "high")
        self.assertEqual(_risk_level(1.0), "high")


class RiskModelTest(unittest.TestCase):
    def setUp(self):
        self.model = RiskModel()

    def test_feature_contract_matches_declared_columns(self):
        self.assertEqual(set(self.model.feature_cols), set(ALL_FEATURE_COLS))

    def test_calibrator_is_attached(self):
        # D057 - the deployed artifact should have a Platt calibrator after
        # calibrate_risk_model.py --save has been run.
        self.assertTrue(self.model.is_calibrated, "expected a calibrator attached to the deployed artifact (D057)")
        self.assertIsNotNone(self.model.calibrator)

    def test_calibrated_risk_still_a_probability(self):
        score = self.model.predict_risk(HIGH_RISK_FEATURES)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_calibration_preserves_relative_ranking(self):
        # Platt/isotonic calibration is a MONOTONIC transform of the raw
        # score by construction - a feature set with a higher raw score must
        # not end up with a LOWER calibrated score than one with a lower raw
        # score. Checked on the two fixtures directly (not assumed from
        # calibrate_risk_model.py's own report).
        raw_low = self.model._raw_proba([[LOW_RISK_FEATURES[c] for c in self.model.feature_cols]])[0]
        raw_high = self.model._raw_proba([[HIGH_RISK_FEATURES[c] for c in self.model.feature_cols]])[0]
        cal_low = self.model.predict_risk(LOW_RISK_FEATURES)
        cal_high = self.model.predict_risk(HIGH_RISK_FEATURES)
        if raw_high > raw_low:
            self.assertGreaterEqual(cal_high, cal_low,
                                     "calibration must not reverse the raw model's ranking")

    def test_predict_risk_returns_probability(self):
        score = self.model.predict_risk(LOW_RISK_FEATURES)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_missing_feature_raises(self):
        incomplete = dict(LOW_RISK_FEATURES)
        del incomplete["gaze_entropy_bits"]
        with self.assertRaises(ValueError):
            self.model.predict_risk(incomplete)

    def test_none_values_are_imputed_not_rejected(self):
        with_missing = dict(LOW_RISK_FEATURES)
        with_missing["gaze_entropy_bits"] = None  # e.g. gaze_missing=True upstream
        score = self.model.predict_risk(with_missing)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_batch_matches_individual_calls(self):
        individual = [self.model.predict_risk(LOW_RISK_FEATURES), self.model.predict_risk(HIGH_RISK_FEATURES)]
        batch = self.model.predict_risk_batch([LOW_RISK_FEATURES, HIGH_RISK_FEATURES])
        self.assertEqual(len(batch), 2)
        for a, b in zip(individual, batch):
            self.assertAlmostEqual(a, b, places=6)

    def test_model_path_not_found_raises_clear_error(self):
        with self.assertRaises(FileNotFoundError):
            RiskModel(model_path="/nonexistent/path/model.joblib")


class WarningSystemNoLLMTest(unittest.TestCase):
    """llm_backend='none' - tests the risk-decision logic without requiring
    any LLM backend to be running."""

    def setUp(self):
        self.ws = WarningSystem(llm_backend="none")

    def test_low_risk_features_do_not_warn(self):
        result = self.ws.decide(LOW_RISK_FEATURES, kiosk_label="Kiosk 1")
        self.assertEqual(result["risk_level"], "low")
        self.assertFalse(result["should_warn"])
        self.assertIsNone(result["message"])

    def test_warn_uses_default_message_when_llm_backend_is_none(self):
        result = self.ws.decide(HIGH_RISK_FEATURES, kiosk_label="Kiosk 2")
        if result["should_warn"]:
            self.assertEqual(result["message"], DEFAULT_WARNING_MESSAGE)

    def test_result_never_leaks_raw_features_as_the_decision_mechanism(self):
        # The result dict should carry which feature COLUMNS were used (for
        # auditability) but decide() itself must not require passing raw
        # features through to the LLM-phrasing step - checked structurally by
        # confirming _phrase_warning's signature takes only
        # risk_level/kiosk_label/reason, not features.
        import inspect
        sig = inspect.signature(self.ws._phrase_warning)
        self.assertEqual(list(sig.parameters.keys()), ["risk_level", "kiosk_label", "reason"])

    def test_invalid_llm_backend_rejected(self):
        with self.assertRaises(ValueError):
            WarningSystem(llm_backend="not_a_real_backend")


class OfflineSessionScoringTest(unittest.TestCase):
    def test_scores_a_real_completed_session(self):
        from warning_system import score_session_offline
        session_dir = "/Users/naman/Documents/MTP/backend/raw_data/session_20260421_134202_008"
        if not os.path.isdir(session_dir):
            self.skipTest("sample session directory not present in this environment")
        results = score_session_offline(session_dir)
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertIn(r["risk_level"], ("low", "medium", "high"))
            self.assertIn("trial", r)
            self.assertIn("actual_decision", r)


if __name__ == "__main__":
    unittest.main()
