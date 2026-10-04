#!/usr/bin/env python3
"""
AOI-free gaze analysis pilot (Decision D021/D025).

Gaze is head-local only in the existing 140 sessions (no head pose logged - see D021),
so semantic AOI labels (coupon/price/kiosk-screen) are not recoverable. This prototypes
the fallback: unlabeled fixation clustering, switching rate, and dispersion/entropy
within each kiosk-decision window, on the same 3 pilot participants used throughout
(021, 041, 100). Pilot-stage only - not run across all 140.

Decision windows are built from the interaction log's own event markers:
  start = "Flowgraph Reached" (arrival at a station)
  end   = the first subsequent "charging" / "disabled_charging" / "driving" page event
No AOI identity is assigned anywhere in this script - clusters are unlabeled regions
in head-local gaze-direction space, nothing more.
"""
import glob
import json
import math

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

RAW_DATA_DIR = "/Users/naman/Documents/MTP/backend/raw_data"
OUT_DIR = "/Users/naman/Documents/MTP/gaze_pilot_out"

PILOTS = {
    "021": ("session_20260423_160401_021", "021.csv", "interactions_20260423_160415.csv"),
    "041": ("session_20260622_155420_041", "041.csv", "interactions_20260622_155502.csv"),
    "100": ("session_20260713_160902_100", "100.csv", "interactions_20260713_160920.csv"),
}

VELOCITY_THRESHOLD_DEG_S = 30.0
MIN_FIXATION_MS = 100.0
DBSCAN_EPS = 0.08       # unit-vector distance; chord length ~= angle in radians for small angles -> ~4.6 deg
DBSCAN_MIN_SAMPLES = 1  # an isolated single fixation is still its own cluster


def build_decision_windows(interactions_path):
    df = pd.read_csv(interactions_path)
    windows = []
    reached_ts, reached_station = None, None
    for _, row in df.iterrows():
        if row.get("direction") != "incoming" or row.get("channel") != "parsed_json":
            continue
        route = str(row.get("route", "")).strip().lower()
        msg = str(row.get("message", "")).strip().lower()
        page = str(row.get("page", "")).strip().lower()
        ts = row["timestamp_unix_ms"] / 1000.0
        if route == "flowgraph" and msg == "reached":
            reached_ts = ts
            try:
                reached_station = int(row.get("trial")) if not pd.isna(row.get("trial")) else None
            except Exception:
                reached_station = None
        elif route == "ui" and page in ("charging", "disabled_charging", "driving") and reached_ts is not None:
            windows.append({"station": reached_station, "start": reached_ts, "end": ts, "end_page": page})
            reached_ts = None
    return windows


def load_gaze(session_dir, gaze_file):
    cols = ["relative_to_unix_epoch_timestamp", "status", "stability",
            "gaze_forward_x", "gaze_forward_y", "gaze_forward_z"]
    df = pd.read_csv(f"{RAW_DATA_DIR}/{session_dir}/{gaze_file}", usecols=cols)
    df["t_epoch"] = df["relative_to_unix_epoch_timestamp"] / 1e9
    valid = (df["status"] == 2) & (df["stability"] > 0)
    return df[valid].sort_values("t_epoch").reset_index(drop=True)


def fixations_in_window(gaze_df, start, end):
    """I-VT fixation detection (same method as gaze_pilot.py) restricted to [start,end],
    returning each fixation's mean gaze_forward unit vector and timing."""
    seg = gaze_df[(gaze_df["t_epoch"] >= start) & (gaze_df["t_epoch"] <= end)].reset_index(drop=True)
    if len(seg) < 3:
        return []

    t = seg["t_epoch"].to_numpy()
    v = seg[["gaze_forward_x", "gaze_forward_y", "gaze_forward_z"]].to_numpy(dtype=np.float64)
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    v = v / norms

    dt = np.diff(t)
    dot = np.clip(np.sum(v[:-1] * v[1:], axis=1), -1.0, 1.0)
    ang_deg = np.degrees(np.arccos(dot))
    with np.errstate(divide="ignore", invalid="ignore"):
        ang_vel = np.where(dt > 0, ang_deg / dt, 0.0)
    gap_break = dt > 0.1
    is_saccade = (ang_vel > VELOCITY_THRESHOLD_DEG_S) | gap_break

    labels = np.ones(len(seg), dtype=bool)
    labels[1:][is_saccade] = False
    labels[:-1][is_saccade] = False

    fixations = []
    run_start = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[run_start]:
            if labels[run_start]:
                dur_ms = (t[i - 1] - t[run_start]) * 1000.0 if i - 1 > run_start else 1000.0 / 200.0
                if dur_ms >= MIN_FIXATION_MS:
                    mean_v = v[run_start:i].mean(axis=0)
                    mean_v = mean_v / (np.linalg.norm(mean_v) or 1.0)
                    fixations.append({
                        "start_t": t[run_start], "end_t": t[i - 1], "duration_ms": dur_ms,
                        "mean_dir": mean_v,
                    })
            run_start = i
    return fixations


