"""Register the scored Gate 5 runs and generate the SLM master tables programmatically (never by hand), per docs/protocol/GATE5_scoring_spec.md.

  python -m backend.pipeline.gate5.master_table5 register   # score the stored replies and write registry rows g5_slm_<model>
  python -m backend.pipeline.gate5.master_table5 table      # results/master_table_gate5.md from the registry
"""
import json
import re
import sys

import numpy as np
import pandas as pd

from ..gate2.benchmark import load_gate3
from ..gate2.registry import register
from .build_scenarios import VISIBLE, load_cfg
from .score_spec import REFS, SUBSETS, score_all
from .score_slm import MODELS


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return o


def register_all():
    cfg = load_gate3()
    cfg["target"] = dict(cfg["target"], label_version="slm-scenarios-v1")
    ds = load_cfg()["paths_resolved"]["out_dir"] / "scenarios_inputs.jsonl"
    res, meta = score_all()
    for m in MODELS:
        eid, run = register(cfg, "g5_slm_" + m.replace(":", "_"), "approved 240-station scenario set; accuracy pass temperature 0 seed 1; consistency 5 seeds at 0.3; scoring per GATE5_scoring_spec",
                            [1, 2, 3, 4, 5], m, dict(prompts="configs/gate5_prompts.yaml", scenarios="scenarios/slm_v1", spec="docs/protocol/GATE5_scoring_spec.md"), _clean(res[m]), ds,
                            notes="Gate 5 SLM benchmark; failed replies count as wrong; references and degenerate flags per spec")
        print(m, eid)


def _p(d, k=3, counts=False):
    s = f"{d['p']:.{k}f} [{d['lo']:.{k}f}, {d['hi']:.{k}f}]"
    return s + (f" ({d['k']:.0f}/{d['n']})" if counts else "")


def _ci(d):
    return f"{d['point']:+.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}]"


