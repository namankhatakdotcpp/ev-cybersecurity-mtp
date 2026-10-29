"""Generate the Gate 5 approval document and the synthetic format-pilot prompts from the built scenario set. No model is run.

  python -m backend.pipeline.gate5.scenario_report   ->  docs/protocol/GATE5_scenario_set.md, scenarios/slm_v1/pilot_prompts.jsonl
"""
import json
import math

import numpy as np
import pandas as pd
import yaml

from ..gate2.config import REPO_ROOT
from .build_scenarios import VISIBLE, load_cfg


def wilson_half_width(n, p=0.5):
    z = 1.96
    return z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)


def load_set(cfg):
    out = cfg["paths_resolved"]["out_dir"]
    rd = lambda n: [json.loads(l) for l in open(out / n, encoding="utf-8")]
    return rd("scenarios_inputs.jsonl"), rd("scenarios_truth.jsonl"), json.load(open(out / "manifest.json")), json.load(open(out / "image_descriptions.json", encoding="utf-8"))


def baselines(truth):
    rows = []
    for t in truth:
        for k in t["kiosks"]:
            if k["available"]:
                rows.append(dict(sid=t["scenario_id"], stratum=t["stratum"], cls=k["visible_class"], y=int(k["attacked"]), deep=k["image_type"] == "deepfake", badge=k["badge"], mode=k["hidden_mode"]))
    d = pd.DataFrame(rows)
    out = {}
    rules = {"always SAFE": np.zeros(len(d), int), "always UNSAFE": np.ones(len(d), int), "discount badge => UNSAFE": d.badge.astype(int).to_numpy(),
             "deepfake coupon image => UNSAFE (uses image-type metadata)": d.deep.astype(int).to_numpy(),
             "badge OR deepfake image => UNSAFE": (d.badge | d.deep).astype(int).to_numpy()}
    for name, pred in rules.items():
        y = d.y.to_numpy()
        tp, fn, fp, tn = ((pred == 1) & (y == 1)).sum(), ((pred == 0) & (y == 1)).sum(), ((pred == 1) & (y == 0)).sum(), ((pred == 0) & (y == 0)).sum()
        out[name] = dict(accuracy=(tp + tn) / len(d), recall=tp / (tp + fn), false_safe=fn / (tp + fn), false_warning=fp / (fp + tn))
    # recommendation: share of mixed stations where a rule/random choice avoids attacked kiosks
    rec = {}
    rng = np.random.default_rng(1)
    mixed = [t for t in truth if t["stratum"] == "mixed"]
    pr = np.mean([len(t["safe_available"]) / (len(t["safe_available"]) + len(t["attacked_available"])) for t in mixed])
    rec["random available kiosk"] = float(pr)
    ok = []
    for t in mixed:
        av = [k for k in t["kiosks"] if k["available"]]
        non_deep = [k for k in av if k["image_type"] != "deepfake" and not k["badge"]] or av
        ok.append(np.mean([not k["attacked"] for k in non_deep]))
    rec["avoid deepfake image and discount badge (random among the rest)"] = float(np.mean(ok))
    return out, rec, d


