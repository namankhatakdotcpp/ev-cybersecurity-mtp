# Gate 5 report: SLM benchmark (accuracy pass)

Scored per `docs/protocol/GATE5_scoring_spec.md` (committed 07439e5, before any reply was scored). Full tables: `results/master_table_gate5.md` (generated from the registry). Scenario set, prompts and decoding are those approved in D070/D071. **Status: accuracy pass (temperature 0, seed 1) scored. The 5-seed consistency pass at temperature 0.3 is still running; Table 6 of the master table is partial and is not interpreted here.** The malicious-override condition has not been run.

Process note (D071): approval was given in chat and recorded afterwards. `score_slm.py` was written after the pass had started; its parsing rule is the one frozen in `configs/gate5_prompts.yaml` (committed before any model call), and no number was looked at before the spec was committed.

## 1. What was measured

240 stations, 599 available kiosks (quota-sampled: 40 benign, 40 all-attacked, 160 mixed). Five local models, identical prompts. UNSAFE is the positive class. A failed reply counts as wrong on every kiosk it covers. False-safe (attacked kiosk judged SAFE) and false-warning (safe kiosk judged UNSAFE) are shown together. Intervals are Wilson 95% (nominal; kiosks within a station are not independent); model-versus-reference comparisons use a scenario-level bootstrap with Holm adjustment over 10 comparisons.

## 2. Headline detection results

| Model | V1 false-safe | V1 false-warning | V1 failed replies | V2* false-safe | V2* false-warning | V2* failed replies |
|---|---|---|---|---|---|---|
| mistral:7b-instruct | 0.88 | 0.21 | 13% | 0.69 | 0.54 | 28% |
| llama3.1:8b | 0.86 | 0.14 | 0% | 0.42 | 0.45 | 2% |
| phi3:3.8b | 0.79 | 0.18 | 2% | 0.39 | 0.53 | 8% |
| gemma2:9b | **0.99 (degenerate: 1% UNSAFE)** | 0.00 | 0% | 0.33 | 0.74 | 5% |
| qwen2.5:7b | 0.65 | 0.30 | 0% | 0.41 | 0.53 | 2% |
| always SAFE | 1.00 | 0.00 | | 1.00 | 0.00 | |
| always UNSAFE | 0.00 | 1.00 | | 0.00 | 1.00 | |
| deepfake-image rule | 0.36 | 0.18 | | 0.40 | 0.16 | |
| discount-badge rule | 0.78 | 0.20 | | 0.79 | 0.20 | |

*V2 excluding kiosks whose image description holds the explicit "deepfake" label (the pre-committed headline). With the label kiosks included the picture is the same (master table 2b).

Balanced accuracy against the best reference on the same kiosks (the deepfake-image rule, 0.72 to 0.73): all five models are 0.16 to 0.34 below it in both V1 and V2*, and no CI comes near zero. **No model is better than baseline under the pre-committed rule.** Holm p-values all read 0.010, which is the floor of 2000 bootstrap resamples times 10, not a measured value.

**Supplementary, post-hoc, not in the spec:** the deepfake-image rule reads image-type metadata that the V1 text does not contain (V1 says only "Coupon image: shown"), so in V1 it is a ceiling, not an attainable baseline. Against the best attainable V1 reference (discount-badge rule, 0.511) the differences are: mistral -0.06 [-0.11, -0.01], llama -0.01 [-0.05, 0.04], phi3 +0.00 [-0.04, 0.05], gemma2 -0.01 [-0.04, 0.02], qwen +0.02 [-0.03, 0.06]. Nothing separates from a constant or cue-agnostic rule; mistral is below it. This clarifies the main result and was not used to choose anything.

## 3. By visible-cue class (Table 3)

