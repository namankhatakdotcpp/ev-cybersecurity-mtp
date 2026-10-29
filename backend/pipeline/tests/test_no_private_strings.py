"""Guard before any push: tracked files must not carry the lab-folder name, home-directory paths of the original machines,
participant session folder names (outside the data table that already existed), capture timestamps, or the private session map."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BS = chr(92)
LAB = re.compile(r"\w+_EVTrip_\w+_Under_\w+")        # the lab folder name, matched by shape so this file does not repeat it
SESSION = re.compile(r"session_20\d{6}_\d{6}_\d{3}")
CAPTURE = re.compile(r"varjo_capture_20\d\d-\d\d-\d\d_")
# files that predate the Gate work and are already on origin; they are a separate decision (docs/audit/PUSH_REVIEW.md, section 3)
LEGACY = {"backend/pipeline/feature_table.csv", "backend/gaze/aoi_free_pilot.py", "Decision.md"}
# paths produced by the Gate 0-6 work; the home-path and session checks apply to these only
NEW = ("backend/pipeline/gate2/", "backend/pipeline/gate5/", "backend/pipeline/gate6/", "backend/pipeline/video_pilot/", "backend/pipeline/paths.py", "backend/pipeline/build_video_gaze_map.py",
       "backend/pipeline/tests/", "configs/gate", "docs/", "results/", "scenarios/", "private_example/")


def new_files():
    return [f for f in tracked() if f.startswith(NEW) and f not in LEGACY]


def tracked():
    out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    return [f for f in out if not f.endswith((".pdf", ".docx", ".joblib", ".lua"))]


def text(f):
    try:
        return (ROOT / f).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def test_lab_folder_name_nowhere():
    assert [f for f in tracked() if LAB.search(text(f))] == []


def test_no_user_home_paths_in_new_files():
    bad = [f for f in new_files() if f != "docs/audit/PUSH_REVIEW.md" and re.search(r"/Users/[A-Za-z]|C:" + re.escape(BS) + "{1,2}Users", text(f))]
    assert bad == []


def test_no_session_folders_or_capture_names_in_new_files():
    bad = [f for f in new_files() if (SESSION.search(text(f)) or CAPTURE.search(text(f)))]
    assert bad == []


def test_private_dir_ignored_and_map_untracked():
    assert "backend/pipeline/video_gaze_session_map.csv" not in tracked()
    assert not [f for f in tracked() if f.startswith("private/")]
    r = subprocess.run(["git", "check-ignore", "private/video_gaze_session_map.csv"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0