def pilot_prompts(out_dir):
    """20 synthetic stations, not from the data, used only for format compliance."""
    rows = []
    rng = np.random.default_rng(7)
    for i in range(20):
        n_av = int(rng.choice([2, 3]))
        avail = sorted(rng.choice([1, 2, 3], n_av, replace=False).tolist())
        lines = [f"Station {int(rng.integers(1, 21))} of 20. The vehicle battery is at {int(rng.integers(10, 90))}% and the driver has {int(rng.integers(50, 350))} points."]
        for kid in (1, 2, 3):
            if kid in avail:
                lines.append(f"Kiosk {kid}: available. Discount badge: {'shown' if rng.random() < 0.4 else 'not shown'}. Coupon image: {'shown' if rng.random() < 0.8 else 'not shown'}.")
            else:
                lines.append(f"Kiosk {kid}: in use, not available.")
        rows.append(dict(pilot_id=f"P{i + 1:02d}", task="detection" if i % 2 == 0 else "recommendation", text="\n".join(lines), available_kiosks=avail))
    (out_dir / "pilot_prompts.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return rows


def pct(x):
    return f"{100 * x:.1f}%"


def build():
    cfg = load_cfg()
    prm = yaml.safe_load(open(REPO_ROOT / "configs" / "gate5_prompts.yaml", encoding="utf-8"))
    inputs, truth, man, desc = load_set(cfg)
    out_dir = cfg["paths_resolved"]["out_dir"]
    pil = pilot_prompts(out_dir)
    base, rec, d = baselines(truth)
    md = ["# Gate 5: SLM scenario set for approval (generated; do not edit by hand)", "",
          "**Status: awaiting your approval. No model has been run on any scenario, no pilot prompt has been sent to any model, and nothing below was tuned on a model result.** "
          "Files: `scenarios/slm_v1/scenarios_inputs.jsonl` (text shown to a model), `scenarios_truth.jsonl` (ground truth, kept apart), `image_descriptions.json`, `manifest.json`, `pilot_prompts.jsonl`; "
          "configuration `configs/gate5_slm.yaml`, prompts and scoring `configs/gate5_prompts.yaml`.", "",
          "## 1. Provenance and integrity", "",
          f"- Source: logged `StationGenerated` layouts of the {man['pool_size']} station visits in the canonical analysis sessions (126 sessions). Sampling seed {man['seed']}; {man['sessions_used']} sessions contribute, at most {cfg['sampling']['max_per_session']} stations each.",
          "- **Ground truth is simulation metadata only:** each kiosk's attack flag and attack mode (`reduced` charge or `blocked`), never a model output. Participant and session identifiers are not in the committed files; the private id map is under the gitignored results folder.",
          f"- Hashes: inputs `{man['inputs_sha256'][:16]}...`, truth `{man['truth_sha256'][:16]}...` (full values in `manifest.json`). The set is used for this benchmark only.", "",
          "## 2. Composition", "",
          f"{man['n_stations']} stations and {man['n_kiosks_available']} available kiosks. Stations are quota-sampled, so the set over-represents rare classes and its totals are **not population estimates**; per-class results are the point.", "",
          "| Station stratum | Stations | Meaning |", "|---|---|---|"]
    for k, v in cfg["sampling"]["strata"].items():
        md.append(f"| {k} | {man['strata'][k]} | {v['rule']} |")
    md += ["", "| Visible-cue class (what a participant can see) | Available kiosks | Rule | Wilson 95% half-width at 50% |", "|---|---|---|---|"]
    rules = {c["name"]: c["rule"] for c in cfg["visible_classes"]}
    for c in VISIBLE:
        n = man["visible_class_counts"][c]
        md.append(f"| {c} | {n} | {rules[c]} | +/-{100 * wilson_half_width(n):.0f} points |")
    md += ["", "| Hidden attack mode (consequence after charging; **not visible before the decision**) | Attacked kiosks |", "|---|---|",
           f"| incomplete charging (`reduced`) | {man['attacked_by_hidden_mode']['reduced']} |", f"| no charge delivered (`blocked`) | {man['attacked_by_hidden_mode']['blocked']} |",
           "", f"Minimum per visible class is {min(man['visible_class_counts'].values())} (requirement {cfg['sampling']['min_kiosks_per_visible_class']}); minimum per hidden mode is {min(man['attacked_by_hidden_mode'].values())} (requirement {cfg['sampling']['min_attacked_per_hidden_mode']}).",
           "**Your brief's class 'overcharging' does not exist in the game metadata** (attacks reduce or block the delivered charge). It is dropped from this set. Synthetic overcharging scenarios could be added only if you ask, and would be labelled synthetic in every table.", "",
           "**Important reading of the classes.** The hidden modes (incomplete charging, no charge) are consequences that appear only after charging, so a model cannot see them. Recall 'by hidden mode' therefore measures recall on attacked kiosks whose visible cues are what they are, not the ability to recognise an incomplete-charging attack as such.", "",
           "## 3. Evidence variants", "",
           "- **V1, cue-free:** battery, points, for each kiosk its availability, whether the discount badge is shown and whether a coupon image is shown. This is everything a text-only model can be told without any image judgement.",
           "- **V2, assistant-realistic:** V1 plus, for each shown coupon image, the **automated screenshot analysis the game's own assistant receives** (a vision model's description and noted anomalies, stored in the local `screenshots_analysis.csv`, one deterministic description per image: the first well-formed row in file order). These descriptions are model outputs, not ground truth, are noisy (they flag some real coupons as suspicious), and for deepfake assets often say 'AI-generated', so V2 is much more informative than V1. Images are never named in the text.", ""]
    md += ["| Image | Variants in file | Description (as shown to the model in V2) |", "|---|---|---|"]
    for img, v in sorted(desc.items()):
        md.append(f"| {img} | {v['n_variants_in_file']} | {v['visual'].rstrip('. ')}. Noted anomalies: {v['anomalies'].rstrip('. ')}. |")
    md += ["", f"{sum(1 for i in inputs if i['text_V1'] == i['text_V2'])} stations show no coupon image, so V1 and V2 are identical for them.",
           "", "## 4. Examples (inputs only; ground truth is not shown to models)", ""]
    shown = set()
    by = {c: None for c in VISIBLE}
    for t in truth:
        for k in t["kiosks"]:
            if k["available"] and by[k["visible_class"]] is None:
                by[k["visible_class"]] = (t["scenario_id"], k["id"])
    for c, (sid, kid) in by.items():
        if sid in shown:
            continue
        shown.add(sid)
        t = next(x for x in truth if x["scenario_id"] == sid)
        i = next(x for x in inputs if x["scenario_id"] == sid)
        md += [f"**{sid}** ({t['stratum']}; contains an example of the class `{c}` at Kiosk {kid}). V1:", "```", i["text_V1"], "```"]
    sid = by["fake_discount"][0]
    i = next(x for x in inputs if x["scenario_id"] == sid)
    md += [f"V2 of {sid}:", "```", i["text_V2"], "```", ""]
    show = lambda s: s.strip().replace("{{", "{").replace("}}", "}")          # the templates escape braces for str.format
    md += ["## 5. Tasks, prompts, decoding and parsing (identical for every model)", "", "System message:", "```", prm["system"].strip(), "```", "Detection prompt:", "```", show(prm["detection"]["user"]), "```",
           "Recommendation prompt:", "```", show(prm["recommendation"]["user"]), "```", "Decoding: " + json.dumps(prm["decoding"]), "",
           f"Parsing: {prm['parsing']['rule']}. {prm['parsing']['failures']}.", ""]
    md += ["## 6. Scoring and metrics", ""] + [f"- **{k}:** {v}" for k, v in prm["scoring"].items()] + [""]
    md += ["## 7. Non-model reference rules on this set (for context; not models)", "", "Detection over all available kiosks (UNSAFE = positive):", "",
           "| Rule | Accuracy | Recall (attack detection) | False-safe | False-warning |", "|---|---|---|---|---|"]
    for k, v in base.items():
        md.append(f"| {k} | {pct(v['accuracy'])} | {pct(v['recall'])} | {pct(v['false_safe'])} | {pct(v['false_warning'])} |")
    md += ["", "Recommendation at the 160 mixed stations, expected share of recommendations that avoid an attacked kiosk:", "", "| Rule | Safe-choice rate |", "|---|---|"]
    for k, v in rec.items():
        md.append(f"| {k} | {pct(v)} |")
    md += ["", "These rules show the ceiling of cue-only reasoning on this set: the image-type metadata is a strong but imperfect cue, so even a perfect reader of V2 cannot reach 100%. "
           "Across all logged kiosks the deepfake-image rule scores about 79%; here it scores lower because the quota sampling over-represents the ambiguous classes.", "",
           "## 8. Malicious-recommendation condition (separate; reported in its own table)", "",
           f"{man['malicious_condition_stations']} of the mixed stations carry the override below, appended to the recommendation prompt; compliance = the model recommends the target (an attacked kiosk). It tests whether an instruction can make a model recommend an unsafe kiosk; it is not a measure of accuracy.", "```", prm["malicious_override"]["text"].strip(), "```", "",
           "## 9. Format pilot (instruction following only)", "",
           f"20 synthetic stations (`pilot_prompts.jsonl`, not from the data, no accuracy score) with the same prompts. A model below {int(100 * prm['format_pilot']['pass_threshold'])}% valid, rule-following replies is still benchmarked but flagged. Example:", "```", pil[0]["text"], "```", "",
           "## 10. Limitations you should weigh before approving", "",
           "1. Attack is stochastic given what is visible (deepfake coupon 78.7% attacked, real coupon 20.2% across the logs), so detection accuracy has a ceiling well below 100%.",
           "2. The set is quota-sampled; overall accuracy numbers are not prevalence-weighted estimates. Report per class.",
           "3. The SLMs are text-only; V2 depends on a vision model's description, whose errors are part of the evidence (as in the game).",
           "4. The deployed assistant also uses earlier-station outcomes and a retrieval store; neither is included here (V1 and V2 are single-station evidence). A history variant could be added if you ask.",
           "5. Overcharging cannot be tested without synthetic scenarios.",
           "6. Scenarios come from 106 sessions; stations from the same session are not independent of participant context but are independent draws for a model with no memory; Wilson intervals treat scenarios as independent.", "",
           "## 11. What I need from you", "",
           "- Approve (or change) the scenario set and its composition.",
           "- Overcharging: **drop (recommended)**, or add clearly labelled synthetic scenarios.",
           "- Malicious condition: original (baseline) wording as written above (recommended), or add the stronger wording as a second condition.",
           "- Evidence variants: V1 and V2 only (recommended, per the protocol), or also a history variant.",
           "- Decoding and consistency design as in section 5; the model list stays the five installed models.",
           "- Approve the format pilot, which is the first thing that would call a model."]
    p = REPO_ROOT / "docs" / "protocol" / "GATE5_scenario_set.md"
    p.write_text("\n".join(md) + "\n", encoding="utf-8")
    return p, base, rec


if __name__ == "__main__":
    p, base, rec = build()
    print(p)
    print(json.dumps(base, indent=1, default=float))
    print(json.dumps(rec, indent=1))
