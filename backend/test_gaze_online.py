"""
Validation for gaze_online.py (D056): a replay harness (streams real,
already-logged sessions through GazeOnlineProcessor sample-by-sample) plus
unit tests asserting agreement with the offline pipeline.

Agreement is tested two different ways, because they test two different
things:
  1. EXACT agreement on short windows: when the trailing buffer window is
     large enough to contain an ENTIRE decision window, the online processor
     is running the identical algorithm (same functions, literally imported
     from build_feature_table.py) on the identical data as the offline
     pipeline - these MUST match exactly, and a test asserts they do. If this
     fails, gaze_online.py has a real bug, not an expected streaming/offline
     difference.
  2. REPORTED (not asserted pass/fail) divergence on longer windows: a 3s
     trailing buffer at the END of a 20s decision window is measuring
     something genuinely different from the offline whole-window computation
     - this is expected, and the honest thing to do is report the max/mean
     absolute difference, not hide it behind a tolerance assertion that would
     either be meaninglessly loose or fail for a reason that isn't a bug.

Latency is measured and reported for ingest() (the true per-raw-sample cost,
called once per gaze sample, ~200 Hz worth in a real session) SEPARATELY from
compute_features() (called only at a simulated polling cadence, not once per
raw sample - see gaze_online.py's own module docstring for why conflating the
two would misrepresent what "per-sample latency" actually costs).
"""
import csv
import sys
import time
import unittest

import numpy as np

from gaze_online import GazeOnlineProcessor, DEFAULT_WINDOW_S

sys.path.insert(0, "/Users/naman/Documents/MTP/backend/pipeline")
from build_feature_table import build_station_events, load_gaze, fixations_in_window, gaze_features  # noqa: E402

RAW_DATA_DIR = "/Users/naman/Documents/MTP/backend/raw_data"

# A real consumer calling compute_features() every raw sample would pay an
# O(buffer size) cost per sample - this project's existing polling loops all
# run at 5 Hz (odometer/UI/head-pose workers, D053/D054), so that's used here
# as the simulated recompute cadence, NOT asserted as sufficient for anything
# - just a reasonable, already-established-in-this-project starting point.
SIMULATED_POLL_HZ = 5.0


def _discover_five_sessions():
    from build_feature_table import discover_sessions
    sessions = discover_sessions()
    with_gaze = [s for s in sessions if s["gaze_file"]]
    return with_gaze[:5]


