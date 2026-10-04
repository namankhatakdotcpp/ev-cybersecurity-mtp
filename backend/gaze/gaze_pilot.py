#!/usr/bin/env python3
"""
Gaze pipeline pilot: fixation/saccade detection on a handful of participants,
validating the approach before scaling to all 140 sessions.

Deliberately does NOT attempt AOI (coupon/price/kiosk-screen) mapping yet - that
requires either synchronized screen/scene geometry (which fixation code location
does not have access to) or manually calibrated screen-space regions, neither of
which exist in this dataset. This pilot establishes whether fixation/saccade
detection itself produces sane, physiologically plausible results first.

Method: I-VT (velocity-threshold) classification on the 3D gaze_forward unit
vector, after filtering samples to status==2 (valid track) and stability>0
(Varjo's own confidence fields, inspected directly from the data - not assumed).
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

RAW_DATA_DIR = "/Users/naman/Documents/MTP/backend/raw_data"
OUT_DIR = "/Users/naman/Documents/MTP/backend/Muse/decoded/../../gaze_pilot_out"  # placeholder, fixed below
OUT_DIR = "/Users/naman/Documents/MTP/gaze_pilot_out"
os.makedirs(OUT_DIR, exist_ok=True)

VELOCITY_THRESHOLD_DEG_S = 30.0   # standard I-VT cutoff for a moderately clean tracker
MIN_FIXATION_MS = 100.0           # literature floor (Salvucci & Goldberg 2000 use ~100ms)


def load_gaze(pid_str):
    candidates = glob.glob(os.path.join(RAW_DATA_DIR, f"session_*_{pid_str}", f"{int(pid_str)}.csv"))
    candidates += glob.glob(os.path.join(RAW_DATA_DIR, f"session_*_{pid_str}", f"{pid_str}.csv"))
    candidates = sorted(set(candidates))
    if not candidates:
        return None, None
    path = candidates[0]
    cols = [
        "relative_to_unix_epoch_timestamp", "frame_number", "stability", "status",
        "gaze_forward_x", "gaze_forward_y", "gaze_forward_z",
        "left_pupil_size", "right_pupil_size", "left_eye_openness", "right_eye_openness",
    ]
    df = pd.read_csv(path, usecols=cols)
    return df, path


def classify_fixations(df):
    # Quality filter using Varjo's own fields, not an assumption.
    valid = (df["status"] == 2) & (df["stability"] > 0)
    n_total = len(df)
    df = df[valid].copy()
    n_valid = len(df)

    df = df.sort_values("relative_to_unix_epoch_timestamp").reset_index(drop=True)
    t = df["relative_to_unix_epoch_timestamp"].to_numpy(dtype=np.float64) / 1e9  # ns -> s

    v = df[["gaze_forward_x", "gaze_forward_y", "gaze_forward_z"]].to_numpy(dtype=np.float64)
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    v = v / norms

    dt = np.diff(t)
    # angle between consecutive gaze-direction samples
    dot = np.clip(np.sum(v[:-1] * v[1:], axis=1), -1.0, 1.0)
    ang_deg = np.degrees(np.arccos(dot))
    with np.errstate(divide="ignore", invalid="ignore"):
        ang_vel = np.where(dt > 0, ang_deg / dt, 0.0)

    # Treat any sample-to-sample gap bigger than 100ms as a track break (don't let
    # a dropout masquerade as a single huge "saccade").
    gap_break = dt > 0.1
    is_saccade = (ang_vel > VELOCITY_THRESHOLD_DEG_S) | gap_break

    # label[i] applies to the transition from sample i to i+1; build per-sample fixation/saccade labels
    labels = np.ones(len(df), dtype=bool)  # True = fixation
    labels[1:][is_saccade] = False
    labels[:-1][is_saccade] = False

    # group into runs
    events = []
    run_start = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[run_start]:
            dur_ms = (t[i - 1] - t[run_start]) * 1000.0 if i - 1 > run_start else (1000.0 / 200.0)
            events.append({
                "kind": "fixation" if labels[run_start] else "saccade",
                "start_idx": run_start, "end_idx": i - 1,
                "start_t": t[run_start], "end_t": t[i - 1],
                "duration_ms": dur_ms,
                "n_samples": i - run_start,
            })
            run_start = i

    fixations = [e for e in events if e["kind"] == "fixation" and e["duration_ms"] >= MIN_FIXATION_MS]
    saccades = [e for e in events if e["kind"] == "saccade"]

    # saccade amplitude = angle between the gaze direction just before and just after
    for s in saccades:
        i0, i1 = s["start_idx"], min(s["end_idx"] + 1, len(v) - 1)
        amp = np.degrees(np.arccos(np.clip(np.dot(v[i0], v[i1]), -1.0, 1.0)))
        s["amplitude_deg"] = float(amp)

    return {
        "n_total_samples": n_total,
        "n_valid_samples": n_valid,
        "valid_fraction": round(n_valid / n_total, 4) if n_total else None,
        "duration_s": float(t[-1] - t[0]) if len(t) else None,
        "n_fixations": len(fixations),
        "n_saccades": len(saccades),
        "fixation_duration_ms_mean": float(np.mean([f["duration_ms"] for f in fixations])) if fixations else None,
        "fixation_duration_ms_median": float(np.median([f["duration_ms"] for f in fixations])) if fixations else None,
        "fixation_duration_ms_min": float(np.min([f["duration_ms"] for f in fixations])) if fixations else None,
        "fixation_duration_ms_max": float(np.max([f["duration_ms"] for f in fixations])) if fixations else None,
        "saccade_amplitude_deg_mean": float(np.mean([s["amplitude_deg"] for s in saccades])) if saccades else None,
        "saccade_amplitude_deg_median": float(np.median([s["amplitude_deg"] for s in saccades])) if saccades else None,
        "fixations_per_minute": round(len(fixations) / ((t[-1] - t[0]) / 60.0), 2) if len(t) > 1 else None,
    }, fixations, saccades


def main():
    pids = sys.argv[1:] or ["021", "041", "100"]
    summary_rows = []
    for pid in pids:
        print(f"\n=== Participant {pid} ===")
        df, path = load_gaze(pid)
        if df is None:
            print("  no gaze file found")
            continue
        print(f"  file: {path}, {len(df)} rows")
        stats, fixations, saccades = classify_fixations(df)
        stats["participant_id"] = pid
        summary_rows.append(stats)
        for k, v in stats.items():
            print(f"  {k}: {v}")

        # Save fixation events for manual inspection
        pd.DataFrame(fixations).to_csv(os.path.join(OUT_DIR, f"{pid}_fixations.csv"), index=False)
        pd.DataFrame(saccades).to_csv(os.path.join(OUT_DIR, f"{pid}_saccades.csv"), index=False)

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(os.path.join(OUT_DIR, "gaze_pilot_summary.csv"), index=False)
    print(f"\n\nWrote pilot summary to {os.path.join(OUT_DIR, 'gaze_pilot_summary.csv')}")


if __name__ == "__main__":
    main()
