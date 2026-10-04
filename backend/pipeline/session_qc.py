#!/usr/bin/env python3
"""
Per-session QC check (Objective 3 prep): a pass/fail flag per modality, for one
session or across every session in backend/raw_data/. Read-only - never writes
into raw_data, never modifies a session folder.

Checks, thresholds taken directly from already-established project rules
(cited inline, not invented for this script):
  - gaze:      valid-sample fraction (Varjo status==2 & stability>0, D020/D022's
               established filter) >= 50% (D022's proposed session-level
               exclusion threshold, applied here for the first time as an
               actual per-session check rather than left as a proposal).
  - eeg:       flatline fraction (D013/decode_all.py's own method: fraction of
               zero-diff consecutive samples per EEG_ channel) < 15% in every
               channel (D019's inclusion rule). Only applicable where a decoded
               EEG file exists for this participant - "not_available" is a
               distinct status from "fail", since most existing sessions never
               had a Muse headband at all.
  - events:    number of "Flowgraph"/"Reached" events logged ~20 (the mid-sem
               report's own "about 15-20 per session" scenario description,
               Section 7.2) - pass band widened slightly to 15-25 to avoid
               penalizing sessions that legitimately ran a couple of stations
               short/over.
  - head_pose: a head-pose log file for this session exists and is non-empty.
               Expects the format `evHeadPoseLogger.lua` (D031/this round's
               Task 2) would produce once a Python-side consumer polls and
               writes it - NOT YET IMPLEMENTED on the Python side (only the
               Lua buffer/drain hook exists, UNTESTED). This check is written
               now so new-data-collection sessions can be QC'd the moment that
               consumer exists; for every one of the existing 140 sessions (and
               for any session before that consumer is wired) this will
               correctly, honestly report FAIL - head pose was never logged for
               them (D021), this is not a bug in this script.
               Expected file: <session_dir>/headpose_*.csv with at least the
               columns timestamp_unix_ms,pos_x,pos_y,pos_z,quat_x,quat_y,
               quat_z,quat_w - this exact schema is this script's own stated
               expectation (not yet implemented elsewhere), documented here so
               the Python-side consumer, when written, has a concrete target.
"""
import argparse
import glob
import json
import os
import re

import numpy as np
import pandas as pd

RAW_DATA_DIR = "/Users/naman/Documents/MTP/backend/raw_data"
EEG_DECODED_DIR = "/Users/naman/Documents/MTP/backend/Muse/decoded"

GAZE_VALID_FRACTION_MIN = 0.50       # D022
EEG_FLATLINE_FRACTION_MAX = 0.15     # D019
REACHED_EVENTS_MIN = 15              # mid-sem report Sec 7.2 ("about 15-20")
REACHED_EVENTS_MAX = 25


