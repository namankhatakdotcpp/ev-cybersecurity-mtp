"""Matched EEG set for Gate 4 (Protocol v1 section 6): primary T1 rows that also have usable EEG features. The EEG
columns come from the committed feature table, joined by session and event order (the same key as the T1 table)."""
import yaml
import pandas as pd

from .benchmark import load_gate3
from .build_t1_table import build_table
from .config import REPO_ROOT


def load_gate4(path=None):
    cfg = load_gate3()
    with open(path or REPO_ROOT / "configs" / "gate4_eeg.yaml", "r", encoding="utf-8") as f:
        cfg["g4"] = yaml.safe_load(f)
    return cfg


def set_columns4(cfg, name):
    f = cfg["features"]
    return list(f["exposure"] + f["design"] + cfg["g4"]["sets"][name]["extra"])


def build_matched(cfg):
    T = build_table(cfg)
    ft = pd.read_csv(cfg["paths_resolved"]["feature_table"], dtype={"participant_id": str})
    ft["idx"] = ft.groupby("session_dir").cumcount()
    eeg = cfg["g4"]["matched_set"]["eeg_features"]
    T = T.merge(ft[["session_dir", "idx", "eeg_missing"] + eeg], on=["session_dir", "idx"], how="left", validate="one_to_one")
    T["eeg_missing"] = T["eeg_missing"].astype(bool)
    primary = T[T["eligible_primary"]].reset_index(drop=True)
    matched = primary[~primary["eeg_missing"]].reset_index(drop=True)
    exp = cfg["g4"]["matched_set"]["expected"]
    got = dict(rows=len(matched), participants=int(matched["participant_id"].nunique()), events=int(matched["y"].sum()))
    assert got == exp, f"matched set differs from the pre-specified counts: {got} vs {exp}"
    assert matched[eeg].notna().all().all()
    return T, primary, matched
