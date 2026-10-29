"""Analyse per-frame logs from the FPS measurement protocol (docs/fps/FPS_MEASUREMENT_PROTOCOL.md).

Reads a manifest `runs.csv` (columns run_id, condition, repeat, file; optional kind) and one frame-time CSV per run, and writes
per-run metrics and a per-condition summary. It contains no measured data and invents none: with no input there is no output.

  python -m backend.fps.analyze_frametimes analyze --manifest runs.csv --out out_dir [--warmup-s 10] [--window-s 120] [--baseline C0]
  python -m backend.fps.analyze_frametimes schedule --conditions C0,C5 --repeats 5 --seed 1
"""
import argparse
import math
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REFRESH_HZ = 90.0
BUDGET_MS = 1000.0 / REFRESH_HZ
FRAME_TIME_COLUMNS = ("msbetweenpresents", "frametime", "frametime_ms", "ms_between_presents", "msbetweendisplaychange_unused")
TOL = 1e-9
METRICS = ["frames", "duration_s", "mean_fps", "fps_1pct_low", "fps_01pct_low", "p50_ms", "p95_ms", "p99_ms", "p999_ms",
           "over_budget_share", "severe_late_share", "dropped_frames", "fps_min"]


def find_columns(header):
    """Returns (frame-time column, dropped column or None); fails loudly if no frame-time column is recognised."""
    low = {h.strip().lower(): h for h in header}
    for name in FRAME_TIME_COLUMNS:
        if name in low:
            return low[name], low.get("dropped")
    raise ValueError(f"no frame-time column found in {list(header)}; expected one of {FRAME_TIME_COLUMNS[:4]}")


def load_frametimes(path, warmup_s=0.0, window_s=None):
    """Frame times in ms after dropping the first `warmup_s` seconds, and (optionally) keeping `window_s` seconds; plus the dropped count or None."""
    df = pd.read_csv(path)
    col, dcol = find_columns(df.columns)
    ft = pd.to_numeric(df[col], errors="coerce")
    ok = ft.notna() & (ft > 0)
    if not ok.all():
        raise ValueError(f"{path}: {int((~ok).sum())} rows have a missing or non-positive frame time")
    ft = ft.to_numpy(dtype=float)
    start = np.cumsum(ft) - ft
    keep = start >= warmup_s * 1000.0
    if window_s is not None:
        keep &= start < (warmup_s + window_s) * 1000.0
    dropped = None
    if dcol is not None:
        d = df[dcol].astype(str).str.strip().str.lower().isin(["1", "true", "yes"]).to_numpy()
        dropped = int(d[keep].sum())
    ft = ft[keep]
    if len(ft) == 0:
        raise ValueError(f"{path}: no frames left after the warm-up and window trimming")
    return ft, dropped


def low_fps(ft, pct):
    """FPS equivalent of the mean of the slowest `pct` percent of frames; NaN if fewer than 100/pct frames exist."""
    n = len(ft)
    if n < 100.0 / pct:
        return float("nan")
    k = max(1, math.ceil(n * pct / 100.0))
    return 1000.0 / float(np.sort(ft)[-k:].mean())


def run_metrics(ft, dropped=None, budget_ms=BUDGET_MS):
    ft = np.asarray(ft, dtype=float)
    total = float(ft.sum())
    return {
        "frames": len(ft), "duration_s": total / 1000.0, "mean_fps": len(ft) / (total / 1000.0),
        "fps_1pct_low": low_fps(ft, 1.0), "fps_01pct_low": low_fps(ft, 0.1),
        "p50_ms": float(np.percentile(ft, 50)), "p95_ms": float(np.percentile(ft, 95)),
        "p99_ms": float(np.percentile(ft, 99)), "p999_ms": float(np.percentile(ft, 99.9)),
        "over_budget_share": float((ft > budget_ms + TOL).mean()), "severe_late_share": float((ft > 2 * budget_ms + TOL).mean()),
        "dropped_frames": dropped if dropped is not None else float("nan"), "fps_min": 1000.0 / float(ft.max()),
    }


def analyze(manifest, warmup_s=10.0, window_s=None):
    manifest = Path(manifest)
    m = pd.read_csv(manifest, dtype=str)
    missing = {"run_id", "condition", "repeat", "file"} - set(m.columns)
    if missing:
        raise ValueError(f"manifest lacks columns {sorted(missing)}")
    rows = []
    for r in m.itertuples():
        if getattr(r, "kind", "frametime") == "overlay-only":
            continue
        ft, dropped = load_frametimes(manifest.parent / r.file, warmup_s, window_s)
        rows.append({"run_id": r.run_id, "condition": r.condition, "repeat": r.repeat, **run_metrics(ft, dropped)})
    if not rows:
        raise ValueError("the manifest has no run with a per-frame log")
    return pd.DataFrame(rows)


def summarize(runs, baseline="C0"):
    """Mean, min and max of each run-level metric per condition, plus the difference of the condition mean to the baseline mean. Descriptive only."""
    cols = [c for c in METRICS if c not in ("frames", "duration_s")]
    g = runs.groupby("condition")
    out = []
    for cond, d in g:
        row = {"condition": cond, "runs": len(d)}
        for c in cols:
            row[f"{c}_mean"], row[f"{c}_min"], row[f"{c}_max"] = d[c].mean(), d[c].min(), d[c].max()
        out.append(row)
    s = pd.DataFrame(out).set_index("condition")
    if baseline in s.index:
        for c in cols:
            s[f"{c}_diff_vs_{baseline}"] = s[f"{c}_mean"] - s.loc[baseline, f"{c}_mean"]
    return s.reset_index()


def schedule(conditions, repeats, seed):
    """Blocked random order: each block of `len(conditions)` runs contains every condition once."""
    rng = random.Random(seed)
    order = []
    for rep in range(1, repeats + 1):
        block = list(conditions)
        rng.shuffle(block)
        order += [(len(order) + i + 1, c, rep) for i, c in enumerate(block)]
    return order


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--manifest", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--warmup-s", type=float, default=10.0)
    a.add_argument("--window-s", type=float, default=None)
    a.add_argument("--baseline", default="C0")
    s = sub.add_parser("schedule")
    s.add_argument("--conditions", required=True)
    s.add_argument("--repeats", type=int, required=True)
    s.add_argument("--seed", type=int, required=True)
    args = ap.parse_args(argv)
    if args.cmd == "schedule":
        print("order,condition,repeat")
        for o, c, r in schedule(args.conditions.split(","), args.repeats, args.seed):
            print(f"{o},{c},{r}")
        return 0
    runs = analyze(args.manifest, args.warmup_s, args.window_s)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runs.to_csv(out / "run_metrics.csv", index=False, float_format="%.4f")
    summarize(runs, args.baseline).to_csv(out / "condition_summary.csv", index=False, float_format="%.4f")
    print(f"wrote {out / 'run_metrics.csv'} and {out / 'condition_summary.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
