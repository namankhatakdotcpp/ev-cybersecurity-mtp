"""Run: python -m backend.pipeline.gate2.diagnostics.g4_noise_columns\nPost-hoc DIAGNOSTIC (not pre-specified; does not change any Gate 4 conclusion): does adding 17 pure-noise columns to the
BG model raise the nested-CV AUROC on the matched set? Same ridge learner, folds and seeds as S6."""
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from backend.pipeline.gate2 import benchmark as bm
from backend.pipeline.gate2.matched import build_matched, load_gate4, set_columns4

cfg = load_gate4()
_, _, M = build_matched(cfg)
log1p = cfg["features"]["log1p_counts"]
bg = set_columns4(cfg, "BG")
y = M["y"].to_numpy(float)
R = len(cfg["claim_b"]["repeat_seeds"])

def auroc(df, cols):
    res = [bm.run_repeat(df, {"M": cols}, "ridge", cfg, r, log1p) for r in range(R)]
    return float(bm.metrics_for(y, np.array([r["M"]["oof"] for r in res]))[0][0])

def one(seed, k=17):
    rng = np.random.default_rng(900 + seed)
    d = M.copy()
    names = [f"noise{i}" for i in range(k)]
    for n in names:
        d[n] = rng.normal(size=len(d))
    return auroc(d, bg + names)

base = auroc(M, bg)
d17 = np.array(Parallel(n_jobs=24)(delayed(one)(s) for s in range(40)))
d5 = np.array(Parallel(n_jobs=24)(delayed(one)(s, 5) for s in range(40)))
print(f"BG alone: {base:.4f}")
print(f"BG + 17 noise columns: mean {d17.mean():.4f} (delta {d17.mean()-base:+.4f}), sd {d17.std():.4f}, range [{d17.min():.4f}, {d17.max():.4f}], share above BG {np.mean(d17>base):.2f}")
print(f"BG + 5 noise columns: mean {d5.mean():.4f} (delta {d5.mean()-base:+.4f}), sd {d5.std():.4f}")
