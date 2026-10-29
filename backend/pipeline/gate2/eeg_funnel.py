"""Read-only EEG cohort funnel (no inclusion rule is defined or changed here).

The EEG screening rule is the one already applied by `build_feature_table.load_eeg_qualified` (D019, D034); it is repeated
below only so this script runs without that module's machine-specific paths. The funnel and the per-participant table are
printed as Markdown for `docs/audit/EEG_COHORT_FUNNEL.md`.

  python -m backend.pipeline.gate2.eeg_funnel
"""
import json
import os

import pandas as pd


from .matched import build_matched, load_gate4

CHECK = ("012", "053", "054", "058")


def screened(row):
    """Same conditions as build_feature_table.load_eeg_qualified."""
    try:
        flat = json.loads(str(row["eeg_flatline_fraction_per_channel"]).replace('""', '"'))
        max_flat = max(flat.values()) if flat else 0.0
    except Exception:
        max_flat = 0.0
    dur = float(row.get("eeg_duration_s") or 0)
    gap = float(row.get("eeg_gap_total_s") or 0) / dur if dur else 0.0
    return (row.get("best_sync") == "overlap_confirmed" and float(row.get("eeg_samples") or 0) > 0
            and max_flat < 0.15 and gap < 0.5)


def stage_reason(row, in_ft, n_ft_eeg, in_primary, in_matched):
    if row["status"] != "decoded":
        return "not decoded"
    if row.get("best_sync") != "overlap_confirmed":
        return "session timestamps not confirmed (%s)" % row.get("best_sync")
    if not screened(row):
        return "failed quality screen"
    if not in_ft:
        return "no decision rows in the feature table"
    if n_ft_eeg == 0:
        return "no decision window with EEG"
    if not in_primary:
        return "no primary-set (T1) row"
    return "in matched set" if in_matched else "primary rows exist but none with EEG"


def _window_location(T, dec, qual):
    """Where the decision windows of screened participants fall relative to their EEG recording (UTC)."""
    d = dec.set_index("participant_id")
    out = {"with": 0, "after": 0, "inside": 0, "before": 0}
    for r in T[T["participant_id"].isin(qual)].itertuples():
        s, e = pd.Timestamp(d.loc[r.participant_id, "eeg_start_utc"]).value / 1e6, pd.Timestamp(d.loc[r.participant_id, "eeg_end_utc"]).value / 1e6
        if not r.eeg_missing:
            out["with"] += 1
        elif r.t_end_ms < s:
            out["before"] += 1
        elif r.t_start_ms > e:
            out["after"] += 1
        else:
            out["inside"] += 1
    return out


def main():
    cfg = load_gate4()
    paths = cfg["paths_resolved"]
    raw = paths["raw_data_dir"]
    dec = pd.read_csv(os.path.join(os.path.dirname(raw), "Muse", "decoded", "decode_summary_resynced.csv"), dtype=str)
    ft = pd.read_csv(paths["feature_table"], dtype={"participant_id": str})
    T, primary, matched = build_matched(cfg)
    T_all = T.merge(ft.assign(idx=ft.groupby("session_dir").cumcount())[["session_dir", "idx"]], on=["session_dir", "idx"])

    sess = {d.split("_")[-1] for d in os.listdir(raw) if d.startswith("session_")}
    ft_p = set(ft["participant_id"])
    n_rows = ft.groupby("participant_id").size()
    n_eeg = ft[~ft["eeg_missing"].astype(bool)].groupby("participant_id").size()
    prim_p = set(primary["participant_id"])
    match_p = set(matched["participant_id"])

    dec["decoded"] = dec["status"] == "decoded"
    dec["sync_ok"] = dec["best_sync"] == "overlap_confirmed"
    dec["screen_ok"] = dec.apply(screened, axis=1)
    qual = set(dec.loc[dec["screen_ok"], "participant_id"])
    with_any_window = {p for p in qual if p in ft_p}
    with_eeg_window = {p for p in qual if n_eeg.get(p, 0) > 0}
    primary_q = with_eeg_window & prim_p

    funnel = [
        ("Participants with a session folder in raw data", len(sess)),
        ("Participants in the feature table (any decision row)", len(ft_p)),
        ("Participants in the primary set (T1 rows with gaze)", len(prim_p)),
        ("EEG recordings found (decode summary rows)", len(dec)),
        ("Decoded (status decoded)", int(dec["decoded"].sum())),
        ("Session timestamps verified (best_sync = overlap_confirmed)", int(dec["sync_ok"].sum())),
        ("Quality-screened (D019 rule: verified, samples > 0, flatline < 0.15, gap share < 0.5)", len(qual)),
        ("... of those, with any decision row in the feature table", len(with_any_window)),
        ("... of those, with at least one decision window that has EEG", len(with_eeg_window)),
        ("... of those, with a primary-set (T1) row", len(primary_q)),
        ("Matched set (primary rows with EEG)", len(match_p)),
    ]
    print("| Stage | Participants |\n|---|---|")
    for k, v in funnel:
        print(f"| {k} | {v} |")
    print(f"\nMatched set rows: {len(matched)}; primary set rows: {len(primary)}; feature-table rows: {len(ft)}; "
          f"feature-table rows with EEG: {int((~ft['eeg_missing'].astype(bool)).sum())}")
    why = {p: stage_reason(dec[dec["participant_id"] == p].iloc[0], p in ft_p, int(n_eeg.get(p, 0)), p in prim_p, p in match_p)
           for p in sorted(qual - match_p)}
    print("\nScreened but not matched, by where each stops:")
    for reason in sorted(set(why.values())):
        print(f"- {reason}: {sum(1 for v in why.values() if v == reason)}")
    where = _window_location(T_all, dec, qual)
    print(f"\nDecision windows of screened participants, by position relative to the EEG recording "
          f"(rows with EEG: {where['with']}; without EEG: start after the recording ended {where['after']}, "
          f"inside the recording but no usable EEG {where['inside']}, before it started {where['before']})")
    print(f"Screened but not matched: {sorted(qual - match_p)}")
    print(f"Matched but not screened: {sorted(match_p - qual)}")
    print(f"Decoded but not verified: {sorted(set(dec.loc[dec['decoded'] & ~dec['sync_ok'], 'participant_id']))}")
    print(f"Verified but failed screen: {sorted(set(dec.loc[dec['sync_ok'] & ~dec['screen_ok'], 'participant_id']))}")

    print("\n| Participant | Decoded | Sync | Screen | Feature rows | Rows with EEG | Primary rows | Matched rows | Where it stops |\n|---|---|---|---|---|---|---|---|---|")
    ids = list(CHECK) + sorted((set(dec.loc[dec["decoded"] & ~dec["screen_ok"], "participant_id"]) | set(dec.loc[~dec["decoded"], "participant_id"])) - set(CHECK))
    for p in ids:
        r = dec[dec["participant_id"] == p]
        if r.empty:
            print(f"| {p} | no EEG recording | - | - | {n_rows.get(p, 0)} | {n_eeg.get(p, 0)} | {int((primary['participant_id'] == p).sum())} | 0 | no EEG recording |")
            continue
        r = r.iloc[0]
        print(f"| {p} | {r['status']} | {r['best_sync']} | {bool(r['screen_ok'])} | {n_rows.get(p, 0)} | {n_eeg.get(p, 0)} | "
              f"{int((primary['participant_id'] == p).sum())} | {int((matched['participant_id'] == p).sum())} | "
              f"{stage_reason(r, p in ft_p, int(n_eeg.get(p, 0)), p in prim_p, p in match_p)} |")


if __name__ == "__main__":
    main()
