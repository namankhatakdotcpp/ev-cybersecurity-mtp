"""Checks the analysis table against the counts established independently in Gate 1 (raw-log recomputation).
Skipped automatically when the raw data are not available on the machine."""
import pytest

from backend.pipeline.gate2.build_t1_table import build_table, primary_counts
from backend.pipeline.gate2.config import load_config

CFG = load_config()
HAVE_DATA = CFG["paths_resolved"]["raw_data_dir"].exists() and CFG["paths_resolved"]["feature_table"].exists()
pytestmark = pytest.mark.skipif(not HAVE_DATA, reason="raw data or feature table not available")


@pytest.fixture(scope="module")
def table():
    return build_table(CFG)


def test_row_count_and_unique_keys(table):
    assert len(table) == 1123
    assert table.participant_id.nunique() == 126
    assert not table.duplicated(["session_dir", "idx"]).any()


def test_counts_match_gate1(table):
    c = primary_counts(table)
    assert c["universe_rows"] == 516 and c["universe_participants"] == 115 and c["universe_events"] == 233
    assert c["primary_rows"] == 492 and c["primary_participants"] == 112 and c["primary_events"] == 220


def test_no_skip_or_forced_choice_row_is_eligible(table):
    e = table[table.eligible_universe]
    assert (e.decision == "charge").all()
    assert (e.n_attacked >= 1).all() and (e.n_attacked <= e.n_available - 1).all()
    assert e.y.isin([0, 1]).all()


def test_offset_and_layout_fields(table):
    e = table[table.eligible_primary]
    assert set(e.n_available.unique()) <= {2, 3}
    assert ((e.p_exp > 0) & (e.p_exp < 1)).all()
    assert e.offset.notna().all()
    assert set(e.period.unique()) <= {"apr", "jun", "jul_aug"}
    assert e.incident_mode.isin([0, 1]).all()


def test_primary_rows_have_complete_features(table):
    e = table[table.eligible_primary]
    cols = ["log_window_duration_s", "ai_help_used", "trial_index", "gaze_n_fixations", "gaze_n_clusters", "gaze_n_transitions",
            "gaze_transitions_per_fixation", "gaze_dispersion", "gaze_entropy_bits"]
    assert e[cols].notna().all().all()
