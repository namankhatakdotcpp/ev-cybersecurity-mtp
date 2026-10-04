#!/usr/bin/env python3
"""
Phase 2 (D034+): real feature-extraction pipeline, generalizing the already-piloted
and validated logic (not a rewrite) across all 140 sessions:

  - Gaze: AOI-free fixation-cluster features (D025/D030-validated method, copied
    from backend/gaze/aoi_free_pilot.py's fixations_in_window/analyze_window, not
    the old AOI-anchored dwell/TTFF, which D021/D026/D030 closed off).
  - EEG: band power (delta/theta/alpha/beta) in low-motion windows, for the 67/140
    D019-qualified participants only. All other participants get eeg_missing=True
    and NaN feature columns - not zero-filled, not imputed (standing rule).
  - Behavioural: decision/outcome labels from game logs only (never gaze/EEG).

Output: one row per (participant, station) scenario-event, written to
backend/pipeline/feature_table.csv, with explicit *_missing boolean columns per
modality so downstream modeling can handle missingness honestly.
"""
import glob
import json
import math
import os
import re

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from scipy.signal import welch

RAW_DATA_DIR = "/Users/naman/Documents/MTP/backend/raw_data"
EEG_DECODED_DIR = "/Users/naman/Documents/MTP/backend/Muse/decoded"
CONTAMINATED_JSON = "/Users/naman/Documents/MTP/backend/rag_contaminated_sessions.json"
EEG_SUMMARY_CSV = "/Users/naman/Documents/MTP/backend/Muse/decoded/decode_summary_resynced.csv"
OUT_CSV = "/Users/naman/Documents/MTP/backend/pipeline/feature_table.csv"

VELOCITY_THRESHOLD_DEG_S = 30.0
MIN_FIXATION_MS = 100.0
DBSCAN_EPS = 0.08
DBSCAN_MIN_SAMPLES = 1

EEG_BANDS = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30)}
EEG_CHANNELS = ["EEG_TP9", "EEG_AF7", "EEG_AF8", "EEG_TP10"]
EEG_FS = 256.0
MOTION_LOW_PERCENTILE = 50  # "low-motion" = below the session's own median accel-magnitude


# ---------------------------------------------------------------------------
# Session discovery / ground-truth lookups
# ---------------------------------------------------------------------------