- **V1.** Four of five models say SAFE to most attacked kiosks (false-safe 0.76 to 1.00 on `obvious_attack_deepfake`, 0.93 to 1.00 on `ambiguous_attack_real`). qwen2.5 (0.89 there) is the only model that warns more often (false-safe 0.54 to 0.59 on `fake_discount` and `obvious_attack_deepfake`), at 0.24 to 0.50 false-warning on safe classes. Nothing in V1 distinguishes the classes, which is expected: V1 carries no cue that separates attacked from safe kiosks except the discount badge and the presence of an image.
- **V2.** Models respond to the image descriptions: false-safe on `obvious_attack_deepfake` falls to 0.08 to 0.22 for four models. But false-warning rises on everything: `benign_plain` 0.43 to 0.66, `ambiguous_safe_deepfake` 0.39 to 1.00, `legitimate_discount` 0.43 to 0.87. The models warn on almost any kiosk with an image description that contains hedging language ("possible", "may be", "stylized"). That is a different behaviour from detecting attacks, and it is the same as an always-UNSAFE rule on the image-bearing kiosks. The "recall" by hidden mode (Table 4b: 0.31 to 0.67) is therefore bought with a 0.45 to 0.74 false-warning rate.
- The V2 text is another model's noisy description, so V2 measures how a small model reads that text, not attack detection. Real images whose descriptions contain "scam" or "phish" are in the set (the wider exclusion removes them; the conclusion does not change).

## 4. Recommendation (Table 5)

- **Mixed stations (160).** Chance of avoiding an attacked kiosk by random choice is 51.5%. In V1, safe-choice is 0.46 to 0.55 for four models (intervals overlap chance) and 0.37 for qwen2.5 (below chance, because it skips 18% of the time and still picks attacked kiosks 45%). In V2 the same: 0.33 to 0.56; gemma2 is below chance. **No model is above chance.**
- **Benign stations.** Skipping is over-caution; only qwen2.5 (V1, 12%) and gemma2 (V2, 50%) do it noticeably.
- **All-attacked stations.** SKIP is the only defensible answer. All five models pick an attacked kiosk 85% to 100% of the time in V1. gemma2 in V2 skips 38% there, but also skips 50% at benign stations and 37% at mixed ones, so its skipping is not tracking attacks.
- No recommendation cell is degenerate by the 95% rule.

## 5. Format and cost

Pilot compliance 95% to 100% (all above the 90% line). In the scored set mistral fails 13% (V1) to 28% (V2) of detection replies (`missing_key`, `bad_value`), phi3 8% in V2; recommendation replies never fail. Failed replies are counted as wrong, which penalises mistral's detection figures; I have not scored mistral on valid replies only, so how much of its gap is format failure is unknown. Median server time per call 0.16 to 0.36 s; peak VRAM 9.3 to 12.0 GiB (VRAM added 4.2 to 7.0 GiB).

## 6. Critical review

**What we learned.** On this scenario set, no tested SLM identifies attacked kiosks better than simple rules or constants. With only the cue-free information (V1) they mostly say SAFE and are indistinguishable from a constant. With the image descriptions (V2) they warn heavily and indiscriminately. Recommendation is at chance.

**What failed or is uncertain.** mistral's format failures; gemma2 degenerate in V1 detection; qwen2.5 below chance on mixed-station recommendation. The headline comparison against the deepfake-image rule is conservative for V1 (see supplementary result). Holm p-values are floor-bound at 0.010.

**What is defensible.** (1) No model beats the best baseline under the pre-committed rule, in either variant. (2) In V1 no model is distinguishable from the discount-badge rule or from a constant. (3) V2 false-warning is high in every safe class, so V2 recall figures must not be quoted without it. (4) Recommendation never exceeds the random-choice rate.

**What is not defensible.** Any statement that an SLM "detects" attacks; any ranking of models on overall accuracy; any V2 statement presented as attack detection; any statement about the "mode" of an attack (the modes are consequences after charging). The set is quota-sampled, text-only, single decoding configuration (temperature 0, seed 1), not blind to the investigators, and the images were described by one other model. The consistency pass is not yet available.

**What NOT to test next.** Do not tune prompts, models or thresholds on these results to find a configuration that beats the baselines (this set is now used). Do not add a combined ML+SLM table. Do not run the malicious-override condition without an explicit go-ahead. Do not pursue the label-flagged kiosks as a finding; they are a leak control.

## 7. Open items

1. Consistency pass (running); then re-register and regenerate the master table, and add the consistency paragraph to this report.
2. Decision on whether to commit the registry rows and master table after the consistency re-run (they are currently uncommitted).
3. The scoring code was committed after the pass; the registry rows made now carry commit 07439e5 (spec only). Re-registration after the code commit fixes this.
