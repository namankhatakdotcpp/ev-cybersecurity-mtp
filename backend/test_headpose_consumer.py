"""
Unit test for D053's Python-side consumer of evHeadPoseLogger.lua
(receive_ui.py's _handle_headpose_batch / headpose_*.csv writer).

Does NOT require a real BeamNG connection - BeamNGpy's constructor doesn't
connect until .open() is called, and these tests never call .open(). Mocks
nothing BeamNG-related because nothing BeamNG-related is exercised: this
tests pure data handling (JSON batch in, CSV rows out, timestamp
reconstruction), which is the only part of the consumer this session can
validate without the real Windows/BeamNG workstation. The Lua side
(evHeadPoseLogger.lua) and the actual queue_lua_command round-trip remain
UNTESTED, same as that file's own header states.
"""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from receive_ui import EVBackend


class HeadPoseConsumerTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # __init__ already calls _init_headpose_log() when the flag is set
        # (receive_ui.py) - no need to call it again here.
        self.backend = EVBackend(
            rag_enabled=False,
            interaction_log_dir=self.tmpdir,
            experiment_config={"head_pose_logging_enabled": True},
        )

    def tearDown(self):
        try:
            if self.backend.headpose_log_file:
                self.backend.headpose_log_file.close()
            if self.backend.log_file:
                self.backend.log_file.close()
        except Exception:
            pass

    def _read_rows(self):
        with open(self.backend.headpose_log_path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_header_matches_declared_schema(self):
        with open(self.backend.headpose_log_path, newline="", encoding="utf-8") as f:
            header = next(csv.reader(f))
        self.assertEqual(header, [
            "timestamp_unix_ms", "pos_x", "pos_y", "pos_z",
            "quat_x", "quat_y", "quat_z", "quat_w", "marker",
        ])

    def test_batch_writes_one_row_per_sample(self):
        samples = [
            {"px": 1.0, "py": 2.0, "pz": 3.0, "qx": 0, "qy": 0, "qz": 0, "qw": 1, "dtSim": 0.0},
            {"px": 1.1, "py": 2.0, "pz": 3.0, "qx": 0, "qy": 0, "qz": 0, "qw": 1, "dtSim": 0.01},
            {"px": 1.2, "py": 2.0, "pz": 3.0, "qx": 0, "qy": 0, "qz": 0, "qw": 1, "dtSim": 0.01},
        ]
        self.backend._handle_headpose_batch(json.dumps(samples))
        rows = self._read_rows()
        self.assertEqual(len(rows), 3)
        self.assertEqual(float(rows[0]["pos_x"]), 1.0)
        self.assertEqual(float(rows[2]["pos_x"]), 1.2)

    def test_timestamps_reconstructed_in_increasing_order_from_dtSim(self):
        # 3 samples, 10ms apart (dtSim on sample i = gap since sample i-1).
        samples = [
            {"px": 0, "py": 0, "pz": 0, "qx": 0, "qy": 0, "qz": 0, "qw": 1, "dtSim": 0.0},
            {"px": 0, "py": 0, "pz": 0, "qx": 0, "qy": 0, "qz": 0, "qw": 1, "dtSim": 0.01},
            {"px": 0, "py": 0, "pz": 0, "qx": 0, "qy": 0, "qz": 0, "qw": 1, "dtSim": 0.01},
        ]
        self.backend._handle_headpose_batch(json.dumps(samples))
        rows = self._read_rows()
        ts = [int(r["timestamp_unix_ms"]) for r in rows]
        self.assertEqual(ts, sorted(ts), "reconstructed timestamps must be monotonically increasing")
        # Each gap should be ~10ms (reconstructed from dtSim), not 0 and not huge.
        self.assertAlmostEqual(ts[1] - ts[0], 10, delta=2)
        self.assertAlmostEqual(ts[2] - ts[1], 10, delta=2)
        # The last sample should be anchored very close to "now" (receipt time).
        import time
        now_ms = int(time.time() * 1000)
        self.assertLess(abs(now_ms - ts[-1]), 1000)

    def test_marker_field_round_trips(self):
        samples = [
            {"px": 0, "py": 0, "pz": 0, "qx": 0, "qy": 0, "qz": 0, "qw": 1, "dtSim": 0.0},
            {"px": 0, "py": 0, "pz": 0, "qx": 0, "qy": 0, "qz": 0, "qw": 1, "dtSim": 0.0,
             "marker": "calibration_nod"},
        ]
        self.backend._handle_headpose_batch(json.dumps(samples))
        rows = self._read_rows()
        self.assertEqual(rows[0]["marker"], "")
        self.assertEqual(rows[1]["marker"], "calibration_nod")

    def test_empty_batch_is_a_noop(self):
        self.backend._handle_headpose_batch("[]")
        self.assertEqual(self._read_rows(), [])

    def test_nil_response_is_a_noop(self):
        # queue_lua_command returns the string "nil" when a Lua function
        # exists but hasn't produced a value, or isn't loaded - must not crash.
        self.backend._handle_headpose_batch("nil")
        self.assertEqual(self._read_rows(), [])

    def test_malformed_json_does_not_raise(self):
        try:
            self.backend._handle_headpose_batch("{not valid json")
        except Exception as e:
            self.fail(f"_handle_headpose_batch raised on malformed JSON: {e}")
        self.assertEqual(self._read_rows(), [])

    def test_disabled_by_default(self):
        backend2 = EVBackend(rag_enabled=False, interaction_log_dir=tempfile.mkdtemp())
        try:
            self.assertFalse(backend2.config["head_pose_logging_enabled"])
            self.assertIsNone(backend2.headpose_log_file)
        finally:
            if backend2.log_file:
                backend2.log_file.close()


if __name__ == "__main__":
    unittest.main()