def analyze_window(fixations):
    if len(fixations) == 0:
        return None
    dirs = np.array([f["mean_dir"] for f in fixations])

    if len(fixations) == 1:
        cluster_ids = np.array([0])
    else:
        db = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES, metric="euclidean")
        cluster_ids = db.fit_predict(dirs)
        # DBSCAN noise label (-1) with min_samples=1 shouldn't occur, but guard anyway
        cluster_ids = np.where(cluster_ids < 0, cluster_ids.max() + 1, cluster_ids)

    n_clusters = len(set(cluster_ids))
    transitions = int(np.sum(np.diff(cluster_ids) != 0))

    # dispersion via circular statistics: resultant vector length R of the mean fixation
    # directions (weighted by duration); dispersion = 1-R (0 = all fixations identical
    # direction, approaching 1 = fixations spread widely/uniformly)
    durs = np.array([f["duration_ms"] for f in fixations], dtype=np.float64)
    weighted = (dirs * durs[:, None]).sum(axis=0) / durs.sum()
    R = np.linalg.norm(weighted)
    dispersion = 1.0 - R

    # Shannon entropy over per-cluster dwell-time occupancy (bits)
    occ = {}
    for cid, d in zip(cluster_ids, durs):
        occ[cid] = occ.get(cid, 0.0) + d
    total = sum(occ.values())
    probs = [v / total for v in occ.values()]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)

    return {
        "n_fixations": len(fixations),
        "n_clusters": n_clusters,
        "n_transitions": transitions,
        "transitions_per_fixation": round(transitions / max(len(fixations) - 1, 1), 3),
        "dispersion_1_minus_R": round(dispersion, 4),
        "entropy_bits": round(entropy, 3),
        "cluster_sequence": cluster_ids.tolist(),
    }


all_rows = []
for pid, (session_dir, gaze_file, inter_file) in PILOTS.items():
    print(f"\n{'='*70}\nParticipant {pid}\n{'='*70}")
    windows = build_decision_windows(f"{RAW_DATA_DIR}/{session_dir}/{inter_file}")
    gaze_df = load_gaze(session_dir, gaze_file)
    print(f"  {len(windows)} decision window(s) found; {len(gaze_df)} valid gaze samples in full session")

    for w in windows:
        fixations = fixations_in_window(gaze_df, w["start"], w["end"])
        result = analyze_window(fixations)
        row = {"participant": pid, "station": w["station"], "window_duration_s": round(w["end"] - w["start"], 2),
               "end_page": w["end_page"]}
        if result:
            row.update(result)
        else:
            row["n_fixations"] = 0
        all_rows.append(row)
        print(f"  station {w['station']} ({w['window_duration_s' if False else 'end_page']} end, "
              f"{row['window_duration_s']}s): {row}")

df = pd.DataFrame(all_rows)
df.to_csv(f"{OUT_DIR}/aoi_free_pilot_summary.csv", index=False)
print(f"\n\nWrote {len(df)} window rows to {OUT_DIR}/aoi_free_pilot_summary.csv")
print(df[["participant","station","window_duration_s","n_fixations","n_clusters","n_transitions",
          "transitions_per_fixation","dispersion_1_minus_R","entropy_bits"]].to_string(index=False))