def _load_raw_gaze_rows(gaze_path):
    """Loads EVERY row (valid and invalid) with its timestamp already
    converted to epoch-ms, unfiltered - so the replay harness can feed
    GazeOnlineProcessor realistic raw input (including invalid samples) and
    let it do its own filtering, exactly as a live consumer would."""
    rows = []
    with open(gaze_path, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                t_ms = float(r["relative_to_unix_epoch_timestamp"]) / 1e6
                rows.append({
                    "t_epoch_ms": t_ms,
                    "x": float(r["gaze_forward_x"]), "y": float(r["gaze_forward_y"]),
                    "z": float(r["gaze_forward_z"]),
                    "status": int(float(r["status"])), "stability": float(r["stability"]),
                })
            except (ValueError, KeyError):
                continue
    rows.sort(key=lambda r: r["t_epoch_ms"])
    return rows


def replay_session(session, window_s=DEFAULT_WINDOW_S, poll_hz=SIMULATED_POLL_HZ):
    """Streams one session's decision windows through GazeOnlineProcessor:
    ingest() on every raw sample (measuring that latency), compute_features()
    only every ~(1/poll_hz) seconds of simulated time (measuring THAT latency
    separately) and once more at the end of each window for comparison
    against the offline whole-window computation."""
    inter_file = session["interactions_file"]
    gaze_file = session["gaze_file"]
    stations = build_station_events(inter_file)
    raw_rows = _load_raw_gaze_rows(gaze_file)

    records = []
    ingest_latencies_ms = []
    compute_latencies_ms = []
    poll_interval_ms = 1000.0 / poll_hz

    for st in stations:
        window_rows = [r for r in raw_rows if st["window_start_ms"] <= r["t_epoch_ms"] <= st["window_end_ms"]]
        if len(window_rows) < 3:
            continue

        proc = GazeOnlineProcessor(window_s=window_s)
        last_poll_ms = None
        last_features = None
        for r in window_rows:
            t0 = time.perf_counter()
            proc.ingest(r["t_epoch_ms"], r["x"], r["y"], r["z"], r["status"], r["stability"])
            ingest_latencies_ms.append((time.perf_counter() - t0) * 1000.0)

            if last_poll_ms is None or (r["t_epoch_ms"] - last_poll_ms) >= poll_interval_ms:
                t1 = time.perf_counter()
                feats = proc.compute_features()
                compute_latencies_ms.append((time.perf_counter() - t1) * 1000.0)
                if feats is not None:
                    last_features = feats
                last_poll_ms = r["t_epoch_ms"]

        # One final compute at window end, so "online_final" reflects the
        # last few seconds of the window even if the last poll tick landed
        # slightly before window_end.
        final_feats = proc.compute_features()
        if final_feats is not None:
            last_features = final_feats

        gaze_df = load_gaze(gaze_file)
        offline_fixations = fixations_in_window(gaze_df, st["window_start_ms"], st["window_end_ms"])
        offline_features = gaze_features(offline_fixations)

        records.append({
            "trial": st["trial"], "window_duration_s": st["window_duration_s"],
            "n_raw_samples": len(window_rows),
            "online_final": last_features, "offline": offline_features,
        })

    return records, ingest_latencies_ms, compute_latencies_ms


def _abs_diffs(records, key):
    diffs = []
    for r in records:
        if r["online_final"] is None or r["offline"] is None:
            continue
        if key not in r["online_final"] or key not in r["offline"]:
            continue
        diffs.append(abs(r["online_final"][key] - r["offline"][key]))
    return diffs


class ExactAgreementOnShortWindowsTest(unittest.TestCase):
    """When window_s covers the ENTIRE decision window, the trailing buffer
    ends up containing the SAME samples the offline whole-window computation
    uses - online and offline must then be identical, since both call the
    exact same fixations_in_window/gaze_features functions. Ingests every raw
    sample cheaply, computes features exactly ONCE at the end (not per
    sample) - this is a correctness check, not a per-sample-cost benchmark."""

    def test_online_matches_offline_when_window_covers_whole_decision_window(self):
        sessions = _discover_five_sessions()
        self.assertGreaterEqual(len(sessions), 1, "need at least one session with gaze data to test")
        session = sessions[0]
        stations = build_station_events(session["interactions_file"])
        raw_rows = _load_raw_gaze_rows(session["gaze_file"])
        gaze_df = load_gaze(session["gaze_file"])

        tested_any = False
        for st in stations:
            window_rows = [r for r in raw_rows if st["window_start_ms"] <= r["t_epoch_ms"] <= st["window_end_ms"]]
            if len(window_rows) < 3:
                continue
            huge_window_s = (st["window_end_ms"] - st["window_start_ms"]) / 1000.0 + 1.0
            proc = GazeOnlineProcessor(window_s=huge_window_s)
            for r in window_rows:
                proc.ingest(r["t_epoch_ms"], r["x"], r["y"], r["z"], r["status"], r["stability"])
            online_features = proc.compute_features()

            offline_fixations = fixations_in_window(gaze_df, st["window_start_ms"], st["window_end_ms"])
            offline_features = gaze_features(offline_fixations)

            if online_features is None or offline_features is None:
                continue
            tested_any = True
            for key in ("gaze_n_fixations", "gaze_n_clusters", "gaze_n_transitions",
                        "gaze_transitions_per_fixation", "gaze_entropy_bits"):
                self.assertEqual(
                    online_features[key], offline_features[key],
                    f"trial {st['trial']}, key={key}: online={online_features[key]} != offline={offline_features[key]}"
                )
            self.assertAlmostEqual(online_features["gaze_dispersion"], offline_features["gaze_dispersion"], places=6)

        self.assertTrue(tested_any, "no decision window in this session had enough samples to test exact agreement")


class ReplayHarnessSmokeTest(unittest.TestCase):
    def test_replay_runs_without_error_on_five_sessions(self):
        sessions = _discover_five_sessions()
        self.assertEqual(len(sessions), 5)
        for session in sessions:
            records, ingest_lat, compute_lat = replay_session(session, window_s=DEFAULT_WINDOW_S)
            self.assertIsInstance(records, list)
            self.assertIsInstance(ingest_lat, list)
            self.assertIsInstance(compute_lat, list)


def main_report():
    """Runs the full 5-session replay at the default 3s window, reports
    max/mean absolute difference per feature (the expected, informative
    online-vs-offline divergence on real decision windows, most of which are
    longer than 3s) and ingest/compute latency separately - the deliverable
    the task asked for, not just pass/fail tests."""
    sessions = _discover_five_sessions()
    print(f"Replaying {len(sessions)} sessions at window_s={DEFAULT_WINDOW_S}, "
          f"simulated poll rate={SIMULATED_POLL_HZ} Hz\n")

    all_records = []
    all_ingest = []
    all_compute = []
    for session in sessions:
        print(f"=== {session['session_dir']} ===")
        records, ingest_lat, compute_lat = replay_session(session, window_s=DEFAULT_WINDOW_S)
        all_records.extend(records)
        all_ingest.extend(ingest_lat)
        all_compute.extend(compute_lat)
        for r in records:
            print(f"  trial {r['trial']} ({r['window_duration_s']:.1f}s, {r['n_raw_samples']} samples): "
                  f"online={r['online_final']}  offline={r['offline']}")
        print()

    print("="*78)
    ing = np.array(all_ingest)
    comp = np.array(all_compute)
    print(f"ingest() latency across {len(ing)} raw samples (this Mac, NOT the lab workstation):")
    print(f"  mean={ing.mean()*1000:.1f}us  median={np.median(ing)*1000:.1f}us  "
          f"p95={np.percentile(ing, 95)*1000:.1f}us  max={ing.max():.3f}ms")
    print(f"\ncompute_features() latency across {len(comp)} calls (simulated {SIMULATED_POLL_HZ} Hz poll cadence):")
    print(f"  mean={comp.mean():.3f}ms  median={np.median(comp):.3f}ms  "
          f"p95={np.percentile(comp, 95):.3f}ms  max={comp.max():.3f}ms")
    poll_budget_ms = 1000.0 / SIMULATED_POLL_HZ
    print(f"  (budget at {SIMULATED_POLL_HZ} Hz polling: {poll_budget_ms:.1f}ms/call - "
          f"{'within budget' if comp.max() < poll_budget_ms else 'EXCEEDS budget on at least one call'})")

    print(f"\nOnline (3s trailing window, end-of-window snapshot) vs. offline (whole decision window) "
          f"- EXPECTED divergence on windows longer than {DEFAULT_WINDOW_S}s, reported not asserted:")
    for key in ("gaze_n_clusters", "gaze_entropy_bits", "gaze_transitions_per_fixation"):
        diffs = _abs_diffs(all_records, key)
        if diffs:
            d = np.array(diffs)
            print(f"  {key}: n={len(d)} mean_abs_diff={d.mean():.4f} max_abs_diff={d.max():.4f}")
        else:
            print(f"  {key}: no comparable windows (online or offline returned None)")

    long_windows = [r for r in all_records if r["window_duration_s"] > DEFAULT_WINDOW_S]
    short_windows = [r for r in all_records if r["window_duration_s"] <= DEFAULT_WINDOW_S]
    print(f"\n{len(short_windows)}/{len(all_records)} decision windows were <= {DEFAULT_WINDOW_S}s "
          f"(online and offline see the same data for these); {len(long_windows)} were longer "
          f"(online reports only the final {DEFAULT_WINDOW_S}s, by design).")


if __name__ == "__main__":
    if "--report" in sys.argv:
        main_report()
    else:
        unittest.main()