def _is_gaze_csv(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            header = f.readline()
        return "gaze_forward_x" in header
    except Exception:
        return False


def _find_gaze_file(session_dir):
    candidates = [f for f in glob.glob(os.path.join(session_dir, "*.csv"))
                  if not os.path.basename(f).startswith("interactions") and _is_gaze_csv(f)]
    return candidates[0] if candidates else None


def _find_interactions_file(session_dir):
    candidates = glob.glob(os.path.join(session_dir, "interactions_*.csv"))
    return candidates[0] if candidates else None


def _participant_id_from_dirname(session_dir):
    m = re.match(r"session_\d+_\d+_(\d+)", os.path.basename(session_dir))
    return m.group(1) if m else None


def check_gaze(session_dir):
    gaze_path = _find_gaze_file(session_dir)
    if gaze_path is None:
        return {"status": "fail", "reason": "no gaze file found", "valid_fraction": None}
    try:
        df = pd.read_csv(gaze_path, usecols=["status", "stability"])
    except Exception as e:
        return {"status": "fail", "reason": f"could not read gaze file: {e}", "valid_fraction": None}
    if len(df) == 0:
        return {"status": "fail", "reason": "gaze file is empty", "valid_fraction": None}
    valid = (df["status"] == 2) & (df["stability"] > 0)
    frac = float(valid.mean())
    status = "pass" if frac >= GAZE_VALID_FRACTION_MIN else "fail"
    return {"status": status, "reason": f"valid_fraction={frac:.4f} (threshold {GAZE_VALID_FRACTION_MIN})",
            "valid_fraction": round(frac, 4)}


def check_eeg(participant_id):
    eeg_path = os.path.join(EEG_DECODED_DIR, participant_id, f"{participant_id}_eeg_decoded.csv")
    if not os.path.exists(eeg_path):
        return {"status": "not_available", "reason": "no decoded EEG file for this participant", "max_flatline": None}
    try:
        df = pd.read_csv(eeg_path)
    except Exception as e:
        return {"status": "fail", "reason": f"could not read EEG file: {e}", "max_flatline": None}
    eeg_cols = [c for c in df.columns if c.startswith("EEG_")]
    if not eeg_cols:
        return {"status": "fail", "reason": "decoded EEG file has no EEG_ columns", "max_flatline": None}
    flat_fracs = {}
    for col in eeg_cols:
        vals = df[col].to_numpy(dtype=float)
        if len(vals) > 10:
            flat_fracs[col] = float(np.sum(np.diff(vals) == 0) / (len(vals) - 1))
    if not flat_fracs:
        return {"status": "fail", "reason": "too few samples to compute flatline fraction", "max_flatline": None}
    max_flat = max(flat_fracs.values())
    status = "pass" if max_flat < EEG_FLATLINE_FRACTION_MAX else "fail"
    return {"status": status,
            "reason": f"max_flatline={max_flat:.4f} across channels (threshold {EEG_FLATLINE_FRACTION_MAX})",
            "max_flatline": round(max_flat, 4)}


def check_events(session_dir):
    inter_path = _find_interactions_file(session_dir)
    if inter_path is None:
        return {"status": "fail", "reason": "no interactions file found", "n_reached": None}
    n_reached = 0
    try:
        with open(inter_path, newline="", encoding="utf-8", errors="ignore") as f:
            import csv
            for row in csv.DictReader(f):
                payload_raw = row.get("payload_json") or ""
                if '"Message": "Reached"' in payload_raw or '"Message":"Reached"' in payload_raw:
                    try:
                        payload = json.loads(payload_raw)
                        if payload.get("route") == "Flowgraph" and payload.get("Message") == "Reached":
                            n_reached += 1
                    except Exception:
                        pass
    except Exception as e:
        return {"status": "fail", "reason": f"could not read interactions file: {e}", "n_reached": None}
    status = "pass" if REACHED_EVENTS_MIN <= n_reached <= REACHED_EVENTS_MAX else "fail"
    return {"status": status,
            "reason": f"n_reached={n_reached} (expected {REACHED_EVENTS_MIN}-{REACHED_EVENTS_MAX})",
            "n_reached": n_reached}


def check_head_pose(session_dir):
    candidates = glob.glob(os.path.join(session_dir, "headpose_*.csv"))
    if not candidates:
        return {"status": "fail", "reason": "no headpose_*.csv found (D021: never logged for "
                "existing sessions; for new sessions, requires the Python-side consumer for "
                "evHeadPoseLogger.lua, not yet implemented - see this file's header)",
                "n_samples": None}
    path = candidates[0]
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return {"status": "fail", "reason": f"could not read {os.path.basename(path)}: {e}", "n_samples": None}
    required_cols = {"timestamp_unix_ms", "pos_x", "pos_y", "pos_z", "quat_x", "quat_y", "quat_z", "quat_w"}
    missing = required_cols - set(df.columns)
    if missing:
        return {"status": "fail", "reason": f"{os.path.basename(path)} missing columns: {sorted(missing)}",
                "n_samples": len(df)}
    if len(df) == 0:
        return {"status": "fail", "reason": f"{os.path.basename(path)} is empty", "n_samples": 0}
    return {"status": "pass", "reason": f"{len(df)} head-pose samples found", "n_samples": len(df)}


def qc_session(session_dir):
    participant_id = _participant_id_from_dirname(session_dir)
    gaze = check_gaze(session_dir)
    eeg = check_eeg(participant_id) if participant_id else {"status": "fail", "reason": "could not parse participant id", "max_flatline": None}
    events = check_events(session_dir)
    head_pose = check_head_pose(session_dir)

    required_pass = [gaze["status"], events["status"]]  # eeg/head_pose may legitimately be not_available
    overall = "pass" if all(s == "pass" for s in required_pass) else "fail"

    return {
        "session_dir": os.path.basename(session_dir), "participant_id": participant_id,
        "gaze_status": gaze["status"], "gaze_detail": gaze["reason"],
        "eeg_status": eeg["status"], "eeg_detail": eeg["reason"],
        "events_status": events["status"], "events_detail": events["reason"],
        "head_pose_status": head_pose["status"], "head_pose_detail": head_pose["reason"],
        "overall": overall,
    }


def main():
    parser = argparse.ArgumentParser(description="Per-session QC check (Objective 3 prep).")
    parser.add_argument("--session", help="Path to a single session directory. If omitted, runs over every session in backend/raw_data/.")
    parser.add_argument("--out-csv", default="/Users/naman/Documents/MTP/backend/pipeline/session_qc_report.csv")
    args = parser.parse_args()

    if args.session:
        session_dirs = [args.session]
    else:
        session_dirs = sorted(glob.glob(f"{RAW_DATA_DIR}/session_*"))

    rows = []
    for d in session_dirs:
        r = qc_session(d)
        rows.append(r)
        print(f"{r['session_dir']:45s} gaze={r['gaze_status']:6s} eeg={r['eeg_status']:14s} "
              f"events={r['events_status']:6s} head_pose={r['head_pose_status']:6s} -> {r['overall']}")

    df = pd.DataFrame(rows)
    df.to_csv(args.out_csv, index=False)
    print(f"\nWrote {len(df)} session QC rows to {args.out_csv}")
    print(df["overall"].value_counts().to_string())
    print("\nPer-modality status counts:")
    for col in ("gaze_status", "eeg_status", "events_status", "head_pose_status"):
        print(f"  {col}:", df[col].value_counts().to_dict())


if __name__ == "__main__":
    main()
