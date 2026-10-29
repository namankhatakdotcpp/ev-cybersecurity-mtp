"""Gate 4 selection-bias report: who has usable EEG, and why do other rows lack it? Compares the matched EEG set with
the other primary rows and participants on variables that are legitimately available (not outcome-driven selection),
and decomposes EEG availability for the participants whose recordings were synchronised with their session.

Outputs a dict (stored in the registry) and a Markdown file generated from it."""
import json
import os

import numpy as np
import pandas as pd
from scipy import stats

from .build_t1_table import count_valid_gaze_samples


def smd(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    s = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return float((a.mean() - b.mean()) / s) if s > 0 else 0.0


def cluster_boot_smd(df, var, flag, B, seed):
    rng = np.random.default_rng(seed)
    A = {p: g[var].to_numpy(float) for p, g in df[df[flag]].groupby("participant_id")}
    O = {p: g[var].to_numpy(float) for p, g in df[~df[flag]].groupby("participant_id")}
    ka, ko = list(A), list(O)
    out = []
    for _ in range(B):
        a = np.concatenate([A[ka[i]] for i in rng.integers(0, len(ka), len(ka))])
        o = np.concatenate([O[ko[i]] for i in rng.integers(0, len(ko), len(ko))])
        out.append(smd(a, o))
    return [float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975))]


def bh(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        run = min(run, p[i] * m / (rank + 1))
        adj[i] = run
    return adj


def coverage_analysis(T, muse_dir):
    ds = pd.read_csv(os.path.join(muse_dir, "decoded", "decode_summary_resynced.csv"), dtype={"participant_id": str})
    q = ds[ds["best_sync"] == "overlap_confirmed"].copy()
    q["start"] = pd.to_datetime(q["eeg_start_utc"], utc=True)
    q["end"] = pd.to_datetime(q["eeg_end_utc"], utc=True)
    q = q.set_index("participant_id")
    rows = T[T["participant_id"].isin(q.index)].copy()
    w0 = pd.to_datetime(rows["t_start_ms"], unit="ms", utc=True).values
    w1 = pd.to_datetime(rows["t_end_ms"], unit="ms", utc=True).values
    s, e = q.loc[rows["participant_id"], "start"].values, q.loc[rows["participant_id"], "end"].values
    rows["reason"] = np.select([w1 < s, w0 > e, (w0 < s) | (w1 > e)], ["window before EEG start", "window after EEG end", "window partly outside EEG span"],
                               "inside EEG span")
    rows["eeg_usable"] = ~rows["eeg_missing"]
    ct = pd.crosstab(rows["reason"], rows["eeg_usable"])
    # session-link integrity
    canon = T.drop_duplicates("participant_id").set_index("participant_id")["session_dir"]
    mism = [p for p in q.index if p in canon.index and q.loc[p, "best_session_dir"] != canon[p]]
    # trial position of unusable-after-end rows vs usable rows (qualified participants only)
    return dict(n_participants=int(rows["participant_id"].nunique()), n_rows=len(rows), crosstab={r: {str(c): int(v) for c, v in ct.loc[r].items()} for r in ct.index},
                share_after_eeg_end=float((rows["reason"] == "window after EEG end").mean()),
                median_trial_usable=float(rows.loc[rows["eeg_usable"], "trial_index"].median()),
                median_trial_after_end=float(rows.loc[rows["reason"] == "window after EEG end", "trial_index"].median()),
                session_link_mismatches=len(mism))


def run(cfg, T_all, primary, matched):
    raw = cfg["paths_resolved"]["raw_data_dir"]
    sb = cfg["g4"]["selection_bias"]
    P = primary.copy()
    P["matched"] = ~P["eeg_missing"]
    vc = count_valid_gaze_samples(T_all, raw)
    P["gaze_valid_rate"] = vc.loc[T_all.index[T_all["eligible_primary"]]].to_numpy() / ((P["t_end_ms"] - P["t_start_ms"]) / 1000.0)
    out = dict(counts=dict(primary_rows=len(P), primary_participants=int(P.participant_id.nunique()), matched_rows=int(P.matched.sum()),
                           matched_participants=int(P[P.matched].participant_id.nunique()),
                           other_rows=int((~P.matched).sum()), other_participants=int(P[~P.matched].participant_id.nunique()),
                           participants_in_both=int(len(set(P[P.matched].participant_id) & set(P[~P.matched].participant_id)))))
    # ---- row level (cluster-bootstrap CI for the standardised mean difference)
    rows = []
    for v in sb["row_level"]:
        a, b = P.loc[P.matched, v].astype(float), P.loc[~P.matched, v].astype(float)
        rows.append(dict(variable=v, matched_mean=float(a.mean()), other_mean=float(b.mean()), smd=smd(a, b),
                         smd_ci=cluster_boot_smd(P.assign(**{v: P[v].astype(float)}), v, "matched", 1000, 5151)))
    rows.append(dict(variable="gaze_valid_rate (valid samples per second in the window)", matched_mean=float(P.loc[P.matched, "gaze_valid_rate"].mean()),
                     other_mean=float(P.loc[~P.matched, "gaze_valid_rate"].mean()), smd=smd(P.loc[P.matched, "gaze_valid_rate"], P.loc[~P.matched, "gaze_valid_rate"]),
                     smd_ci=cluster_boot_smd(P, "gaze_valid_rate", "matched", 1000, 5152)))
    out["row_level"] = rows
    # ---- participant level
    pp = P.groupby("participant_id").agg(n_rows=("y", "size"), event_rate=("y", "mean"), incident_mode=("incident_mode", "first"), period=("period", "first"),
                                          gaze_valid_rate=("gaze_valid_rate", "mean"), matched=("matched", "max"), session_dir=("session_dir", "first"))
    # a participant counts as matched if any of their primary rows has usable EEG
    demo = []
    for p, r in pp.iterrows():
        f = os.path.join(raw, r["session_dir"], "demographics.json")
        d = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
        demo.append({k: d.get(k) for k in sb["demographics"]})
    pp = pp.join(pd.DataFrame(demo, index=pp.index))
    pp["age"] = pd.to_numeric(pp["age"], errors="coerce")
    tests = []
    for v in ["n_rows", "event_rate", "incident_mode", "gaze_valid_rate", "age"]:
        a, b = pp.loc[pp.matched, v].dropna(), pp.loc[~pp.matched, v].dropna()
        tests.append(dict(variable=v, kind="numeric", matched=float(a.mean()), other=float(b.mean()), smd=smd(a, b), p=float(stats.mannwhitneyu(a, b).pvalue), n=[int(len(a)), int(len(b))]))
    for v in ["period"] + [d for d in sb["demographics"] if d != "age"]:
        ct = pd.crosstab(pp[v].fillna("missing"), pp["matched"])
        if ct.shape[0] < 2 or ct.shape[1] < 2:
            continue
        chi2, p, _, _ = stats.chi2_contingency(ct)
        V = float(np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1))))
        shares = (ct / ct.sum()).round(3)
        tests.append(dict(variable=v, kind="categorical", cramers_v=V, p=float(p), shares_matched={str(k): float(x) for k, x in shares[True].items()} if True in shares else {},
                          shares_other={str(k): float(x) for k, x in shares[False].items()} if False in shares else {}, n=[int(pp.matched.sum()), int((~pp.matched).sum())]))
    adj = bh([t["p"] for t in tests])
    for t, q_ in zip(tests, adj):
        t["fdr_bh"] = float(q_)
    out["participant_level"] = tests
    out["participant_counts"] = dict(matched=int(pp.matched.sum()), other=int((~pp.matched).sum()))
    # ---- outcome and exposure in the matched rows (the claim about generalisability)
    out["outcome"] = dict(event_rate_matched=float(P.loc[P.matched, "y"].mean()), event_rate_other=float(P.loc[~P.matched, "y"].mean()))
    out["coverage"] = coverage_analysis(T_all, os.path.join(os.path.dirname(raw), "Muse"))
    return out


