import numpy as np
import pandas as pd

from ..score_spec import REFS, detection_block, holm, degenerate_det, model_p


def _df(preds):
    n = len(preds)
    return pd.DataFrame(dict(scenario_id=[f"S{i // 3:03d}" for i in range(n)], attacked=[i % 2 for i in range(n)], pred=preds, fail=[""] * n,
                             visible_class=["benign_plain" if i % 2 == 0 else "ambiguous_attack_real" for i in range(n)], hidden_mode=["none" if i % 2 == 0 else "reduced" for i in range(n)],
                             image_type=["real"] * n, badge=[0] * n))


def test_failed_reply_is_wrong():
    df = _df(["FAIL"] * 12)
    p = model_p(df)
    assert (p[df.attacked.to_numpy() == 1] == 0).all() and (p[df.attacked.to_numpy() == 0] == 1).all()


def test_constants_and_perfect_model():
    perfect = _df(["UNSAFE" if i % 2 else "SAFE" for i in range(60)])
    b = detection_block(perfect)
    assert b["balanced_accuracy"] == 1.0 and b["false_safe"]["p"] == 0 and b["false_warning"]["p"] == 0
    assert b["diff_vs_best"]["lo"] > 0
    assert all(abs(b["references"][r]["balanced_accuracy"] - 0.5) < 1e-9 for r in ("always SAFE", "always UNSAFE", "random (expected)"))


def test_constant_model_is_degenerate_and_not_better():
    b = detection_block(_df(["SAFE"] * 60))
    assert b["degenerate"]["flag"] and b["diff_vs_best"]["hi"] <= 1e-9 or b["diff_vs_best"]["lo"] <= 0


def test_holm_monotone():
    a = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert a["a"] <= a["c"] <= a["b"] and all(v <= 1 for v in a.values())
