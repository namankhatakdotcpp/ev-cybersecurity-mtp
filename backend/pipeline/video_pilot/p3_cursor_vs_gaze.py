import cv2, numpy as np, pandas as pd, os, itertools, json
W, H = 2048, 1536
BASE = r"D:\MTP_scratch\video_pilot\win"
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from backend.pipeline.paths import RAW, VARJO, SESSION_MAP, pilot_sessions
R = str(RAW)
PS = pilot_sessions()
S = {"021": (PS["021"]["session"], 37.0, 62.055), "041": (PS["041"]["session"], 209.5, 234.444), "100": (PS["100"]["session"], 355.8, 380.766)}


def find_cursor(img):
    b, g, r = [img[:, :, i].astype(int) for i in range(3)]
    m = ((r > 190) & (g > 40) & (g < 130) & (b < 60) & (r - g > 100)).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    best = None
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 120 < a < 2500 and 15 < w < 80 and 15 < h < 80 and a / (w * h) > 0.3:
            if best is None or a > best[2]:
                best = (x, y, a, w, h)
    if best is None:
        return None
    x, y, a, w, h = best
    # tip = top-left-most pixel of the blob
    ys, xs = np.where(lab[y:y + h, x:x + w] == [i for i in range(1, n) if st[i][0] == x and st[i][1] == y][0])
    k = np.argmin(xs + ys)
    return float(xs[k] + x), float(ys[k] + y)


rows = []
for pid, (sess, t0, click) in S.items():
    g = pd.read_csv(os.path.join(R, sess, pid + ".csv"), usecols=["relative_to_video_first_frame_timestamp", "status", "stability",
                    "gaze_projected_to_left_view_x", "gaze_projected_to_left_view_y", "gaze_projected_to_right_view_x", "gaze_projected_to_right_view_y", "focus_distance"])
    g = g.apply(pd.to_numeric, errors="coerce")
    g = g.dropna(subset=["relative_to_video_first_frame_timestamp"]).reset_index(drop=True)
    gt = g.relative_to_video_first_frame_timestamp.values / 1e9
    for k in range(54):
        t = t0 + 0.5 * k
        img = cv2.imread(os.path.join(BASE, pid, "f_%03d.png" % (k + 1)))
        c = find_cursor(img)
        sel = (np.abs(gt - t) < 0.1) & (g.status.values == 2) & (g.stability.values > 0)
        if c is None or sel.sum() < 5:
            rows.append(dict(pid=pid, t=t, dt_click=t - click, cx=np.nan, cy=np.nan)); continue
        d = g[sel]
        rows.append(dict(pid=pid, t=t, dt_click=t - click, cx=c[0], cy=c[1], n=int(sel.sum()),
                         lx=d.gaze_projected_to_left_view_x.median(), ly=d.gaze_projected_to_left_view_y.median(),
                         rx=d.gaze_projected_to_right_view_x.median(), ry=d.gaze_projected_to_right_view_y.median(),
                         fd=d.focus_distance.median()))
D = pd.DataFrame(rows)
D.to_csv(os.path.join(BASE, "cursor_gaze_pairs.csv"), index=False)
print(D.groupby("pid").apply(lambda x: pd.Series(dict(frames=len(x), cursor_found=int(x.cx.notna().sum())))))
V = D.dropna(subset=["cx", "lx"])
print(V.groupby("pid")[["cx", "cy", "lx", "ly", "rx", "ry", "fd"]].agg(["min", "max"]).round(3).T.to_string())

# 1) literal conventions -> pixel error vs cursor
print("\n== literal conventions (median px error vs cursor; image 2048x1536)")
def conv(x, y, flipx, flipy, signed):
    u = (x + 1) / 2 if signed else x
    v = (y + 1) / 2 if signed else y
    if flipx: u = 1 - u
    if flipy: v = 1 - v
    return u * W, v * H
for eye in ["l", "r"]:
    for flipx, flipy in itertools.product([0, 1], [0, 1]):
        e = []
        for _, r in V.iterrows():
            px, py = conv(r[eye + "x"], r[eye + "y"], flipx, flipy, True)
            e.append(np.hypot(px - r.cx, py - r.cy))
        print(f" eye={eye} flipx={flipx} flipy={flipy}: median err {np.median(e):.0f}px  (frame diag {np.hypot(W,H):.0f}); baseline const-at-median-cursor: {np.median(np.hypot(V.cx-V.cx.median(), V.cy-V.cy.median())):.0f}px")

# 2) affine fit on 021 -> test on 041, 100 (no refit), per eye and mean-of-eyes
def feats(df, eye):
    if eye == "m":
        return np.c_[(df.lx + df.rx) / 2, (df.ly + df.ry) / 2, np.ones(len(df))]
    return np.c_[df[eye + "x"], df[eye + "y"], np.ones(len(df))]
print("\n== affine fit on 021, held-out test (no refit)")
tr = V[V.pid == "021"]
for eye in ["l", "r", "m"]:
    A = feats(tr, eye)
    cx, *_ = np.linalg.lstsq(A, tr.cx.values, rcond=None); cy, *_ = np.linalg.lstsq(A, tr.cy.values, rcond=None)
    ftr = np.hypot(A @ cx - tr.cx, A @ cy - tr.cy)
    out = f" eye={eye}: train(021) median {np.median(ftr):.0f}px;"
    for p in ["041", "100"]:
        te = V[V.pid == p]; B = feats(te, eye)
        er = np.hypot(B @ cx - te.cx, B @ cy - te.cy)
        base = np.hypot(te.cx - tr.cx.median(), te.cy - tr.cy.median())
        near = V[(V.pid == p) & (V.dt_click.between(-6, 1))]
        out += f" {p}: median {np.median(er):.0f}px (n={len(te)}; const-baseline {np.median(base):.0f}px; corr(x)={np.corrcoef(B@cx, te.cx)[0,1]:.2f});"
    print(out, " coef x:", cx.round(1), "y:", cy.round(1))
# 3) left vs right disagreement in px under the signed-normalized x scale
dis = ((V.lx - V.rx).abs() / 2 * W)
print("\n== L/R x disagreement (px if signed-normalized): median %.0f, p90 %.0f ; y: median %.0f" % (dis.median(), dis.quantile(.9), ((V.ly - V.ry).abs() / 2 * H).median()))
print("focus_distance median by pid:", V.groupby("pid").fd.median().round(2).to_dict())