def to_markdown(out):
    c = out["counts"]
    md = ["# Gate 4 selection-bias report (generated; do not edit by hand)", "",
          f"Primary T1 rows with gaze: {c['primary_rows']} rows, {c['primary_participants']} participants. Matched (usable EEG): {c['matched_rows']} rows, "
          f"{c['matched_participants']} participants. Other: {c['other_rows']} rows, {c['other_participants']} participants. "
          f"{c['participants_in_both']} participants contribute rows to both groups (their early stations have EEG, later ones do not).", "",
          "## Why rows lack EEG (participants whose recording was confirmed to overlap their session)", ""]
    cov = out["coverage"]
    md.append(f"{cov['n_participants']} participants, {cov['n_rows']} rows. Link between EEG recording and canonical session folder: {cov['session_link_mismatches']} mismatches.")
    md.append("\n| Window position relative to the EEG recording | EEG unusable | EEG usable |\n|---|---|---|")
    for r, d in cov["crosstab"].items():
        md.append(f"| {r} | {d.get('False', 0)} | {d.get('True', 0)} |")
    md.append(f"\nShare of rows whose decision window falls after the recording ended: {cov['share_after_eeg_end']:.1%}. Median trial index of rows with usable EEG "
              f"{cov['median_trial_usable']:.0f} vs {cov['median_trial_after_end']:.0f} for rows after the recording ended.")
    md += ["", "## Row level: matched vs other primary rows (standardised mean difference, participant-cluster bootstrap 95% CI)", "",
           "| Variable | Matched mean | Other mean | SMD [95% CI] |", "|---|---|---|---|"]
    for r in out["row_level"]:
        md.append(f"| {r['variable']} | {r['matched_mean']:.3f} | {r['other_mean']:.3f} | {r['smd']:.2f} [{r['smd_ci'][0]:.2f}, {r['smd_ci'][1]:.2f}] |")
    md += ["", f"## Participant level ({out['participant_counts']['matched']} matched vs {out['participant_counts']['other']} other primary participants; exploratory, Benjamini-Hochberg across all tests)", "",
           "| Variable | Matched | Other | Effect size | p | FDR |", "|---|---|---|---|---|---|"]
    for t in out["participant_level"]:
        if t["kind"] == "numeric":
            md.append(f"| {t['variable']} | {t['matched']:.3f} | {t['other']:.3f} | SMD {t['smd']:.2f} | {t['p']:.3f} | {t['fdr_bh']:.3f} |")
        else:
            top = max(t["shares_matched"], key=lambda k: t["shares_matched"][k] if k in t["shares_matched"] else 0)
            md.append(f"| {t['variable']} (largest matched category: {top}) | {t['shares_matched'].get(top, 0):.2f} | {t['shares_other'].get(top, 0):.2f} | Cramer's V {t['cramers_v']:.2f} | {t['p']:.3f} | {t['fdr_bh']:.3f} |")
    o = out["outcome"]
    md += ["", f"Event rate: matched rows {o['event_rate_matched']:.3f}, other rows {o['event_rate_other']:.3f}."]
    return "\n".join(md) + "\n"
