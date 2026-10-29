"""Tests with synthetic frame times only; no measured data is used or stored."""
import math

import numpy as np
import pandas as pd
import pytest

from backend.fps.analyze_frametimes import (BUDGET_MS, analyze, find_columns, load_frametimes, low_fps, run_metrics, schedule, summarize)


def _write(path, ft, col="msBetweenPresents", dropped=None):
    d = {col: ft}
    if dropped is not None:
        d["Dropped"] = dropped
    pd.DataFrame(d).to_csv(path, index=False)


def test_constant_90_fps():
    m = run_metrics(np.full(900, BUDGET_MS))
    assert m["mean_fps"] == pytest.approx(90.0)
    assert m["fps_1pct_low"] == pytest.approx(90.0)
    assert m["over_budget_share"] == 0.0 and m["severe_late_share"] == 0.0
    assert m["fps_min"] == pytest.approx(90.0)


def test_spikes_set_the_lows_and_shares():
    ft = np.concatenate([np.full(990, 10.0), np.full(10, 50.0)])       # 1% of frames at 50 ms
    m = run_metrics(ft)
    assert m["fps_1pct_low"] == pytest.approx(1000 / 50.0)             # slowest 1% are exactly the 10 spikes
    assert m["fps_01pct_low"] == pytest.approx(1000 / 50.0)
    assert m["over_budget_share"] == pytest.approx(0.01)
    assert m["severe_late_share"] == pytest.approx(0.01)
    assert m["mean_fps"] == pytest.approx(1000 / 10.4)
    assert m["fps_min"] == pytest.approx(20.0)


def test_budget_boundary_is_not_late():
    assert run_metrics([BUDGET_MS] * 10)["over_budget_share"] == 0.0
    assert run_metrics([BUDGET_MS + 0.01] * 10)["over_budget_share"] == 1.0
    assert run_metrics([2 * BUDGET_MS] * 10)["severe_late_share"] == 0.0


def test_point_one_percent_low_needs_enough_frames():
    assert math.isnan(low_fps(np.full(500, 10.0), 0.1))
    assert not math.isnan(low_fps(np.full(1000, 10.0), 0.1))


def test_percentiles_of_a_ramp():
    m = run_metrics(np.arange(1, 1001, dtype=float))
    assert m["p50_ms"] == pytest.approx(500.5)
    assert m["p99_ms"] == pytest.approx(np.percentile(np.arange(1, 1001), 99))


def test_column_detection_is_case_insensitive_and_fails_loudly():
    assert find_columns(["Application", "FrameTime", "Dropped"]) == ("FrameTime", "Dropped")
    assert find_columns(["x", "MSBETWEENPRESENTS"])[0] == "MSBETWEENPRESENTS"
    with pytest.raises(ValueError):
        find_columns(["Application", "CPUTime"])


def test_warmup_and_window_trimming(tmp_path):
    p = tmp_path / "a.csv"
    _write(p, np.concatenate([np.full(1000, 100.0), np.full(1000, 10.0)]))      # 100 s at 100 ms, then 10 s at 10 ms
    ft, _ = load_frametimes(p, warmup_s=100.0)
    assert len(ft) == 1000 and set(ft) == {10.0}
    ft, _ = load_frametimes(p, warmup_s=100.0, window_s=5.0)
    assert len(ft) == 500


def test_dropped_column_counted_after_trimming(tmp_path):
    p = tmp_path / "d.csv"
    _write(p, np.full(200, 10.0), col="FrameTime", dropped=[1] * 5 + [0] * 195)
    _, dropped = load_frametimes(p, warmup_s=0.0)
    assert dropped == 5
    _, dropped = load_frametimes(p, warmup_s=1.0)                                # the first 100 frames are warm-up
    assert dropped == 0


def test_bad_rows_and_empty_trim_are_errors(tmp_path):
    p = tmp_path / "bad.csv"
    _write(p, [10.0, float("nan"), 10.0])
    with pytest.raises(ValueError):
        load_frametimes(p)
    q = tmp_path / "short.csv"
    _write(q, [10.0] * 10)
    with pytest.raises(ValueError):
        load_frametimes(q, warmup_s=60.0)


def test_manifest_summary_and_baseline_difference(tmp_path):
    rng = np.random.default_rng(0)
    rows = []
    for cond, base in (("C0", 14.0), ("C5", 10.0)):
        for rep in (1, 2, 3):
            f = f"{cond}_{rep}.csv"
            _write(tmp_path / f, base + rng.normal(0, 0.2, 2000))
            rows.append(dict(run_id=f"{cond}-{rep}", condition=cond, repeat=rep, file=f))
    rows.append(dict(run_id="X-1", condition="C0", repeat=4, file="none.csv", kind="overlay-only"))
    pd.DataFrame(rows).to_csv(tmp_path / "runs.csv", index=False)
    runs = analyze(tmp_path / "runs.csv", warmup_s=1.0)
    assert len(runs) == 6                                                        # the overlay-only row is skipped
    s = summarize(runs, "C0").set_index("condition")
    assert s.loc["C5", "mean_fps_diff_vs_C0"] > 0 and s.loc["C0", "mean_fps_diff_vs_C0"] == 0
    assert s.loc["C0", "over_budget_share_mean"] > s.loc["C5", "over_budget_share_mean"]
    assert s.loc["C0", "runs"] == 3


def test_manifest_without_required_columns_fails(tmp_path):
    pd.DataFrame({"run_id": ["a"]}).to_csv(tmp_path / "runs.csv", index=False)
    with pytest.raises(ValueError):
        analyze(tmp_path / "runs.csv")


def test_schedule_is_blocked_random_and_reproducible():
    a = schedule(["C0", "C5"], 5, seed=1)
    assert a == schedule(["C0", "C5"], 5, seed=1)
    assert [o for o, _, _ in a] == list(range(1, 11))
    for rep in range(1, 6):
        assert sorted(c for _, c, r in a if r == rep) == ["C0", "C5"]
    assert a != schedule(["C0", "C5"], 5, seed=2)


def test_no_measurement_files_are_stored_in_the_repository():
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    assert not list((root / "docs" / "fps").glob("**/*.csv")) and not (root / "docs" / "fps" / "data").exists()
