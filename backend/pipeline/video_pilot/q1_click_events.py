import pandas as pd, os, glob, json
R = r"backend\raw_data"
FF = {"021": (0.0, 125.8, "session_<redacted>"), "041": (0.0, 1640.0, "session_<redacted>"), "100": (0.0, 970.0, "session_<redacted>")}
pd.set_option("display.width", 220)
out = []
for pid, (ff, dur, sess) in FF.items():
    I = pd.read_csv(glob.glob(os.path.join(R, sess, "interactions*.csv"))[0])
    I = I[(I.channel == "parsed_json") & (I.route == "UI")].copy()
    I["vt"] = I.timestamp_unix_ms / 1000 - ff
    I = I[(I.vt > 0) & (I.vt < dur)]
    for _, r in I.iterrows():
        pj = json.loads(r.payload_json) if isinstance(r.payload_json, str) else {}
        out.append(dict(pid=pid, vt=round(r.vt, 3), page=r.page, trial=r.trial, kiosk_used=pj.get("kiosk_used"), seq=pj.get("seq")))
D = pd.DataFrame(out)
print(D.groupby(["pid", "page"]).size().unstack(fill_value=0).to_string())
print(D[D.page.isin(["charging", "assistant_chat"])].to_string())
D.to_csv(r"D:\MTP_scratch\video_pilot\ui_events_in_video.csv", index=False)
