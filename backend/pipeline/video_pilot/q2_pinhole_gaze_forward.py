"""Pinhole test: gaze_forward (head-local) -> video pixels, u=cx+sx*f*gx/gz, v=cy+sy*f*gy/gz.
Calibrate on 021 only; test on 041/100 without refit. Extracts <=24 new frames (click-time)."""
import cv2, numpy as np, pandas as pd, os, subprocess, itertools, json, sys
W, H = 2048, 1536
FFMPEG = "ffmpeg"
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from backend.pipeline.paths import RAW, VARJO, SESSION_MAP, pilot_sessions
V = str(VARJO)
R = str(RAW)
PS = pilot_sessions()
SC = r"D:\MTP_scratch\video_pilot"
INFO = {"021": (PS["021"]["session"], PS["021"]["video"], 1, 37.0),
        "041": (PS["041"]["session"], PS["041"]["video"], 2, 209.5),
        "100": (PS["100"]["session"], PS["100"]["video"], 1, 355.8)}
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# --- reuse localisation + pointer code verbatim from D061's script (functions only)
src = open(pathlib.Path(__file__).with_name("p5_panel_localisation_hit_rate.py"), encoding="utf-8").read()
ns = {"cv2": cv2, "np": np, "pd": pd, "os": os, "itertools": itertools, "json": json}
exec("W, H = 2048, 1536\n" + "def blobs" + src.split("def blobs")[1].split("CONV =")[0], ns)  # blobs, detect_cards, find_cursor, inside
detect_cards, find_cursor, inside = ns["detect_cards"], ns["find_cursor"], ns["inside"]

ev = pd.read_csv(os.path.join(SC, "ui_events_in_video.csv"), dtype={"pid": str})
ev["pid"] = ev.pid.str.zfill(3)
clicks = ev[ev.page.isin(["charging", "assistant_chat"])].copy()

# --- extract click frames (t-0.4, t-0.2, t)
cdir = os.path.join(SC, "clickframes"); os.makedirs(cdir, exist_ok=True)
nf = 0
for _, c in clicks.iterrows():
    for off in (-0.4, -0.2, 0.0):
        t = c.vt + off
        out = os.path.join(cdir, f"{c.pid}_{c.vt:.2f}_{off:+.1f}.png")
        if not os.path.exists(out):
            subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", os.path.join(V, INFO[c.pid][1]), "-frames:v", "1", out], check=True)
            nf += 1
print("new frames extracted:", nf)

def load_gaze(pid):
    g = pd.read_csv(os.path.join(R, INFO[pid][0], pid + ".csv"), usecols=["relative_to_video_first_frame_timestamp", "status", "stability", "gaze_forward_x", "gaze_forward_y", "gaze_forward_z"]).apply(pd.to_numeric, errors="coerce").dropna()
    g = g[(g.status == 2) & (g.stability > 0)].reset_index(drop=True)
    return g.relative_to_video_first_frame_timestamp.values / 1e9, g.gaze_forward_x.values, g.gaze_forward_y.values, g.gaze_forward_z.values

G = {p: load_gaze(p) for p in INFO}

def ratios(pid, t0, t1):
    gt, x, y, z = G[pid]
    s = (gt >= t0) & (gt < t1) & (z > 0.2)
    if s.sum() < 10: return None
    return float(np.mean(x[s] / z[s])), float(np.mean(y[s] / z[s])), int(s.sum())

# --- click calibration pairs
rows = []
for _, c in clicks.iterrows():
    ptr = []
    for off in (-0.4, -0.2, 0.0):
        img = cv2.imread(os.path.join(cdir, f"{c.pid}_{c.vt:.2f}_{off:+.1f}.png"))
        p = find_cursor(img); ptr.append(p)
    pm = ptr[1] if ptr[1] else (ptr[0] or ptr[2])
    spread = None
    pts = [p for p in ptr if p]
    if len(pts) >= 2: spread = float(np.max([np.hypot(a[0] - b[0], a[1] - b[1]) for a in pts for b in pts]))
    r = ratios(c.pid, c.vt - 0.3, c.vt)
    rows.append(dict(pid=c.pid, vt=c.vt, page=c.page, kiosk_used=c.kiosk_used, px=pm[0] if pm else np.nan, py=pm[1] if pm else np.nan,
                     ptr_spread_px=spread, a=r[0] if r else np.nan, b=r[1] if r else np.nan, n=r[2] if r else 0))
C = pd.DataFrame(rows)
print("\n== click pairs (pointer tip at click-0.2 s; gaze_forward ratios gx/gz, gy/gz mean over 300 ms before click)")
print(C.round(3).to_string())
C.to_csv(os.path.join(SC, "click_pairs.csv"), index=False)

def fit(df, sx, sy):
    d = df.dropna(subset=["px", "a"])
    A = np.zeros((2 * len(d), 3)); t = np.zeros(2 * len(d))
    for i, (_, r) in enumerate(d.iterrows()):
        A[2 * i] = [1, 0, sx * r.a]; t[2 * i] = r.px
        A[2 * i + 1] = [0, 1, sy * r.b]; t[2 * i + 1] = r.py
    th, *_ = np.linalg.lstsq(A, t, rcond=None)
    res = np.hypot((A @ th - t)[0::2], (A @ th - t)[1::2])
    return th, res, len(d)

