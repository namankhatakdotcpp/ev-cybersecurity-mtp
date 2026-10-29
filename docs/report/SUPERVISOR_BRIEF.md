# Supervisor brief: results of the gated re-analysis

Date: 2026-10-29. All statements are associations in a small, partly exploratory sample; none is causal. Numbers are from `docs/report/FINAL_REPORT.md`, which is generated from the experiment registry.

**1. The original "risky" label is largely exposure-driven.** Whether a charge decision counted as risky followed mainly from how many kiosks were attacked at that station (the layout was randomised): about 27% risky with one attacked kiosk, 62% with two, 67% with three, none with zero. Layout alone separated risky from safe charge decisions with an AUROC of 0.83. The earlier behaviour AUROC of about 0.67 was largely a skip-versus-charge detector. The target was therefore redefined: given a charge at a station that has both attacked and safe kiosks, was the chosen kiosk attacked?

**2. No gaze, behaviour or EEG feature adds detectable value on the redefined target at this sample size.** Primary set: 492 decisions from 112 participants. Adding gaze to behaviour and exposure: likelihood-ratio p = 0.226, permutation p = 0.387, out-of-sample AUROC difference +0.005 [-0.006, +0.015]; the primary hypothesis (H1) is not supported. Across ridge, random forest and boosting, no feature set beat the exposure-only baseline (AUROC about 0.63, no comparison with a confidence interval above zero). On the EEG-matched subset (150 rows, 49 participants), adding EEG gave +0.031 [-0.013, +0.070] over gaze plus behaviour. This is "not detected", not "no effect": power is limited and the EEG rows are a biased subset (earlier, mostly April sessions).

**3. Small language models.** Five models were tested on 240 text-based stations. No model showed reliable detection above the simple rule baselines (best rule about 0.72 balanced accuracy; models 0.38 to 0.56). With cue-free prompts, false-safe rates were 0.65 to 0.99. With image descriptions, false-safe rates fell, false warnings rose to 0.45 to 0.74, and the descriptions can themselves reveal the image type. Recommendations on mixed stations were near chance. When explicitly instructed to recommend an attacked kiosk, all five complied at nearly every designated station; this measures instruction-following only and says nothing about the in-game assistant. No best model is claimed. A provisional scoring look occurred before the scoring spec was fixed; this is disclosed, and the override condition was rerun and scored under a rule written first.

**4. Main limitations.** Small sample and no untouched test set (earlier decisions used the same participants); target redefined after the data were seen; the decision window ends at the choice, so duration and gaze counts are mechanically tied to skip versus charge; the assistant's replies and the benign or malicious condition were not logged; EEG recordings end early in many sessions (41% of decision windows of participants with a confirmed recording fall after it ended); the language-model scenario set is text-only and quota-sampled; many sensitivity runs, so unadjusted p-values are descriptive.

**5. Recommended design for the next data collection.**
- Log head pose and kiosk world positions, so gaze can be mapped to areas of interest without video.
- Log the assistant's responses and the benign or malicious condition for every decision, with three randomised assistant conditions.
- Record whole-session EEG with start and end markers per trial.
- Counterbalance trial order and kiosk layout, so exposure is not confounded with position and time.
- Log decision latency and pre-decision gaze as defined measures.
- Pre-register the scenario set, the primary outcome and the analysis before collecting data.

**Decision needed from you.** The repository was public until 2026-10-29 and is now private. Older files contain participant codes linked to session folder names, which embed the session date and time. Is that linkage acceptable under the consent terms, and for how long may the repository be shared? Options are in `docs/audit/LEGACY_EXPOSURE_PLAN.md`.
