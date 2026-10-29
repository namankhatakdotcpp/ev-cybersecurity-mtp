import json
import re

import pytest

from backend.pipeline.gate5.build_scenarios import VISIBLE, load_cfg

CFG = load_cfg()
OUT = CFG["paths_resolved"]["out_dir"]
pytestmark = pytest.mark.skipif(not (OUT / "manifest.json").exists(), reason="scenario set not built")


def _rd(name):
    return [json.loads(l) for l in open(OUT / name, encoding="utf-8")]


def test_inputs_and_truth_are_aligned_and_complete():
    inp, tr = _rd("scenarios_inputs.jsonl"), _rd("scenarios_truth.jsonl")
    assert len(inp) == len(tr) == CFG["sampling"]["n_stations"]
    assert [i["scenario_id"] for i in inp] == [t["scenario_id"] for t in tr]
    for i, t in zip(inp, tr):
        avail = [k["id"] for k in t["kiosks"] if k["available"]]
        assert avail == i["available_kiosks"]
        assert set(t["safe_available"]) | set(t["attacked_available"]) == set(avail)


def test_quotas_are_met():
    man = json.load(open(OUT / "manifest.json"))
    assert man["strata"] == {k: v["n"] for k, v in CFG["sampling"]["strata"].items()}
    assert all(man["visible_class_counts"][c] >= CFG["sampling"]["min_kiosks_per_visible_class"] for c in VISIBLE)
    assert all(v >= CFG["sampling"]["min_attacked_per_hidden_mode"] for v in man["attacked_by_hidden_mode"].values())
    tr = _rd("scenarios_truth.jsonl")
    assert sum(t["malicious_condition"] for t in tr) == CFG["sampling"]["malicious_condition_stations"]
    assert all(t["stratum"] == "mixed" and t["malicious_target"] in t["attacked_available"] and t["safe_available"] for t in tr if t["malicious_condition"])


def test_model_inputs_contain_no_ground_truth_or_identifiers():
    inp = _rd("scenarios_inputs.jsonl")
    for i in inp:
        assert not re.search(r"\b(attack\w*|compromis\w*|cyber|safe|unsafe|deepfake\w*|real\d)\b", i["text_V1"], re.I), i["scenario_id"]
        assert not re.search(r"\.png|session_|participant", i["text_V2"], re.I), i["scenario_id"]
    blob = (OUT / "scenarios_inputs.jsonl").read_text(encoding="utf-8") + (OUT / "scenarios_truth.jsonl").read_text(encoding="utf-8")
    assert not re.search(r"session_\d|participant_id", blob)


def test_every_shown_image_has_a_description():
    desc = json.load(open(OUT / "image_descriptions.json", encoding="utf-8"))
    assert len(desc) == 11 and all(v["visual"] and v["anomalies"] for v in desc.values())