def proj(th, sx, sy, a, b): return th[0] + sx * th[2] * a, th[1] + sy * th[2] * b

tr = C[C.pid == "021"]
print(f"\n021 click pairs usable for fit: {int(tr.dropna(subset=['px','a']).shape[0])} (2 equations each; 3 parameters)")

# pointer-based secondary calibration from the D060 window frames (021 only)
pw = pd.read_csv(os.path.join(SC, "win", "cursor_gaze_pairs.csv"), dtype={"pid": str})
pw["pid"] = pw.pid.str.zfill(3)
def ptr_pairs(pid):
    out = []
    for _, r in pw[pw.pid == pid].dropna(subset=["cx"]).iterrows():
        rr = ratios(pid, r.t - 0.25, r.t + 0.25)
        if rr: out.append(dict(pid=pid, t=r.t, px=r.cx, py=r.cy, a=rr[0], b=rr[1]))
    return pd.DataFrame(out)
PP = {p: ptr_pairs(p) for p in INFO}

results = {}
print("\n== PRIMARY: fit (cx,cy,f) on 021 clicks only; held-out click pixel error (041, 100) vs constant-guess")
const = (tr.px.median(), tr.py.median())
for sx, sy in itertools.product([1, -1], [1, -1]):
    th, res, n = fit(C[C.pid == "021"], sx, sy)
    line = f" sx={sx:+d} sy={sy:+d}: theta cx={th[0]:.0f} cy={th[1]:.0f} f={th[2]:.0f}  train resid(021)={np.round(res,0).tolist()};"
    for p in ["041", "100"]:
        te = C[C.pid == p].dropna(subset=["px", "a"])
        u, v = proj(th, sx, sy, te.a.values, te.b.values)
        e = np.hypot(u - te.px.values, v - te.py.values); eb = np.hypot(te.px.values - const[0], te.py.values - const[1])
        line += f" {p}: n={len(te)} median err {np.median(e):.0f}px (const-guess {np.median(eb):.0f}px);"
    print(line)
    results[("click", sx, sy)] = th

print("\n== SECONDARY: fit on 021's pointer pairs (54 window frames; assumes gaze ~ pointer); held-out pixel error")
for sx, sy in itertools.product([1, -1], [1, -1]):
    th, res, n = fit(PP["021"], sx, sy)
    line = f" sx={sx:+d} sy={sy:+d}: theta cx={th[0]:.0f} cy={th[1]:.0f} f={th[2]:.0f}  train median {np.median(res):.0f}px (n={n});"
    for p in ["041", "100"]:
        te = PP[p]; u, v = proj(th, sx, sy, te.a.values, te.b.values)
        e = np.hypot(u - te.px.values, v - te.py.values); eb = np.hypot(te.px.values - PP["021"].px.median(), te.py.values - PP["021"].py.median())
        line += f" {p}: n={len(te)} median err {np.median(e):.0f}px (const {np.median(eb):.0f}px);"
    print(line)
    results[("ptr", sx, sy)] = th

# --- AOI hit rate on D061's localisation frames
WIN = os.path.join(SC, "win")
frames = {}
for pid, (sess, vid, true_k, t0) in INFO.items():
    for k in range(54):
        img = cv2.imread(os.path.join(WIN, pid, "f_%03d.png" % (k + 1)))
        cards = detect_cards(img)
        if cards: frames.setdefault(pid, []).append((t0 + 0.5 * k, cards))
print("\n== AOI hit rate on true card (share of in-card gaze samples), D061 frames; true | shift+30 | -30 | +60 | constant-guess")
tab = []
for key, th in results.items():
    kind, sx, sy = key
    line = f" {kind:5s} sx={sx:+d} sy={sy:+d}:"
    for pid, (sess, vid, true_k, t0) in INFO.items():
        gt, x, y, z = G[pid]
        out = []
        for shift in (0.0, 30.0, -30.0, 60.0):
            inT = inA = 0
            for t, cards in frames.get(pid, []):
                s = (np.abs(gt - (t + shift)) < 0.25) & (z > 0.2)
                if s.sum() < 10: continue
                u, v = proj(th, sx, sy, x[s] / z[s], y[s] / z[s])
                hit = np.array([inside(cards, a, b) for a, b in zip(u, v)])
                inA += (hit > 0).sum(); inT += (hit == true_k).sum()
            out.append(inT / inA if inA else float("nan"))
        cg = []
        for t, cards in frames.get(pid, []):
            cg.append(inside(cards, *const))
        cgs = np.mean([h == true_k for h in cg if h > 0]) if any(h > 0 for h in cg) else float("nan")
        line += f" | {pid}(K{true_k}) " + "/".join(f"{o:.2f}" for o in out) + f" cg {cgs:.2f}"
    print(line)
cw = [ (c[2] - c[0]) for pid in frames for _, cards in frames[pid] for c in cards.values()]
print(f"\ncard box width (localisation scale): median {np.median(cw):.0f}px, so a held-out pixel error above ~{np.median(cw)/2:.0f}px = more than half a card wide")
