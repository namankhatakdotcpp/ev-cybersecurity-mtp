"""Config loading for Gate 2: YAML plus environment overrides; every path is resolved relative to the repository
root (no machine-specific paths)."""
import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "gate2_h1.yaml"


def load_config(path=None):
    path = Path(path) if path else DEFAULT_CONFIG
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_config_path"] = str(path)
    envmap = cfg["paths"].get("env_overrides", {})
    resolved = {}
    for key in ("raw_data_dir", "feature_table", "results_dir"):
        val = os.environ.get(envmap.get(key, ""), cfg["paths"][key])
        p = Path(val)
        resolved[key] = p if p.is_absolute() else REPO_ROOT / p
    cfg["paths_resolved"] = resolved
    return cfg