def _is_gaze_csv(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            header = f.readline()
        return "gaze_forward_x" in header
    except Exception:
        return False


def discover_sessions():
    sessions = []
    for d in sorted(glob.glob(f"{RAW_DATA_DIR}/session_*")):
        base = os.path.basename(d)
        # pid is the numeric participant-id token right after the date_time prefix;
        # a known glitched folder has extra trailing text after it (D013/D029) - take
        # just the leading digit group, not the whole remainder.
        m = re.match(r"session_\d+_\d+_(\d+)", base)
        if not m:
            continue
        pid = m.group(1)
        inter_files = glob.glob(f"{d}/interactions_*.csv")
        if not inter_files:
            continue
        gaze_files = [f for f in glob.glob(f"{d}/*.csv")
                      if not os.path.basename(f).startswith("interactions") and _is_gaze_csv(f)]
        n_inter_rows = sum(1 for _ in open(inter_files[0], encoding="utf-8", errors="ignore"))
        sessions.append({"session_dir": base, "participant_id": pid, "interactions_file": inter_files[0],
                          "gaze_file": gaze_files[0] if gaze_files else None, "n_inter_rows": n_inter_rows})

    # D019/D029 duplicate-folder issue: some participants have >1 session_* folder
    # (e.g. an aborted pre-check attempt plus the real played session). Keep only
    # the folder with the most interaction rows as canonical - do NOT borrow a gaze
    # file from a sibling duplicate folder, since its timestamps belong to a
    # DIFFERENT playthrough and would silently mismatch the real decision windows.
    by_pid = {}
    for s in sessions:
        by_pid.setdefault(s["participant_id"], []).append(s)
    canonical = []
    dropped = []
    for pid, group in by_pid.items():
        if len(group) == 1:
            canonical.append(group[0])
        else:
            group_sorted = sorted(group, key=lambda s: s["n_inter_rows"], reverse=True)
            canonical.append(group_sorted[0])
            dropped.extend(g["session_dir"] for g in group_sorted[1:])
    if dropped:
        print(f"Dropped {len(dropped)} duplicate-folder session(s) (kept the larger interaction log "
              f"per participant, consistent with D019's duplicate-folder finding): {dropped}")
    return sorted(canonical, key=lambda s: s["session_dir"])


def load_contaminated_sessions():
    d = json.load(open(CONTAMINATED_JSON))
    return {s["session_dir"] for s in d["sessions"]}


def load_eeg_qualified():
    rows = list(pd.read_csv(EEG_SUMMARY_CSV, dtype={"participant_id": str}).to_dict("records"))
    usable = {}
    for r in rows:
        pid = str(r["participant_id"])
        sync = r.get("best_sync")
        eeg_samples = float(r.get("eeg_samples") or 0)
        try:
            flat = json.loads(str(r["eeg_flatline_fraction_per_channel"]).replace('""', '"'))
            max_flat = max(flat.values()) if flat else 0.0
        except Exception:
            max_flat = 0.0
        gap_total = float(r.get("eeg_gap_total_s") or 0)
        duration = float(r.get("eeg_duration_s") or 0)
        gap_frac = gap_total / duration if duration else 0.0
        ok = (sync == "overlap_confirmed") and eeg_samples > 0 and max_flat < 0.15 and gap_frac < 0.5
        if ok:
            best_dir = r.get("best_session_dir") or r.get("session_dir")
            usable[pid] = {"session_dir": best_dir}
    return usable


# ---------------------------------------------------------------------------
# Behavioural: decision windows + outcome labels (game logs only)
# ---------------------------------------------------------------------------

def build_station_events(inter_path):
    """Returns a list of dicts, one per station/trial, each with the decision
    window [start,end), the outcome label, and behavioural fields - all derived
    from logged events only (Reached/StationGenerated/charging/disabled_charging/
    driving/assistant_chat), never from gaze or EEG."""
    df = pd.read_csv(inter_path, dtype=str, keep_default_na=False)
    df["ts"] = pd.to_numeric(df["timestamp_unix_ms"], errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)

    events = []
    for _, row in df.iterrows():
        page = (row.get("page") or "").strip().lower()
        payload_raw = row.get("payload_json") or ""
        try:
            payload = json.loads(payload_raw) if payload_raw else {}
        except Exception:
            payload = {}
        events.append({"ts": row["ts"], "page": page, "payload": payload})

    stations = []
    reached_ts, reached_trial, points_before = None, None, None
    ai_help_used = False
    for e in events:
        payload = e["payload"]
        if payload.get("route") == "Flowgraph" and payload.get("Message") == "Reached":
            # close out a previous station with no explicit end (shouldn't normally happen)
            reached_ts = e["ts"]
            try:
                reached_trial = int(payload.get("Station"))
            except Exception:
                reached_trial = None
            points_before = None
            ai_help_used = False
        elif e["page"] == "assistant_chat" and reached_ts is not None:
            ai_help_used = True
        elif e["page"] == "station" and reached_ts is not None and points_before is None:
            try:
                points_before = float(payload.get("points"))
            except Exception:
                points_before = None
        elif e["page"] in ("charging", "disabled_charging") and reached_ts is not None:
            try:
                kiosk_used = int(payload.get("kiosk_used"))
            except Exception:
                kiosk_used = None
            stations.append({
                "trial": reached_trial, "window_start_ms": reached_ts, "window_end_ms": e["ts"],
                "decision": "charge", "kiosk_used": kiosk_used,
                "kiosk_attack": payload.get("kiosk_attack"),
                "charge_amount": payload.get("charge_amount"),
                "points_before": points_before, "points_after": payload.get("points"),
                "ai_help_used": ai_help_used, "end_page": e["page"],
            })
            reached_ts = None
        elif e["page"] == "driving" and reached_ts is not None:
            # reached a station, then drove away with no charging/disabled_charging event -> skip
            stations.append({
                "trial": reached_trial, "window_start_ms": reached_ts, "window_end_ms": e["ts"],
                "decision": "skip", "kiosk_used": None, "kiosk_attack": None,
                "charge_amount": None, "points_before": points_before, "points_after": payload.get("points"),
                "ai_help_used": ai_help_used, "end_page": e["page"],
            })
            reached_ts = None

    for s in stations:
        try:
            pb = float(s["points_before"]) if s["points_before"] is not None else None
            pa = float(s["points_after"]) if s["points_after"] is not None else None
            s["points_lost"] = (pb - pa) if (pb is not None and pa is not None) else None
        except Exception:
            s["points_lost"] = None
        s["window_duration_s"] = (s["window_end_ms"] - s["window_start_ms"]) / 1000.0
    return stations


# ---------------------------------------------------------------------------
# Gaze: AOI-free fixation/cluster features (copied method, D025/D030)
# ---------------------------------------------------------------------------

def load_gaze(gaze_path):
    cols = ["relative_to_unix_epoch_timestamp", "status", "stability",
            "gaze_forward_x", "gaze_forward_y", "gaze_forward_z"]
    df = pd.read_csv(gaze_path, usecols=lambda c: c in cols)
    if not all(c in df.columns for c in cols):
        return None
    df["t_epoch_ms"] = df["relative_to_unix_epoch_timestamp"] / 1e6
    valid = (df["status"] == 2) & (df["stability"] > 0)
    return df[valid].sort_values("t_epoch_ms").reset_index(drop=True)


def fixations_in_window(gaze_df, start_ms, end_ms):
    seg = gaze_df[(gaze_df["t_epoch_ms"] >= start_ms) & (gaze_df["t_epoch_ms"] <= end_ms)].reset_index(drop=True)
    if len(seg) < 3:
        return []
    t = seg["t_epoch_ms"].to_numpy() / 1000.0
    v = seg[["gaze_forward_x", "gaze_forward_y", "gaze_forward_z"]].to_numpy(dtype=np.float64)
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    v = v / norms
    dt = np.diff(t)
    dot = np.clip(np.sum(v[:-1] * v[1:], axis=1), -1.0, 1.0)
    ang_deg = np.degrees(np.arccos(dot))
    with np.errstate(divide="ignore", invalid="ignore"):
        ang_vel = np.where(dt > 0, ang_deg / dt, 0.0)
    is_saccade = (ang_vel > VELOCITY_THRESHOLD_DEG_S) | (dt > 0.1)
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
                    fixations.append({"duration_ms": dur_ms, "mean_dir": mean_v})
            run_start = i
    return fixations


def gaze_features(fixations):
    if len(fixations) == 0:
        return None
    dirs = np.array([f["mean_dir"] for f in fixations])
    if len(fixations) == 1:
        cluster_ids = np.array([0])
    else:
        db = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES, metric="euclidean")
        cluster_ids = db.fit_predict(dirs)
        cluster_ids = np.where(cluster_ids < 0, cluster_ids.max() + 1, cluster_ids)
    n_clusters = len(set(cluster_ids))
    transitions = int(np.sum(np.diff(cluster_ids) != 0))
    durs = np.array([f["duration_ms"] for f in fixations], dtype=np.float64)
    weighted = (dirs * durs[:, None]).sum(axis=0) / durs.sum()
    dispersion = 1.0 - np.linalg.norm(weighted)
    occ = {}
    for cid, d in zip(cluster_ids, durs):
        occ[cid] = occ.get(cid, 0.0) + d
    total = sum(occ.values())
    probs = [v / total for v in occ.values()]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    return {
        "gaze_n_fixations": len(fixations), "gaze_n_clusters": n_clusters,
        "gaze_n_transitions": transitions,
        "gaze_transitions_per_fixation": round(transitions / max(len(fixations) - 1, 1), 4),
        "gaze_dispersion": round(float(dispersion), 4),
        "gaze_entropy_bits": round(entropy, 4),
    }


