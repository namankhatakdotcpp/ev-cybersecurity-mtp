import numpy as np
import pytest

from backend.pipeline.gate2 import selection_bias as sb
from backend.pipeline.gate2.matched import build_matched, load_gate4

CFG = load_gate4()
HAVE = CFG["paths_resolved"]["raw_data_dir"].exists() and CFG["paths_resolved"]["feature_table"].exists()


@pytest.mark.skipif(not HAVE, reason="raw data not available")
def test_matched_set_reproduces_pre_specified_counts_and_is_a_subset_of_primary():
    T, primary, matched = build_matched(CFG)          # asserts the counts internally
    assert len(matched) == 150 and matched.participant_id.nunique() == 49 and int(matched.y.sum()) == 70
    assert set(zip(matched.session_dir, matched.idx)) <= set(zip(primary.session_dir, primary.idx))
    assert (~matched.eeg_missing).all()


def test_smd_and_bh_helpers():
    a, b = np.array([1.0, 2, 3, 4]), np.array([2.0, 3, 4, 5])
    assert abs(sb.smd(a, b) - (-1 / np.sqrt(5 / 3))) < 1e-9          # both samples have variance 5/3, mean difference -1
    adj = sb.bh([0.01, 0.04, 0.03, 0.5])
    assert np.all(adj >= np.array([0.01, 0.04, 0.03, 0.5]) - 1e-12) and adj.max() <= 1.0
    assert adj[0] == min(adj)
