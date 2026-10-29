"""The results chapter must be a pure function of the registry (plus the Gate 0 audit figures): a frozen fixture gives a frozen checksum,
a changed registry value changes the chapter, and the wording rules hold."""
import hashlib
import json
import re
import shutil
from pathlib import Path

from backend.pipeline.gate7.build_results_chapter import build

FX = Path(__file__).parent / "fixture"
FIXTURE = FX / "results"
AUDIT = FX / "GATE0_audit_excerpt.md"
# SHA-256 of the chapter generated from the frozen fixture. If the generator's wording or layout is changed on purpose, regenerate the
# fixture output, check the diff by eye, and update this value in the same commit as the change.
EXPECTED_SHA256 = "97136b0cd7b316840ae6e3e05dab4cc9146f2f62ce403086fe74ede4adeef4f8"

CAUSAL = re.compile(r"\b(caus(e|es|ed|ing|al)|leads? to|led to|results? in|due to|because of|drives?|driven by|effect of)\b", re.I)


def _build(tmp_path, name="chapter.md", results=FIXTURE):
    out = tmp_path / name
    build(results, out, AUDIT)
    return out


def test_frozen_fixture_gives_frozen_checksum(tmp_path):
    out = _build(tmp_path)
    assert hashlib.sha256(out.read_bytes()).hexdigest() == EXPECTED_SHA256


def test_output_is_deterministic(tmp_path):
    assert _build(tmp_path, "a.md").read_bytes() == _build(tmp_path, "b.md").read_bytes()


def test_numbers_come_from_the_registry(tmp_path):
    work = tmp_path / "results"
    shutil.copytree(FIXTURE, work)
    f = next(work.glob("h1_claim_a_*/summary.json"))
    j = json.loads(f.read_text(encoding="utf-8"))
    node = j["metrics"] if "metrics" in j else j
    node["primary"]["n_rows"] = 4321
    f.write_text(json.dumps(j), encoding="utf-8")
    assert "4321 rows" in _build(tmp_path, "changed.md", work).read_text(encoding="utf-8")


def test_audit_figures_come_from_the_audit_file(tmp_path):
    text = _build(tmp_path).read_text(encoding="utf-8")
    assert "26.5%" in text and "0.827" in text


def test_no_causal_wording(tmp_path):
    text = _build(tmp_path).read_text(encoding="utf-8")
    assert CAUSAL.findall(text) == []
