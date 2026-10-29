"""AOI pilot step 2: per-frame kiosk-card localisation (button-anchored colour detection) + gaze AOI hit rate.
Uses the 162 frames already extracted by the previous step; extracts nothing new."""
import cv2, numpy as np, pandas as pd, os, itertools, json
W, H = 2048, 1536
BASE = r"D:\MTP_scratch\video_pilot\win"
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from backend.pipeline.paths import RAW, VARJO, SESSION_MAP, pilot_sessions
R = str(RAW)
PS = pilot_sessions()
S = {"021": (PS["021"]["session"], 37.0, 62.055, 1), "041": (PS["041"]["session"], 209.5, 234.444, 2), "100": (PS["100"]["session"], 355.8, 380.766, 1)}
rng = np.random.default_rng(0)


def blobs(mask, minw=150):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if w >= minw and 25 <= h <= 130 and w / h > 3 and a / (w * h) > 0.55:
            out.append((x, y, w, h))
    return out


def detect_cards(img):
    b, g, r = [img[:, :, i].astype(int) for i in range(3)]
    blue = ((b > 85) & (r < 60) & (b - r > 55) & (b > g + 40)).astype(np.uint8)
    brown = ((r > 70) & (r < 150) & (b < 80) & (r - b > 25) & (g > r - 50) & (g < r - 10)).astype(np.uint8)
    kb = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, np.ones((9, 25), np.uint8))
    kr = cv2.morphologyEx(brown, cv2.MORPH_CLOSE, np.ones((9, 25), np.uint8))
    B = [(x, y, w, h, "blue") for x, y, w, h in blobs(kb)]
    O = [(x, y, w, h, "brown") for x, y, w, h in blobs(kr)]
    allb = B + O
    if len(allb) < 2:
        return None
    # keep the Set Amount row: largest group sharing similar y (Skip Charging sits well above/right)
    best = []
    for a in allb:
        grp = [c for c in allb if abs(c[1] - a[1]) < 110 and abs(c[2] - a[2]) < 0.6 * a[2]]
        if len(grp) > len(best):
            best = grp
    best = sorted(best, key=lambda c: c[0])
    kinds = [c[4] for c in best]
    if "brown" in kinds:
        if kinds[-1] != "brown" or kinds.count("brown") != 1 or len(best) != 3:
            return None
        ids = [1, 2, 3]
    else:
        if len(best) != 3:
            return None
        ids = [1, 2, 3]
    cards = {}
    for k, (x, y, w, h, _) in zip(ids, best):
        cards[k] = (x - 0.04 * w, y - 1.85 * w, x + 1.04 * w, y + h + 0.25 * w)
    return cards


def find_cursor(img):
    b, g, r = [img[:, :, i].astype(int) for i in range(3)]
    m = ((r > 190) & (g > 40) & (g < 130) & (b < 60) & (r - g > 100)).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    best = None
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 120 < a < 2500 and 15 < w < 80 and 15 < h < 80 and a / (w * h) > 0.3 and (best is None or a > best[2]):
            best = (x, y, a, w, h, i)
    if best is None: return None
    x, y, a, w, h, i = best
    ys, xs = np.where(lab[y:y + h, x:x + w] == i); k = np.argmin(xs + ys)
    return float(xs[k] + x), float(ys[k] + y)


def inside(cards, px, py):
    for k, (x0, y0, x1, y1) in cards.items():
        if x0 <= px <= x1 and y0 <= py <= y1: return k
    return 0


CONV = {f"mean_fx{fx}_fy{fy}": (fx, fy) for fx, fy in itertools.product([0, 1], [0, 1])}
def to_px(x, y, fx, fy):
    u = (x + 1) / 2; v = (y + 1) / 2
    if fx: u = 1 - u
    if fy: v = 1 - v
    return u * W, v * H


