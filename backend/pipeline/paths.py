"""Configurable roots for scripts that touch raw or private data. Nothing here is machine specific:

  EV_PROJECT_ROOT  repository root (default: derived from this file)
  EV_RAW_DATA_DIR  session folders (default: <root>/backend/raw_data)
  EV_VARJO_DIR     Varjo gaze CSVs and mp4s (default: <root>/Varjo, gitignored)
  EV_PRIVATE_DIR   participant-linked tables that must not be committed (default: <root>/private, gitignored)
  EV_EEG_DECODED_DIR  decoded Muse EEG (default: <root>/backend/Muse/decoded)
  EV_FEATURE_TABLE    feature table written by build_feature_table.py (default: <root>/backend/pipeline/feature_table.csv)

Scripts using these paths are run from the repository root, for example `python -m backend.pipeline.build_feature_table`.

The private directory holds `video_gaze_session_map.csv` (regenerate it with build_video_gaze_map.py) and `pilot_sessions.json`
(see `private_example/pilot_sessions.example.json` for the layout)."""
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("EV_PROJECT_ROOT") or Path(__file__).resolve().parents[2])
RAW = Path(os.environ.get("EV_RAW_DATA_DIR") or ROOT / "backend" / "raw_data")
VARJO = Path(os.environ.get("EV_VARJO_DIR") or ROOT / "Varjo")
PRIVATE = Path(os.environ.get("EV_PRIVATE_DIR") or ROOT / "private")
SESSION_MAP = PRIVATE / "video_gaze_session_map.csv"
PIPELINE = ROOT / "backend" / "pipeline"
EEG_DECODED = Path(os.environ.get("EV_EEG_DECODED_DIR") or ROOT / "backend" / "Muse" / "decoded")
EEG_SUMMARY = EEG_DECODED / "decode_summary_resynced.csv"
CONTAMINATED_JSON = ROOT / "backend" / "rag_contaminated_sessions.json"
FEATURE_TABLE = Path(os.environ.get("EV_FEATURE_TABLE") or PIPELINE / "feature_table.csv")


def pilot_sessions():
    """{participant code: {"session": folder name, "video": mp4 name, "first_frame_epoch": float}} for the video pilot, from the private directory."""
    f = PRIVATE / "pilot_sessions.json"
    if not f.exists():
        raise FileNotFoundError(f"{f} is missing: the video-pilot scripts need the pilot session list (see private_example/pilot_sessions.example.json)")
    return json.loads(f.read_text(encoding="utf-8"))
