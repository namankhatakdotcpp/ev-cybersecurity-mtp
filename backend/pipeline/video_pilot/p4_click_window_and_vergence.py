import pandas as pd, numpy as np, os
D = pd.read_csv(r"D:\MTP_scratch\video_pilot\win\cursor_gaze_pairs.csv", dtype={"pid": str}).dropna(subset=["cx", "lx"])
D["pid"] = D.pid.astype(str).str.zfill(3)
def F(df): return np.c_[(df.lx + df.rx) / 2, (df.ly + df.ry) / 2, np.ones(len(df))]
tr = D[D.pid == "021"]
A = F(tr); cx = np.linalg.lstsq(A, tr.cx, rcond=None)[0]; cy = np.linalg.lstsq(A, tr.cy, rcond=None)[0]
for lo, hi, lab in [(-30, 5, "all pre/post-click window"), (-1.0, 0.6, "click moment (-1.0..+0.6 s)"), (-6, -1, "approach (-6..-1 s)")]:
    for p in ["021", "041", "100"]:
        te = D[(D.pid == p) & D.dt_click.between(lo, hi)]
        if len(te) < 2: print(lab, p, "n<2"); continue
        er = np.hypot(F(te) @ cx - te.cx, F(te) @ cy - te.cy)
        base = np.hypot(te.cx - tr.cx.median(), te.cy - tr.cy.median())
        print(f"{lab:32s} {p} n={len(te):2d} fit-err median={np.median(er):4.0f}px  const-baseline={np.median(base):4.0f}px {'(TRAIN)' if p=='021' else '(held-out)'}")
# within-session correlation of gaze with cursor, per axis
for p, g in D.groupby("pid"):
    gx = (g.lx + g.rx) / 2; gy = (g.ly + g.ry) / 2
    print(p, "corr(gaze_x,cursor_x)=%.2f corr(gaze_y,cursor_y)=%.2f n=%d" % (np.corrcoef(gx, g.cx)[0, 1], np.corrcoef(gy, g.cy)[0, 1], len(g)))
# L/R offset vs focus_distance over the FULL gaze files
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from backend.pipeline.paths import RAW, VARJO, SESSION_MAP, pilot_sessions
R = str(RAW)
PS = pilot_sessions()
for pid, sess in [(k, PS[k]["session"]) for k in ("021", "041")]:
    g = pd.read_csv(os.path.join(R, sess, pid + ".csv"), usecols=["status", "stability", "focus_distance", "gaze_projected_to_left_view_x", "gaze_projected_to_right_view_x"]).apply(pd.to_numeric, errors="coerce").dropna()
    g = g[(g.status == 2) & (g.stability > 0)]
    d = g.gaze_projected_to_left_view_x - g.gaze_projected_to_right_view_x
    print(pid, "valid n=%d  L-R x: median %.3f  p5 %.3f  p95 %.3f ; focus_distance: min %.3f  median %.3f  frac==2.0: %.3f ; corr(L-R, focus_dist)=%.3f" % (len(g), d.median(), d.quantile(.05), d.quantile(.95), g.focus_distance.min(), g.focus_distance.median(), (g.focus_distance >= 1.999).mean(), np.corrcoef(d, g.focus_distance)[0, 1]))
