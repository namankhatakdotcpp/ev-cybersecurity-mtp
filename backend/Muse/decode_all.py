#!/usr/bin/env python3
"""
Batch-decode all MUSE raw packet files for the EV Charging VR project using OpenMuse.
Groups multi-part files per participant, decodes each group (EEG + ACCGYRO + OPTICS + BATTERY),
writes per-participant decoded CSVs with absolute wall-clock timestamps, computes QC metrics,
and cross-checks each participant's EEG wall-clock window against their raw_data/ session log.

Decodes each sensor type independently (not via decode_rawdata's all-or-nothing call) so that a
handful of malformed subpackets in one sensor stream (observed: truncated OPTICS packets near BLE
reconnects, wrong channel-count) cannot abort extraction of the other sensor types, EEG especially.
"""
import glob
import json
import os
import re
import sys
import traceback
from collections import defaultdict, Counter
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import OpenMuse.decode as omd

RAW_DIR = "/tmp/muse_raw"
OUT_DIR = "/Users/naman/Documents/MTP/backend/Muse/decoded"
RAW_DATA_DIR = "/Users/naman/Documents/MTP/backend/raw_data"
os.makedirs(OUT_DIR, exist_ok=True)

SENSOR_TYPES = ["EEG", "ACCGYRO", "OPTICS", "BATTERY", "Unknown"]


def safe_decode(messages):
    """Re-implementation of OpenMuse.decode.decode_rawdata with per-sensor-type isolation.
    Returns (result_dict, malformed_counts) where malformed_counts records how many
    subpackets were dropped per sensor type for having an off-modal `data` length."""
    all_subpackets = {k: [] for k in SENSOR_TYPES}
    for message in messages:
        parsed = omd.parse_message(message)
        for sensor_type, subpacket_list in parsed.items():
            all_subpackets[sensor_type].extend(subpacket_list)

    result = {}
    malformed = {}
    for sensor_type, subpackets in all_subpackets.items():
        if not subpackets:
            result[sensor_type] = pd.DataFrame()
            malformed[sensor_type] = 0
            continue

        # Robustness filter: drop subpackets whose decoded `data` length isn't the modal
        # length for this sensor type in this recording (truncated/corrupt packets).
        lengths = [len(sp["data"]) if hasattr(sp.get("data"), "__len__") else None for sp in subpackets]
        modal_len = Counter(lengths).most_common(1)[0][0]
        clean = [sp for sp, L in zip(subpackets, lengths) if L == modal_len]
        malformed[sensor_type] = len(subpackets) - len(clean)

        try:
            array, _, _, _, _ = omd.make_timestamps(clean)
        except Exception as e:
            print(f"    make_timestamps still failed for {sensor_type} after filtering: {e}")
            result[sensor_type] = pd.DataFrame()
            continue

        if array.size == 0:
            result[sensor_type] = pd.DataFrame()
            continue

        n_cols = array.shape[1]
        if sensor_type == "EEG":
            columns = ["time", *omd.select_eeg_channels(n_cols - 1)]
        elif sensor_type == "ACCGYRO":
            columns = ["time", *omd.ACCGYRO_CHANNELS]
        elif sensor_type == "OPTICS":
            columns = ["time", *omd.select_optics_channels(n_cols - 1)]
        elif sensor_type == "BATTERY":
            columns = ["time", "battery_percent"]
        else:
            columns = ["time"] + [f"ch_{i+1}" for i in range(n_cols - 1)]
        result[sensor_type] = pd.DataFrame(array, columns=columns)

    return result, malformed


raw_files = glob.glob(os.path.join(RAW_DIR, "**", "*_muse.txt"), recursive=True)
print(f"Found {len(raw_files)} raw files total")

pattern = re.compile(r"(?P<pid>\d+)(?:_(?P<part>\d+))?_muse\.txt$")
groups = defaultdict(list)
skipped = []
for fp in raw_files:
    base = os.path.basename(fp)
    m = pattern.match(base)
    if not m:
        skipped.append(base)
        continue
    pid = int(m.group("pid"))
    part = int(m.group("part")) if m.group("part") else 0
    groups[pid].append((part, fp))

print(f"Grouped into {len(groups)} participants; unmatched filenames: {skipped}")


def line_ts(ln):
    try:
        ts_str = ln.split("\t", 1)[0]
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        return None


def find_session_dir(pid_str):
    matches = glob.glob(os.path.join(RAW_DATA_DIR, f"session_*_{pid_str}"))
    return matches[0] if matches else None


def session_time_window(session_dir):
    csvs = glob.glob(os.path.join(session_dir, "interactions_*.csv"))
    if not csvs:
        return None, None
    try:
        df = pd.read_csv(csvs[0], usecols=["timestamp_iso"])
        ts = pd.to_datetime(df["timestamp_iso"], errors="coerce").dropna()
        if len(ts) == 0:
            return None, None
        return ts.min().to_pydatetime(), ts.max().to_pydatetime()
    except Exception as e:
        print(f"    (could not read interactions csv: {e})")
        return None, None


IST_OFFSET = timedelta(hours=5, minutes=30)
summary_rows = []

