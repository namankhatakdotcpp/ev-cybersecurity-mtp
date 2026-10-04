"""
gaze_online.py - a streaming, sample-at-a-time gaze-feature computer, built to
close the specific gap D055 found: no part of this project computes gaze
features in real time, only post-hoc over a complete, already-logged session.

Reuses the offline pipeline's own fixation-detection and clustering functions
(`build_feature_table.fixations_in_window`/`gaze_features`) directly, rather
than reimplementing the I-VT/DBSCAN logic - the online and offline paths run
literally the same code on whatever window of samples they're given, so any
difference between them is a difference in WHICH samples are in the window
(a trailing N-second buffer vs. the whole decision window), not a difference
in algorithm. See `test_gaze_online.py` for the validation that follows from
this design: when the trailing window covers an entire (short) decision
window, online and offline must agree exactly - and are tested to.

Two-stage API, not "add_sample does everything," because they have genuinely
different costs and a real consumer needs to control them separately:
  - `ingest()` is O(buffer eviction) - cheap, meant to be called for every
    raw gaze sample (Varjo reports at ~199-200 Hz, D020).
  - `compute_features()` re-runs I-VT + DBSCAN over the current buffer -
    this is NOT free (a fresh DataFrame + the full offline algorithm every
    call), and calling it at 200 Hz would make per-sample cost scale with
    buffer size, not stay constant. A real consumer (e.g. warning_system.py)
    should call this at whatever its own polling cadence is (5 Hz, matching
    the rest of this project's polling loops, is a reasonable starting
    point - NOT validated as sufficient, same caveat D053/D054 already
    attached to the head-pose polling rate), not once per raw sample.
  - `add_sample()` is kept as ingest()+compute_features() in one call, for
    callers (and the exact-agreement test) that want the simplest API and
    don't care about the cost distinction - not recommended for a tight
    200 Hz loop; see the module's own benchmark output for why.

=== What this is NOT, stated plainly (same standard as D055's own scaffold) ===
This has never processed a live gaze stream - no live Varjo connection exists
anywhere in this project (D027), so everything here is validated by REPLAYING
already-logged gaze CSVs sample-by-sample, not by a real live feed. Latency
numbers are measured on this session's hardware (Apple Silicon, this Mac),
not the lab workstation - report, don't assume, if/when this runs there.
"""
import sys
from collections import deque
from typing import Optional

import pandas as pd

sys.path.insert(0, "/Users/naman/Documents/MTP/backend/pipeline")
from build_feature_table import fixations_in_window, gaze_features  # noqa: E402

DEFAULT_WINDOW_S = 3.0


class GazeOnlineProcessor:
    """Maintains a trailing `window_s` buffer of valid gaze samples; computes
    AOI-free gaze-cluster features (D025/D030) over the current buffer on
    demand, using the exact offline algorithm restricted to this window
    instead of a whole decision window."""

    def __init__(self, window_s: float = DEFAULT_WINDOW_S):
        self.window_s = window_s
        self.buffer = deque()  # dicts: t_epoch_ms, gaze_forward_x/y/z
        self.n_samples_seen = 0
        self.n_samples_valid = 0

    def reset(self) -> None:
        self.buffer.clear()
        self.n_samples_seen = 0
        self.n_samples_valid = 0

    def ingest(self, t_epoch_ms: float, x: float, y: float, z: float,
               status: int, stability: float) -> None:
        """O(eviction) - append one sample to the trailing buffer if valid,
        evict anything older than window_s. Matches load_gaze()'s offline
        pre-filter exactly: only status==2 and stability>0 samples are kept -
        an invalid sample is dropped, same as the offline pipeline dropping
        it before windowing ever sees it. Does NOT recompute features - call
        compute_features() separately when a fresh estimate is actually
        needed."""
        self.n_samples_seen += 1
        if status == 2 and stability > 0:
            self.n_samples_valid += 1
            self.buffer.append({
                "t_epoch_ms": t_epoch_ms,
                "gaze_forward_x": x, "gaze_forward_y": y, "gaze_forward_z": z,
            })
            cutoff_ms = t_epoch_ms - self.window_s * 1000.0
            while self.buffer and self.buffer[0]["t_epoch_ms"] < cutoff_ms:
                self.buffer.popleft()

    def compute_features(self) -> Optional[dict]:
        """Re-runs the offline I-VT/DBSCAN algorithm over the CURRENT
        trailing buffer. Not O(1) - cost scales with buffer size (number of
        valid samples currently in window_s). Returns None if fewer than 3
        samples are buffered (same minimum as the offline
        fixations_in_window())."""
        if len(self.buffer) < 3:
            return None
        df = pd.DataFrame(self.buffer)
        start_ms = float(df["t_epoch_ms"].min())
        end_ms = float(df["t_epoch_ms"].max())
        fixations = fixations_in_window(df, start_ms, end_ms)
        return gaze_features(fixations)

    def add_sample(self, t_epoch_ms: float, x: float, y: float, z: float,
                   status: int, stability: float) -> Optional[dict]:
        """Convenience: ingest() then compute_features() in one call. Costs
        a full recomputation every call - fine for tests/small buffers or a
        deliberately throttled call site, NOT recommended as the actual
        per-raw-sample call in a 200 Hz loop. See module docstring."""
        self.ingest(t_epoch_ms, x, y, z, status, stability)
        return self.compute_features()