def build():
    cfg = load_gate3()
    results = cfg["paths_resolved"]["results_dir"]
    reg = pd.read_csv(results / "registry.csv", dtype=str)
    rows = {}
    for m in MODELS:
        pat = "^g5_slm_" + re.escape(m.replace(":", "_")) + r"_\d{8}_"
        r = reg[reg["experiment_id"].str.match(pat)]
        if len(r):
            e = r.sort_values("timestamp").iloc[-1]
            rows[m] = (json.loads((results / e["experiment_id"] / "summary.json").read_text())["metrics"], e["experiment_id"], e["git_commit"])
    md = ["# Gate 5 SLM benchmark: master tables (generated from the registry; do not edit by hand)", "",
          "Scenario set v1 (approved): 240 stations, 599 available kiosks, quota-sampled; per-class results are the unit of interpretation and overall numbers are not prevalence-weighted. "
          "Scoring per `docs/protocol/GATE5_scoring_spec.md`: UNSAFE is the positive class; a failed reply counts as wrong on every kiosk it covers; false-safe and false-warning are always shown together; "
          "intervals on rates are Wilson 95% (nominal: kiosks within a station are not independent); comparisons with the best reference predictor use a scenario-level bootstrap (2000 resamples) and Holm adjustment over 10 comparisons (5 models x V1 and V2 excluding label-flagged images). "
          "A model is never described as detecting anything if it is flagged degenerate.", "",
          "Runs: " + "; ".join(f"{m}: `{rows[m][1]}` (code {rows[m][2][:7]})" for m in rows), ""]

    def block(title, header, body, note=None):
        md.append(f"\n### {title}\n")
        if note:
            md.append(note + "\n")
        md.append("| " + " | ".join(header) + " |")
        md.append("|" + "|".join("---" for _ in header) + "|")
        for b in body:
            md.append("| " + " | ".join(str(x) for x in b) + " |")

    M = {m: rows[m][0] for m in rows}
    first = next(iter(M.values()))
    block("Table 1. Format pilot (20 synthetic stations, no accuracy score)", ["Model", "Compliant replies", "Failure categories", "Flagged (< 90%)"],
          [[m, _p(M[m]["pilot"]["compliant"], 2, True), json.dumps(M[m]["pilot"]["failures"]) if M[m]["pilot"]["failures"] else "none", "yes" if M[m]["pilot"]["compliant"]["p"] < 0.9 else "no"] for m in M])

    names = {"V1|all": "V1 cue-free, all kiosks", "V2|all": "V2 image descriptions, all kiosks", "V2|excl_label": "V2 excluding kiosks whose description holds the explicit 'deepfake' label (headline)",
             "V2|excl_wide": "V2 excluding kiosks whose description holds 'fake', 'scam' or 'phish'"}
    for i, (key, label) in enumerate(names.items()):
        body = []
        for m in M:
            d = M[m]["detection"].get(key)
            if not d:
                continue
            dv = d["diff_vs_best"]
            better = ("yes" if d.get("better_than_best_reference") else "no") if "p_holm" in dv else "n/a (not in family)"
            body.append([m, _p(d["failed_replies"], 3, True), ("DEGENERATE (%.0f%% UNSAFE)" % (100 * d["degenerate"]["share_unsafe"])) if d["degenerate"]["flag"] else "no",
                         _p(d["false_safe"]), _p(d["false_warning"]), f"{d['balanced_accuracy']:.3f}", f"{d['best_reference']} ({d['best_reference_balanced_accuracy']:.3f})", _ci(dv),
                         f"{dv['p_holm']:.3f}" if "p_holm" in dv else "-", better])
        ref = first["detection"][key]["references"]
        for r in REFS:
            body.append([f"reference: {r}", "-", "-", _p(ref[r]["false_safe"]), _p(ref[r]["false_warning"]), f"{ref[r]['balanced_accuracy']:.3f}", "-", "-", "-", "-"])
        block(f"Table 2{'abcd'[i]}. Detection, {label}", ["Model", "Failed replies", "Degenerate", "False-safe (attacked judged SAFE)", "False-warning (safe judged UNSAFE)", "Balanced acc.",
                                                          "Best reference (bal. acc.)", "Diff. vs best ref. [95% CI]", "Holm p", "Better than baseline"], body)

    for i, key in enumerate(("V1|all", "V2|all", "V2|excl_label")):
        body = []
        kinds = {c: first["detection"][key]["by_visible_class"][c]["kind"] for c in VISIBLE if c in first["detection"][key]["by_visible_class"]}
        for m in M:
            d = M[m]["detection"][key]["by_visible_class"]
            body.append([m] + [_p(d[c], 2, True) if c in d else "n/a" for c in kinds])
        ref = first["detection"][key]["references"]
        for r in REFS:
            body.append([f"reference: {r}"] + [_p(ref[r]["by_visible_class"][c], 2, True) if c in ref[r]["by_visible_class"] else "n/a" for c in kinds])
        block(f"Table 3{'abc'[i]}. Detection error by visible-cue class, {names[key]}", ["Model"] + [f"{c} ({'false-safe' if k == 'false_safe' else 'false-warning'})" for c, k in kinds.items()], body,
              note="Cell = error rate with Wilson 95% interval and count. Attacked classes: false-safe (attacked kiosk judged SAFE). Safe classes: false-warning (safe kiosk judged UNSAFE).")

    for i, key in enumerate(("V1|all", "V2|excl_label")):
        body = [[m] + [_p(M[m]["detection"][key]["recall_by_hidden_mode"][h], 2, True) if h in M[m]["detection"][key]["recall_by_hidden_mode"] else "n/a" for h in ("reduced", "blocked")] for m in M]
        block(f"Table 4{'ab'[i]}. Recall on attacked kiosks by hidden attack mode, {names[key]}", ["Model", "reduced", "blocked"], body,
              note="Measures recall on attacked kiosks with the cues they happen to show, not recognition of the mode (the modes are consequences after charging).")

    for i, key in enumerate(("V1|all", "V2|all", "V2|excl_label")):
        body = []
        for m in M:
            d = M[m]["recommendation"][key]
            mx, bn, aa = d["mixed"], d["benign"], d["all_attacked"]
            body.append([m, ("DEGENERATE (%s %.0f%%)" % (d["degenerate"].get("top_choice"), 100 * d["degenerate"]["top_share"])) if d["degenerate"]["flag"] else "no",
                         _p(mx["safe"], 2, True), _p(mx["attacked"], 2, True), _p(mx["skip"], 2, True), f"{mx['random_choice_safe_rate']:.3f}",
                         "above" if mx["safe_choice_interval_above_random"] else ("below" if mx["safe_choice_interval_below_random"] else "overlaps"),
                         _p(bn["skip"], 2, True), _p(aa["skip"], 2, True), _p(aa["attacked"], 2, True), _p(d["failed_replies"], 2, True)])
        body.append(["reference: always SKIP", "-", "0.000", "0.000", "1.000", "-", "-", "1.000", "1.000", "0.000", "-"])
        block(f"Table 5{'abc'[i]}. Recommendation by station type, {names[key]}", ["Model", "Degenerate", "Mixed: safe kiosk chosen", "Mixed: attacked kiosk chosen", "Mixed: SKIP", "Random-choice safe rate",
                                                                                      "Safe-choice interval vs random", "Benign: SKIP (over-caution)", "All-attacked: SKIP (protective)", "All-attacked: attacked kiosk chosen", "Failed replies"], body)

    body = []
    for m in M:
        for v in ("V1", "V2"):
            c = M[m]["consistency"].get(v)
            if not c or not c["detection_per_seed"]:
                continue
            fs = [x["false_safe"] for x in c["detection_per_seed"]]
            fw = [x["false_warning"] for x in c["detection_per_seed"]]
            ag = c["agreement"]
            body.append([m, v, f"{len(fs)}", f"{np.mean(fs):.3f} [{min(fs):.3f}, {max(fs):.3f}]", f"{np.mean(fw):.3f} [{min(fw):.3f}, {max(fw):.3f}]",
                         f"{sum(x['degenerate'] for x in c['detection_per_seed'])}/{len(fs)}",
                         _p(ag["detection"]["identical_across_5_seeds"], 3) if "detection" in ag else "-", f"{ag['detection']['mean_pairwise_agreement']:.3f}" if "detection" in ag else "-",
                         _p(ag["recommendation"]["identical_across_5_seeds"], 3) if "recommendation" in ag else "-"])
    block("Table 6. Consistency at temperature 0.3, seeds 1 to 5", ["Model", "Variant", "Seeds scored", "False-safe mean [min, max]", "False-warning mean [min, max]", "Degenerate seeds (detection)",
                                                                       "Detection: identical across seeds", "Detection: mean pairwise agreement", "Recommendation: identical across seeds"], body,
          note="Empty if the consistency pass has not been run or registered.")

    body = []
    for m in M:
        t, vr = M[m]["timing_accuracy_pass"], M[m]["vram_and_runtime"] or {}
        body.append([m, f"{t['calls']}", f"{t['median_server_ms']:.0f}", f"{t['p95_server_ms']:.0f}", f"{t['median_wall_s']:.2f}", t["errors"], f"{M[m]['first_call_load_ms'] / 1000:.1f}",
                     vr.get("peak_vram_mib"), vr.get("vram_added_mib")])
    block("Table 7. Latency and memory (accuracy pass, temperature 0)", ["Model", "Calls", "Median server ms", "p95 server ms", "Median wall s", "Call errors", "First-call load s", "Peak VRAM MiB", "VRAM added MiB"], body)
    out = results / "master_table_gate5.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    {"register": register_all, "table": build}[sys.argv[1]]()