for pid in sorted(groups.keys()):
    parts = sorted(groups[pid], key=lambda x: x[0])
    pid_str = f"{pid:03d}"
    print(f"\n=== Participant {pid_str} ({len(parts)} file part(s)) ===")

    all_lines = []
    for part_num, fp in parts:
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                lines = [ln.rstrip("\n") for ln in f if ln.strip()]
        except Exception as e:
            print(f"  ERROR reading {fp}: {e}")
            continue
        all_lines.extend(lines)

    total_raw_lines = len(all_lines)
    row = {"participant_id": pid_str, "n_parts": len(parts), "total_raw_lines": total_raw_lines}

    if total_raw_lines == 0:
        row["status"] = "no_readable_lines"
        summary_rows.append(row)
        continue

    timed = [(line_ts(ln), ln) for ln in all_lines]
    timed = [(t, ln) for t, ln in timed if t is not None]
    row["unparseable_lines_dropped"] = total_raw_lines - len(timed)
    if not timed:
        row["status"] = "all_lines_unparseable"
        summary_rows.append(row)
        continue
    timed.sort(key=lambda x: x[0])
    sorted_lines = [ln for _, ln in timed]
    first_abs_ts = timed[0][0]

    try:
        decoded, malformed = safe_decode(sorted_lines)
    except Exception as e:
        print(f"  DECODE FAILED: {e}")
        traceback.print_exc()
        row["status"] = f"decode_error: {e}"
        summary_rows.append(row)
        continue

    pdir = os.path.join(OUT_DIR, pid_str)
    os.makedirs(pdir, exist_ok=True)
    row["status"] = "decoded"
    row["malformed_subpackets_dropped"] = json.dumps(malformed)

    for sensor_type, df in decoded.items():
        key = sensor_type.lower()
        if df is None or len(df) == 0:
            row[f"{key}_samples"] = 0
            continue
        n = len(df)
        row[f"{key}_samples"] = n
        row[f"{key}_channels"] = ",".join([c for c in df.columns if c != "time"])

        df = df.copy()
        df["timestamp_utc"] = [
            (first_abs_ts + timedelta(seconds=float(s))).isoformat() for s in df["time"]
        ]
        out_path = os.path.join(pdir, f"{pid_str}_{key}_decoded.csv")
        df.to_csv(out_path, index=False)

        if sensor_type == "EEG" and n > 1:
            t = df["time"].to_numpy(dtype=float)
            duration_s = float(t[-1] - t[0])
            row["eeg_duration_s"] = round(duration_s, 2)
            row["eeg_sample_rate_hz"] = round((n - 1) / duration_s, 2) if duration_s > 0 else None

            diffs = np.diff(t)
            if len(diffs) > 0 and np.any(diffs > 0):
                expected_dt = np.median(diffs[diffs > 0])
                gap_threshold = max(expected_dt * 20, 1.0)
                gap_mask = diffs > gap_threshold
                row["eeg_gap_count"] = int(np.sum(gap_mask))
                row["eeg_gap_total_s"] = round(float(np.sum(diffs[gap_mask])), 2)
            else:
                row["eeg_gap_count"] = None

            eeg_cols = [c for c in df.columns if c.startswith("EEG_")]
            flat_fracs = {}
            for col in eeg_cols:
                vals = df[col].to_numpy(dtype=float)
                if len(vals) > 10:
                    flat = np.sum(np.diff(vals) == 0) / (len(vals) - 1)
                    flat_fracs[col] = round(float(flat), 4)
            row["eeg_flatline_fraction_per_channel"] = json.dumps(flat_fracs)
            row["eeg_start_utc"] = first_abs_ts.isoformat()
            row["eeg_end_utc"] = (first_abs_ts + timedelta(seconds=duration_s)).isoformat()

    session_dir = find_session_dir(pid_str)
    if session_dir is None:
        row["session_dir"] = None
        row["sync_check"] = "no_matching_session_dir"
    else:
        row["session_dir"] = os.path.basename(session_dir)
        sess_start, sess_end = session_time_window(session_dir)
        if sess_start is None:
            row["sync_check"] = "session_has_no_readable_interactions_csv"
        elif "eeg_start_utc" not in row:
            row["sync_check"] = "no_eeg_samples_to_compare"
        else:
            eeg_start_ist = first_abs_ts + IST_OFFSET
            eeg_end_ist = eeg_start_ist + timedelta(seconds=row["eeg_duration_s"])
            overlap = (eeg_start_ist.replace(tzinfo=None) <= sess_end) and (eeg_end_ist.replace(tzinfo=None) >= sess_start)
            row["session_start_ist"] = sess_start.isoformat()
            row["session_end_ist"] = sess_end.isoformat()
            row["eeg_start_ist_est"] = eeg_start_ist.replace(tzinfo=None).isoformat()
            row["eeg_end_ist_est"] = eeg_end_ist.replace(tzinfo=None).isoformat()
            row["sync_check"] = "overlap_confirmed" if overlap else "NO_OVERLAP_MISMATCH"

    summary_rows.append(row)
    print(f"  status={row.get('status')} eeg_samples={row.get('eeg_samples')} "
          f"rate={row.get('eeg_sample_rate_hz')} gaps={row.get('eeg_gap_count')} "
          f"malformed={row.get('malformed_subpackets_dropped')} sync={row.get('sync_check')}")

summary_df = pd.DataFrame(summary_rows)
summary_path = os.path.join(OUT_DIR, "decode_summary.csv")
summary_df.to_csv(summary_path, index=False)
print(f"\n\nWrote summary for {len(summary_rows)} participants to {summary_path}")
n_ok = (summary_df["status"] == "decoded").sum() if "status" in summary_df else 0
print(f"Decoded OK: {n_ok} / {len(summary_df)}")
