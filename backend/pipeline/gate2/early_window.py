"""S2 (Protocol v1 section 2): features restricted to the first N seconds after `Reached`, so the window cannot
contain the keypad/confirm stage that usually comes later. Reuses the pipeline's own fixation and cluster code
(`build_feature_table.fixations_in_window` / `gaze_features`) unchanged; the decision-window duration is dropped."""
import glob
import json
import os

import numpy as np
import pandas as pd

from ..build_feature_table import fixations_in_window, gaze_features, load_gaze


def _assistant_times(inter_path):
    df = pd.read_csv(inter_path, dtype=str, keep_default_na=False)
    df["ts"] = pd.to_numeric(df["timestamp_unix_ms"], errors="coerce")
    df = df.dropna(subset=["ts"])
    return np.sort(df.loc[(df["page"].str.lower() == "assistant_chat") & df["channel"].isin(["ui", "parsed_json"]), "ts"].to_numpy(float))


def build_early_features(table, raw_dir, seconds=5.0, min_window_s=5.0):
    """Returns a DataFrame indexed like `table` (eligible-universe rows only) with early-window gaze features,
    `ai_help_early`, and an `early_ok` flag (window long enough and early gaze features computable)."""
    cols = ["gaze_n_fixations", "gaze_n_clusters", "gaze_n_transitions", "gaze_transitions_per_fixation", "gaze_dispersion", "gaze_entropy_bits"]
    out = pd.DataFrame(index=table.index, columns=cols + ["ai_help_early", "early_ok"], dtype=float)
    out["early_ok"] = False
    for sd, grp in table[table["eligible_universe"]].groupby("session_dir"):
        inter = glob.glob(os.path.join(raw_dir, sd, "interactions*.csv"))[0]
        at = _assistant_times(inter)
        gaze_df = None
        for f in glob.glob(os.path.join(raw_dir, sd, "*.csv")):
            if os.path.basename(f).startswith("interactions"):
                continue
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                    if "gaze_forward_x" not in fh.readline():
                        continue
                gaze_df = load_gaze(f)
                break
            except Exception:
                continue
        for ix, r in grp.iterrows():
            t0 = r["t_start_ms"]
            t1 = t0 + seconds * 1000.0
            out.loc[ix, "ai_help_early"] = float(bool(((at >= t0) & (at <= t1)).any()))
            if (r["t_end_ms"] - t0) / 1000.0 < min_window_s or gaze_df is None or len(gaze_df) == 0:
                continue
            gf = gaze_features(fixations_in_window(gaze_df, t0, t1))
            if gf is None:
                continue
            for c in cols:
                out.loc[ix, c] = gf[c]
            out.loc[ix, "early_ok"] = True
    out["early_ok"] = out["early_ok"].astype(bool)
    return out
