"""Append-only experiment registry (Protocol v1 section 13): one CSV row per run plus a JSON summary per run folder.
Existing runs are never overwritten; a clash of experiment ids is an error."""
import csv
import datetime as dt
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

COLUMNS = ["experiment_id", "timestamp", "protocol_version", "protocol_commit", "dataset_version", "feature_version",
           "label_version", "split_scheme", "seed", "model", "hyperparameters", "environment", "git_commit", "metrics",
           "artifact_paths", "status", "notes"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(args, cwd):
    exe = shutil.which("git")
    if not exe:
        return "unknown"
    try:
        return subprocess.run([exe] + args, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def environment_string():
    import numpy, pandas, scipy, sklearn, statsmodels
    return (f"python {platform.python_version()}; {platform.system()} {platform.release()}; numpy {numpy.__version__}; "
            f"scipy {scipy.__version__}; pandas {pandas.__version__}; scikit-learn {sklearn.__version__}; "
            f"statsmodels {statsmodels.__version__}")


def _jsonable(o):
    import numpy as np
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


def register(cfg, name, split_scheme, seed, model, hyper, metrics, dataset_path, artifacts=(), status="completed", notes="",
             repo_root=None):
    results = Path(cfg["paths_resolved"]["results_dir"])
    eid = f"{name}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    run_dir = results / eid
    if run_dir.exists():
        raise FileExistsError(run_dir)
    run_dir.mkdir(parents=True)
    root = repo_root or results.parent
    commit = _git(["rev-parse", "HEAD"], root)
    dirty = _git(["status", "--porcelain", "--untracked-files=no"], root)
    row = dict(experiment_id=eid, timestamp=dt.datetime.now().isoformat(timespec="seconds"),
               protocol_version=cfg["protocol"]["version"], protocol_commit=cfg["protocol"]["commit"],
               dataset_version=sha256_file(dataset_path) if dataset_path else "", feature_version=sha256_file(cfg["paths_resolved"]["feature_table"]),
               label_version=cfg["target"]["label_version"], split_scheme=split_scheme, seed=json.dumps(seed, default=_jsonable),
               model=model, hyperparameters=json.dumps(hyper, default=_jsonable), environment=environment_string(),
               git_commit=commit + ("+dirty" if dirty not in ("", "unknown") else ""),
               metrics=json.dumps(metrics, default=_jsonable), artifact_paths=json.dumps([str(a) for a in artifacts]),
               status=status, notes=notes)
    (run_dir / "summary.json").write_text(json.dumps(row | {"metrics": metrics, "hyperparameters": hyper}, indent=1, default=_jsonable))
    reg = results / "registry.csv"
    new = not reg.exists()
    with open(reg, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        w.writerow(row)
    return eid, run_dir
