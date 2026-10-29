"""The final report must be a pure function of the registry: a frozen fixture gives a frozen checksum, and changing a registry value changes the report."""
import hashlib
import json
import re
import shutil
from pathlib import Path

from backend.pipeline.gate7.build_final_report import build

FIXTURE = Path(__file__).parent / "fixture" / "results"
# SHA-256 of the report generated from the frozen fixture. If the generator's wording or layout is changed on purpose, regenerate the fixture
# output, check the diff by eye, and update this value in the same commit as the change.
EXPECTED_SHA256 = "13e94b02dc9ada165576386594bb592333d513060f820ae4d475caba6e7d1d05"


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_frozen_fixture_gives_frozen_checksum(tmp_path):
    out = tmp_path / "report.md"
    build(FIXTURE, out)
    assert _sha(out) == EXPECTED_SHA256


def test_output_is_deterministic(tmp_path):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    build(FIXTURE, a)
    build(FIXTURE, b)
    assert a.read_bytes() == b.read_bytes()


def test_numbers_come_from_the_registry(tmp_path):
    work = tmp_path / "results"
    shutil.copytree(FIXTURE, work)
    f = next(work.glob("h1_claim_a_*/summary.json"))
    j = json.loads(f.read_text(encoding="utf-8"))
    node = j["metrics"] if "metrics" in j else j
    node["primary"]["lrt"]["p"] = 0.12345
    f.write_text(json.dumps(j), encoding="utf-8")
    out = tmp_path / "changed.md"
    build(work, out)
    text = out.read_text(encoding="utf-8")
    assert "p = 0.123" in text and "p = 0.226" not in text
    assert _sha(out) != EXPECTED_SHA256


def test_malicious_and_slm_claims_wording(tmp_path):
    out = tmp_path / "r.md"
    build(FIXTURE, out)
    text = out.read_text(encoding="utf-8")
    assert "Best SLM: not named" in text
    assert "no SLM showed reliable detection above the rule baselines" in text
    assert not re.search(r"Best SLM \(rule", text)
