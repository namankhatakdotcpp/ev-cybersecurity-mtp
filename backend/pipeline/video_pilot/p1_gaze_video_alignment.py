import pandas as pd, numpy as np, glob, os, json
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from backend.pipeline.paths import RAW, VARJO, SESSION_MAP, pilot_sessions
R = str(RAW)
M = pd.read_csv(str(SESSION_MAP), dtype=str)
for pid in ["021", "041", "100"]:
    row = M[M.participant_id == pid].iloc[0]
    sess = row.session_folder
    g = pd.read_csv(os.path.join(R, sess, pid + ".csv"), usecols=["relative_to_unix_epoch_timestamp", "relative_to_video_first_frame_timestamp", "frame_number", "status", "stability"])
    e = g.relative_to_unix_epoch_timestamp.astype("int64"); r = g.relative_to_video_first_frame_timestamp.astype("int64")
    off = (e - r) / 1e9
    print(f"== {pid} {sess} rows={len(g)}")
    print(f" rel first/last (s): {r.iloc[0]/1e9:.4f} / {r.iloc[-1]/1e9:.4f}; epoch span {(e.iloc[-1]-e.iloc[0])/1e9:.3f}s; mp4 dur {row.mp4_duration_s}")
    print(f" (epoch - rel) drift over file: min..max spread = {(off.max()-off.min())*1000:.3f} ms; first_frame_epoch={off.iloc[0]:.3f}")
    print(f" frame_number first/last/span: {g.frame_number.iloc[0]}, {g.frame_number.iloc[-1]}, {g.frame_number.iloc[-1]-g.frame_number.iloc[0]} (video frames={int(float(row.mp4_duration_s)*30)})")
    # does the Varjo frame_number counter advance at 30 fps relative to rel time?
    sl = np.polyfit(r / 1e9, g.frame_number.astype(float), 1)
    print(f" frame_number vs rel slope = {sl[0]:.4f} frames/s")
    print(f" status==2 frac {np.mean(g.status==2):.3f}, valid(status2&stab>0) {np.mean((g.status==2)&(g.stability>0)):.3f}")
    # same file in Varjo folder identical size?
    vp = os.path.join(str(VARJO), pid + ".csv")
    print(" Varjo copy same size as session copy:", os.path.getsize(vp) == os.path.getsize(os.path.join(R, sess, pid + ".csv")))
    ia = glob.glob(os.path.join(R, sess, "interactions*.csv"))[0]
    I = pd.read_csv(ia)
    print(" interaction route/message counts:\n", I[I.channel == "parsed_json"].groupby(["route", "message"]).size().sort_values(ascending=False).head(15).to_string())
    t0 = I.timestamp_unix_ms.iloc[0] / 1000; t1 = I.timestamp_unix_ms.iloc[-1] / 1000
    print(f" interaction log unix span {t0:.1f}..{t1:.1f}; gaze/video span {off.iloc[0]:.1f}..{off.iloc[0]+r.iloc[-1]/1e9:.1f}")
