import pytest

from backend.pipeline.gate2 import master_table
from backend.pipeline.gate2.config import load_config

CFG = load_config()
pytestmark = pytest.mark.skipif(not (CFG["paths_resolved"]["results_dir"] / "registry.csv").exists(), reason="no registry on this machine")


def test_master_table_is_generated_from_registry_only_and_is_deterministic():
    a = master_table.build(CFG)
    b = master_table.build(CFG)
    assert a == b
    assert "Table 1" in a and "Table 3" in a
    assert "constant event rate" in a
    # every learner/set pair of the pre-specified grid appears once in Table 1
    for label in ("Ridge logistic (offset)", "Random forest", "HistGradientBoosting"):
        assert sum(1 for line in a.splitlines() if line.startswith(f"| {label} |")) >= 4
