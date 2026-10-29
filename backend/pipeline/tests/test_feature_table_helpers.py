"""The EEG time conversion in build_feature_table must not depend on the datetime resolution pandas infers (D089)."""
import numpy as np
import pandas as pd

from backend.pipeline.build_feature_table import _epoch_ms

ISO = ["2026-04-21T08:18:50.401683+00:00", "2026-04-21T08:18:50.405589+00:00"]
EXPECTED = [pd.Timestamp(t).timestamp() * 1000 for t in ISO]


def test_epoch_ms_from_strings():
    assert np.allclose(_epoch_ms(pd.Series(ISO)), EXPECTED)


def test_epoch_ms_is_resolution_independent():
    base = pd.to_datetime(pd.Series(ISO), utc=True)
    for unit in ("ns", "us", "ms"):
        got = _epoch_ms(base.astype(f"datetime64[{unit}, UTC]")).to_numpy()
        assert np.allclose(got, EXPECTED, atol=1.0 if unit == "ms" else 1e-6), unit
