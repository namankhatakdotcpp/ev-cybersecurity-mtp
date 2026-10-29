# Gate 5 report: SLM benchmark (accuracy pass)

Scored per `docs/protocol/GATE5_scoring_spec.md` (committed 07439e5, before any reply was scored). Full tables: `results/master_table_gate5.md` (generated from the registry). Scenario set, prompts and decoding are those approved in D070/D071. **Status: accuracy pass (temperature 0, seed 1) and consistency pass (5 seeds, temperature 0.3) scored; the consistency results are in section 8 (added after the pass finished, D080).** The malicious-override condition has been run (600 replies, produced outside this session) and is not scored here; it needs its own go-ahead and a rule fixed first.

Process note (D071): approval was given in chat and recorded afterwards. `score_slm.py` was written after the pass had started; its parsing rule is the one frozen in `configs/gate5_prompts.yaml` (committed before any model call), and within this session no number was looked at before the spec was committed, but see Disclosures: the user reports an earlier provisional scoring run whose numbers were seen.

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

1. Done (D080): consistency pass scored, rows re-registered, master table regenerated, section 8 added.
2. Malicious-override pass: still unscored; needs the user's go-ahead and a rule fixed first.
3. The scoring code was committed before this re-registration; the new registry rows carry the later commit.

## 8. Consistency pass (temperature 0.3, seeds 1 to 5; D080)

Master table 6. All 960 items per model were run at five seeds (4,800 replies per model). Scored under the same spec; no rule was changed after the results were seen.

- **Mean rates match the accuracy pass.** False-safe and false-warning averaged over seeds sit within about 0.02 of the temperature-0 values for every model and variant, and the range across seeds is narrow (for example llama3.1 V2 false-safe 0.401 [0.395, 0.412]; qwen2.5 V1 0.654 [0.649, 0.663]). Sampling noise at temperature 0.3 does not change any conclusion in sections 2 to 4.
- **Models are stable, not accurate.** Detection replies are identical across all five seeds for 0.82 to 1.00 of kiosks (phi3 lowest at 0.82 to 0.83; gemma2 0.996 to 1.000; qwen2.5 0.955 to 0.965). Recommendations are identical for 0.69 to 0.97 of stations (phi3 V2 lowest at 0.69). High agreement says the answers repeat, not that they are right.
- **gemma2 V1 is degenerate in all five seeds** (5 of 5): false-safe 0.993, false-warning 0.003, i.e. it answers SAFE to essentially everything. No other model-variant is degenerate in any seed.
- **mistral data note.** Its consistency file has 6,033 lines (4,799 distinct item-seed pairs; 1,234 duplicated and one pair, `V1|recommendation|S001` seed 4, absent). The duplicates come from an interrupted and resumed run; scoring keeps the first reply per item and seed (D076). One missing pair of 4,800 is not expected to move any figure, and its effect was not separately measured.
- **Latency and VRAM from this pass are not used** (three parallel workers).

**Critical review (consistency).** *Learned:* the accuracy-pass picture is not a sampling accident. *Failed or uncertain:* mistral's file irregularity; the check says nothing about other prompt wordings. *Defensible:* results are stable across seeds at temperature 0.3 and the gemma2 V1 degeneracy is reproducible. *Not defensible:* using stability as evidence of ability. *Do not test next:* more seeds or temperatures to look for a better configuration.

## Disclosures (D078, spec Amendment A1)

1. **Forking paths.** A provisional scoring run was made before the scoring spec was committed and its numbers (detection accuracy about 0.50 to 0.59, mistral V2 format breaks, 98 to 100% malicious-override compliance) were seen. The repository holds no output of that run. The spec rules were not changed afterwards; any later change will be listed in Amendment A1.
2. **Scorer written after replies existed.** The parsing rule is the one committed in `configs/gate5_prompts.yaml` before any model call, but `score_slm.py` was written after the pass started. Parsing is strict: a reply that breaks the rule is a failure, with no re-parsing and no format retries (mistral V2: 66 of 240 detection replies fail and are counted as wrong).
3. **Latency and VRAM** are from the sequential accuracy pass only (Table 7). The consistency pass uses parallel workers and the malicious pass ran next to another process using about 10 GB, so neither gives clean figures.
4. **Malicious pass** exists and is unscored.
5. **Approval.** The scenario set, pilot and accuracy pass were approved in chat; the repository has no timestamp for it (D071).