# ---------------------------------------------------------------------------
# EEG: band power in low-motion windows (67/140-qualified participants only)
# ---------------------------------------------------------------------------

_eeg_cache = {}


def load_eeg_pair(pid):
    if pid in _eeg_cache:
        return _eeg_cache[pid]
    eeg_path = f"{EEG_DECODED_DIR}/{pid}/{pid}_eeg_decoded.csv"
    acc_path = f"{EEG_DECODED_DIR}/{pid}/{pid}_accgyro_decoded.csv"
    if not (os.path.exists(eeg_path) and os.path.exists(acc_path)):
        _eeg_cache[pid] = None
        return None
    eeg = pd.read_csv(eeg_path, usecols=["timestamp_utc"] + EEG_CHANNELS)
    # pandas parses these ISO timestamps at microsecond precision (datetime64[us]),
    # so .astype("int64") yields MICROSECONDS since epoch, not nanoseconds - divide
    # by 1e3 (us->ms), not 1e6, to line up with the ms-scale interaction timestamps.
    eeg["t_epoch_ms"] = pd.to_datetime(eeg["timestamp_utc"]).astype("int64") / 1e3
    acc = pd.read_csv(acc_path, usecols=["timestamp_utc", "ACC_X", "ACC_Y", "ACC_Z"])
    acc["t_epoch_ms"] = pd.to_datetime(acc["timestamp_utc"]).astype("int64") / 1e3
    acc["mag"] = np.sqrt(acc["ACC_X"] ** 2 + acc["ACC_Y"] ** 2 + acc["ACC_Z"] ** 2)
    threshold = acc["mag"].median()
    _eeg_cache[pid] = (eeg, acc, threshold)
    return _eeg_cache[pid]


