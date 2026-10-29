"""Read-only: derive Varjo gaze CSV <-> mp4 <-> session-folder map. Stdlib only."""
import csv, os, re, struct, sys, glob, datetime as dt

ROOT = r"<project root>"
VARJO = os.path.join(ROOT, "Varjo")
RAW = os.path.join(ROOT, "backend", "raw_data")
OUT = os.path.join(ROOT, "backend", "pipeline", "video_gaze_session_map.csv")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def mp4_info(path):
    """duration_s, fps(None), creation_utc from moov/mvhd (+ first video track mdhd/stts if cheap)."""
    with open(path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        pos = 0
        while pos < size:
            f.seek(pos)
            hdr = f.read(16)
            if len(hdr) < 8:
                break
            sz, typ = struct.unpack(">I4s", hdr[:8])
            if sz == 1:
                sz = struct.unpack(">Q", hdr[8:16])[0]
            elif sz == 0:
                sz = size - pos
            if typ == b"moov":
                f.seek(pos)
                moov = f.read(min(sz, 64 * 1024 * 1024))
                i = moov.find(b"mvhd")
                v = moov[i + 4]
                if v == 1:
                    ct, _mt, ts, du = struct.unpack(">QQIQ", moov[i + 8:i + 8 + 28])
                else:
                    ct, _mt, ts, du = struct.unpack(">IIII", moov[i + 8:i + 8 + 16])
                created = None
                if ct:
                    created = dt.datetime(1904, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(seconds=ct)
                fps = None
                j = moov.find(b"stts")
                m = moov.find(b"mdhd")
                if j > 0 and m > 0:
                    mv = moov[m + 4]
                    mts = struct.unpack(">I", moov[m + 8 + (16 if mv == 1 else 8):m + 12 + (16 if mv == 1 else 8)])[0]
                    n = struct.unpack(">I", moov[j + 8:j + 12])[0]
                    if n >= 1:
                        cnt, delta = struct.unpack(">II", moov[j + 12:j + 20])
                        if delta:
                            fps = round(mts / delta, 2)
                return du / ts, fps, created
            pos += sz
    return None, None, None


def gaze_span(path):
    """first/last (epoch_ns, rel_to_video_ns), row count unknown (skipped), via head+tail reads."""
    with open(path, "rb") as f:
        head = f.read(8192).decode("utf-8", "ignore").splitlines()
        f.seek(0, 2)
        sz = f.tell()
        f.seek(max(0, sz - 16384))
        tail = f.read().decode("utf-8", "ignore").splitlines()
    cols = head[0].split(",")
    ie = cols.index("relative_to_unix_epoch_timestamp")
    ir = cols.index("relative_to_video_first_frame_timestamp")
    r0 = head[1].split(",")
    r1 = [l for l in tail if l.count(",") == len(cols) - 1][-1].split(",")
    return int(r0[ie]), int(r0[ir]), int(r1[ie]), int(r1[ir])


def fname_ts(name):
    m = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})-(\d{3})", name)
    d = dt.datetime.strptime(m.group(1) + " %s:%s:%s.%s" % m.groups()[1:], "%Y-%m-%d %H:%M:%S.%f")
    return d.replace(tzinfo=IST)


# --- videos
vids = []
for p in sorted(glob.glob(os.path.join(VARJO, "*.mp4"))):
    dur, fps, created = mp4_info(p)
    vids.append(dict(path=p, name=os.path.basename(p), start=fname_ts(p), dur=dur, fps=fps, created=created))
print("videos", len(vids), "with dur", sum(1 for v in vids if v["dur"]), file=sys.stderr)

# --- session folders by pid
sessions = {}
for d in sorted(os.listdir(RAW)):
    m = re.match(r"session_(\d{8})_(\d{6})_(\d+)$", d)
    if m:
        sessions.setdefault(m.group(3), []).append(d)

rows = []
for p in sorted(glob.glob(os.path.join(VARJO, "*.csv"))):
    base = os.path.basename(p)[:-4]
    try:
        e0, r0, e1, r1 = gaze_span(p)
    except Exception as ex:
        rows.append(dict(gaze_csv=base + ".csv", match_method="unreadable:" + str(ex)[:40]))
        continue
    first_frame_epoch = (e0 - r0) / 1e9  # epoch time of video first frame
    ffe = dt.datetime.fromtimestamp(first_frame_epoch, dt.timezone.utc)
    gaze_dur = (e1 - e0) / 1e9
    # nearest video by first-frame epoch vs filename start
    best = min(vids, key=lambda v: abs((v["start"] - ffe).total_seconds()))
    off = (ffe - best["start"]).total_seconds()
    conf = "high" if abs(off) < 30 and best["dur"] and abs(best["dur"] - gaze_dur) < 30 else ("medium" if abs(off) < 120 else "none")
    pid = base if re.fullmatch(r"\d+", base) else ""
    sess = ";".join(sessions.get(pid.lstrip("0").zfill(3), [])) if pid else ""
    rows.append(dict(
        participant_id=pid, gaze_csv=base + ".csv",
        mp4=best["name"] if conf != "none" else "", mp4_duration_s=round(best["dur"], 1) if best["dur"] and conf != "none" else "",
        fps=best["fps"] if conf != "none" else "",
        gaze_epoch_start=round(e0 / 1e9, 3), gaze_epoch_end=round(e1 / 1e9, 3), gaze_duration_s=round(gaze_dur, 1),
        first_frame_utc=ffe.isoformat(timespec="milliseconds"), offset_vs_filename_s=round(off, 2),
        session_folder=sess,
        match_method="first_frame_epoch(gaze epoch - relative_to_video_first_frame) vs mp4 filename (IST)",
        match_confidence=conf))

cols = ["participant_id", "gaze_csv", "mp4", "mp4_duration_s", "fps", "gaze_epoch_start", "gaze_epoch_end",
        "gaze_duration_s", "first_frame_utc", "offset_vs_filename_s", "session_folder", "match_method", "match_confidence"]
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)

used = {r.get("mp4") for r in rows if r.get("mp4")}
print("gaze csvs", len(rows), "matched high", sum(r.get("match_confidence") == "high" for r in rows),
      "medium", sum(r.get("match_confidence") == "medium" for r in rows),
      "none", sum(r.get("match_confidence") == "none" for r in rows))
print("videos used", len(used), "unused", [v["name"] for v in vids if v["name"] not in used][:200])