rows = []; ptr_rows = []; cover = {}
for pid, (sess, t0, click, true_k) in S.items():
    g = pd.read_csv(os.path.join(R, sess, pid + ".csv"), usecols=["relative_to_video_first_frame_timestamp", "status", "stability", "gaze_projected_to_left_view_x", "gaze_projected_to_left_view_y", "gaze_projected_to_right_view_x", "gaze_projected_to_right_view_y"]).apply(pd.to_numeric, errors="coerce").dropna()
    g = g[(g.status == 2) & (g.stability > 0)].reset_index(drop=True)
    gt = g.relative_to_video_first_frame_timestamp.values / 1e9
    gx = ((g.gaze_projected_to_left_view_x + g.gaze_projected_to_right_view_x) / 2).values
    gy = ((g.gaze_projected_to_left_view_y + g.gaze_projected_to_right_view_y) / 2).values
    det = 0
    for k in range(54):
        t = t0 + 0.5 * k
        img = cv2.imread(os.path.join(BASE, pid, "f_%03d.png" % (k + 1)))
        cards = detect_cards(img)
        if cards is None: continue
        det += 1
        c = find_cursor(img)
        if c: ptr_rows.append(dict(pid=pid, t=t, ptr_card=inside(cards, *c)))
        for shift_name, shift in [("true", 0.0), ("shuf+30s", 30.0), ("shuf-30s", -30.0), ("shuf+60s", 60.0)]:
            sel = np.abs(gt - (t + shift)) < 0.25
            if sel.sum() < 10: continue
            for cn, (fx, fy) in CONV.items():
                hits = [inside(cards, *to_px(a, b, fx, fy)) for a, b in zip(gx[sel], gy[sel])]
                hits = np.array(hits)
                rows.append(dict(pid=pid, t=t, dt_click=t - click, shift=shift_name, conv=cn, n=len(hits),
                                 in_any=(hits > 0).mean(), in_true=(hits == true_k).mean(), true_k=true_k,
                                 cards=len(cards)))
    cover[pid] = det
print("frames with unambiguous 3-card detection:", cover, "of 54 each")
D = pd.DataFrame(rows)
P = pd.DataFrame(ptr_rows)
if len(P):
    print("\n== localisation sanity: pointer-in-card (pointer found AND cards detected)")
    for pid, gdf in P.groupby("pid"):
        tk = S[pid][3]
        print(f" {pid}: n={len(gdf)} pointer in a card {np.mean(gdf.ptr_card>0):.2f}; in true card (K{tk}) {np.mean(gdf.ptr_card==tk):.2f}; card counts {gdf.ptr_card.value_counts().to_dict()}")
print("\n== AOI hit rates (sample-level, gaze mapped by each convention; frames dt_click -25..+2)")
print("   in_true = share of ALL gaze samples in true kiosk card; share_of_in_card = in_true / in_any; chance=1/3; shuffles = same frames, gaze time-shifted 30/60 s")
tab = D.groupby(["pid", "conv", "shift"]).agg(frames=("t", "count"), in_any=("in_any", "mean"), in_true=("in_true", "mean")).reset_index()
tab["share_of_in_card"] = tab.in_true / tab.in_any.replace(0, np.nan)
pd.set_option("display.width", 250)
for pid in S:
    t = tab[tab.pid == pid]
    piv = t.pivot(index="conv", columns="shift", values="share_of_in_card").round(2)
    print(f"-- {pid} (true K{S[pid][3]}) share_of_in_card [true | shuffled gaze]; frames={int(t.frames.iloc[0]) if len(t) else 0}; in_any(true)={t[t['shift']=='true'].in_any.round(2).tolist()}")
    print(piv.to_string())
# decision-window only (last 10 s before click)
W2 = D[(D.dt_click > -10) & (D.dt_click < 0)]
t2 = W2.groupby(["pid", "conv", "shift"]).agg(frames=("t", "count"), in_any=("in_any", "mean"), in_true=("in_true", "mean")).reset_index()
t2["share"] = t2.in_true / t2.in_any.replace(0, np.nan)
print("\n== last 10 s before click only: frames per session =", t2[(t2['shift'] == 'true') & (t2.conv == 'mean_fx0_fy0')][["pid", "frames"]].values.tolist())
print(t2[t2['shift'] == 'true'].pivot(index="conv", columns="pid", values="share").round(2).to_string())
D.to_csv(os.path.join(BASE, "aoi_hits.csv"), index=False)

# overlays for visual check
for pid, k in [("021", 0), ("041", 15), ("100", 10)]:
    t0 = S[pid][1]
    for kk in range(k, 54):
        img = cv2.imread(os.path.join(BASE, pid, "f_%03d.png" % (kk + 1)))
        cards = detect_cards(img)
        if cards:
            for kc, (x0, y0, x1, y1) in cards.items():
                cv2.rectangle(img, (int(x0), int(y0)), (int(x1), int(y1)), (0, 255, 255), 4)
                cv2.putText(img, "K%d" % kc, (int(x0) + 10, int(y0) + 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 5)
            cv2.imwrite(os.path.join(BASE, f"overlay_{pid}_f{kk+1:03d}.jpg"), cv2.resize(img, (1024, 768)))
            print("overlay", pid, kk + 1); break