def eeg_band_power_in_window(pid, start_ms, end_ms):
    pair = load_eeg_pair(pid)
    if pair is None:
        return None
    eeg, acc, motion_threshold = pair
    eeg_seg = eeg[(eeg["t_epoch_ms"] >= start_ms) & (eeg["t_epoch_ms"] <= end_ms)]
    if len(eeg_seg) < int(EEG_FS * 2):  # need >=2s for a meaningful PSD
        return None
    acc_seg = acc[(acc["t_epoch_ms"] >= start_ms) & (acc["t_epoch_ms"] <= end_ms)]
    low_motion_mask = pd.Series(True, index=eeg_seg.index)
    if len(acc_seg) > 0:
        acc_low = acc_seg[acc_seg["mag"] <= motion_threshold]
        low_intervals = list(zip(acc_low["t_epoch_ms"], acc_low["t_epoch_ms"] + 50))
        if low_intervals:
            mask = np.zeros(len(eeg_seg), dtype=bool)
            eeg_t = eeg_seg["t_epoch_ms"].to_numpy()
            for lo, hi in low_intervals:
                mask |= (eeg_t >= lo) & (eeg_t < hi)
            if mask.sum() >= EEG_FS * 2:
                low_motion_mask = pd.Series(mask, index=eeg_seg.index)

    seg = eeg_seg[low_motion_mask.values] if low_motion_mask.sum() >= EEG_FS * 2 else eeg_seg
    feats = {}
    for ch in EEG_CHANNELS:
        x = seg[ch].to_numpy(dtype=np.float64)
        x = x - x.mean()
        freqs, psd = welch(x, fs=EEG_FS, nperseg=min(256, len(x)))
        total_power = np.trapezoid(psd, freqs) or 1.0
        for band, (lo, hi) in EEG_BANDS.items():
            band_mask = (freqs >= lo) & (freqs <= hi)
            band_power = np.trapezoid(psd[band_mask], freqs[band_mask])
            feats[f"eeg_{ch.replace('EEG_', '').lower()}_{band}_rel"] = round(float(band_power / total_power), 5)
    feats["eeg_low_motion_fraction"] = round(float(low_motion_mask.mean()), 4)
    return feats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    sessions = discover_sessions()
    contaminated = load_contaminated_sessions()
    eeg_qualified = load_eeg_qualified()
    print(f"Discovered {len(sessions)} sessions; {len(eeg_qualified)} EEG-qualified participants; "
          f"{len(contaminated)} RAG-contaminated sessions")

    rows = []
    for s in sessions:
        pid = s["participant_id"]
        session_dir = s["session_dir"]
        try:
            stations = build_station_events(s["interactions_file"])
        except Exception as e:
            print(f"  [{pid}] interactions parse FAILED: {e}")
            continue

        gaze_df = None
        if s["gaze_file"]:
            try:
                gaze_df = load_gaze(s["gaze_file"])
            except Exception as e:
                print(f"  [{pid}] gaze load FAILED: {e}")

        eeg_pid_for_lookup = pid if pid in eeg_qualified else None

        for st in stations:
            row = {
                "participant_id": pid, "session_dir": session_dir, "trial": st["trial"],
                "decision": st["decision"], "kiosk_used": st["kiosk_used"], "kiosk_attack": st["kiosk_attack"],
                "charge_amount": st["charge_amount"], "points_lost": st["points_lost"],
                "ai_help_used": st["ai_help_used"], "window_duration_s": st["window_duration_s"],
                "rag_contaminated": session_dir in contaminated,
            }

            if gaze_df is not None and len(gaze_df) > 0:
                fixations = fixations_in_window(gaze_df, st["window_start_ms"], st["window_end_ms"])
                gf = gaze_features(fixations)
                row["gaze_missing"] = gf is None
                if gf:
                    row.update(gf)
            else:
                row["gaze_missing"] = True

            if eeg_pid_for_lookup:
                ef = eeg_band_power_in_window(pid, st["window_start_ms"], st["window_end_ms"])
                row["eeg_missing"] = ef is None
                if ef:
                    row.update(ef)
            else:
                row["eeg_missing"] = True

            rows.append(row)

        print(f"  [{pid}] {len(stations)} station-events, gaze_available={gaze_df is not None}, "
              f"eeg_qualified={bool(eeg_pid_for_lookup)}")

    out = pd.DataFrame(rows)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {len(out)} rows ({out['participant_id'].nunique()} participants) to {OUT_CSV}")
    print("\nMissingness summary:")
    print("  gaze_missing:", out["gaze_missing"].sum(), "/", len(out))
    print("  eeg_missing:", out["eeg_missing"].sum(), "/", len(out))
    print("  decision counts:", out["decision"].value_counts().to_dict())


if __name__ == "__main__":
    main()
