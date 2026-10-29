"""Results chapter draft, generated from the experiment registry.

Every number in the chapter is read from `results/registry.csv` and the run folders, or (for the Gate 0 audit figures, which predate
the registry) parsed from `docs/audit/GATE0_audit.md`; the static text contains no result numbers. Wording follows the claims register
of `FINAL_REPORT.md`: associations only, no causal language.

  python -m backend.pipeline.gate7.build_results_chapter     ->  docs/report/RESULTS_CHAPTER_DRAFT.md
"""
import re

from ..gate2.benchmark import load_gate3
from ..gate2.config import REPO_ROOT
from .build_final_report import LEARNERS, SETS, SIMPLE_LEARNER, SIMPLE_SET, SLMS, Reg, ci, f, pp, table


class Ctx:
    """Loads the latest registered run per experiment name once and records which run ids the chapter used."""

    def __init__(self, results_dir=None, audit=None):
        self.R = Reg(load_gate3() if results_dir is None else None, results_dir)
        self.runs = {}
        self.audit = " ".join((audit or REPO_ROOT / "docs" / "audit" / "GATE0_audit.md").read_text(encoding="utf-8").split())

    def get(self, name):
        s, eid = self.R.latest(name)
        self.runs[name] = eid
        return s["metrics"] if "metrics" in s else s

    def audit_match(self, pattern):
        m = re.search(pattern, self.audit)
        if not m:
            raise ValueError(f"Gate 0 audit figure not found: {pattern}")
        return m.groups()


def s1_audit(c):
    """Audit and label redefinition: the original label follows exposure."""
    r0, n0, nrows, share0, r1, r2, r3 = c.audit_match(r"0 attacked -> ([\d.]+)% \(([\d,]+) of ([\d,]+) rows, ([\d.]+)%.*?\), 1 -> ([\d.]+)%, 2 -> ([\d.]+)%, 3 -> ([\d.]+)%")
    a_all, a_ch = c.audit_match(r"([\d.]+) over all rows, ([\d.]+) among charge decisions")
    at_att, at_exp = c.audit_match(r"([\d.]+)% of charge decisions were at an attacked kiosk against roughly ([\d.]+)%")
    nskip, = c.audit_match(r"all ([\d,]+) skips are non-risky")
    a_charged, = c.audit_match(r"AUROC ([\d.]+) \(computed from the class counts\)")
    w_all, w_ch = c.audit_match(r"pooled descriptive AUROC ([\d.]+) over all rows but ([\d.]+) among charge decisions")
    ng, g_lo, g_hi = c.audit_match(r"Among the ([\d,]+) charge rows with gaze, descriptive per-feature AUROC for risky is ([\d.]+)-([\d.]+)")
    b_pt, b_lo, b_hi, bg_pt, bg_lo, bg_hi = c.audit_match(r"behaviour-only AUROC ([\d.]+) \[([\d.]+), ([\d.]+)\]; behaviour\+gaze ([\d.]+) \[([\d.]+), ([\d.]+)\]")
    a = c.get("h1_claim_a")["primary"]
    s5 = c.get("g6_s5_skip_vs_charge")["descriptive_skip_by_exposure"]
    cells = [x for x in s5 if x["n_attacked"] is not None]
    types = [x for x in s5 if x["n_attacked"] is None]

    md = ["## 1. Audit and the redefinition of the target", "",
          "The first analysis step was a read-only audit of the repository and the data (Gate 0). Its central finding is that the original "
          "\"risky decision\" label is largely associated with how many kiosks were attacked at the station, which is randomised by the layout and logged "
          "before the participant decides.", "",
          *table(["Attacked kiosks at the station", "Share of decisions labelled risky"],
                 [["0", f"{r0}% ({n0} of {nrows} rows, {share0}%; risky is impossible)"], ["1", f"{r1}%"], ["2", f"{r2}%"], ["3", f"{r3}%"]]), "",
          f"The number of attacked kiosks alone separates risky from non-risky decisions with a descriptive AUROC of {a_all} over all rows and {a_ch} among charge decisions "
          f"(Gate 0 audit, section 0). Participants did not avoid attacked kiosks: {at_att}% of charge decisions were at an attacked kiosk, against roughly {at_exp}% "
          "expected if an available kiosk had been chosen at random (approximate).", "",
          f"The earlier behaviour-only AUROC of {b_pt} [{b_lo}, {b_hi}] (behaviour plus gaze {bg_pt} [{bg_lo}, {bg_hi}]) is largely a skip-versus-charge detector: "
          f"the label requires a charge, so all {nskip} skips are non-risky, and a score that knew only whether the participant charged would reach an AUROC of {a_charged}. "
          f"Window duration has a pooled descriptive AUROC of {w_all} but {w_ch} among charge decisions, which is chance. "
          f"Among the {ng} charge rows with gaze, the six gaze features have descriptive per-feature AUROCs of {g_lo} to {g_hi} for the original label.", "",
          "**The target was therefore redefined after the data had been seen.** The primary target is whether the chosen kiosk is attacked, given a charge at a station "
          f"that has at least one attacked and at least one safe available kiosk, with the share of attacked kiosks entering as an exposure offset. The primary set has {a['n_rows']} rows from "
          f"{a['n_participants']} participants and {a['n_events']} events (chosen kiosk attacked). The redefinition was not blind: Gate 0 looked at the same rows that the later gates reuse, "
          "and no untouched test set exists.", "",
          f"Skipping a station is not associated with exposure in the way an informed response would be: across the {len(cells)} cells of attacked-by-available kiosks the skip rate ranges from "
          f"{min(x['skip_rate'] for x in cells):.3f} to {max(x['skip_rate'] for x in cells):.3f}, with no rise at stations where nothing is attacked or fall at stations where everything is attacked, "
          "and the intervals overlap. By station type:", "",
          *table(["Station type", "Visits", "Participants", "Skips", "Skip rate [95% CI]"],
                 [[x["meaning"].replace("station type: ", "").replace("_", "-"), x["visits"], x["participants"], x["skips"], f"{x['skip_rate']:.3f} [{x['lo']:.3f}, {x['hi']:.3f}]"] for x in types]), "",
          "(Run `g6_s5_skip_vs_charge`; see the Gate 6 report for why this comparison is not a gaze result.)", ""]
    return md


def s2_h1(c):
    """Primary hypothesis H1 (Gate 2)."""
    a, b = c.get("h1_claim_a"), c.get("h1_claim_b")
    pa = a["primary"]
    d = b["delta_auroc"]["BG_minus_B"]
    m = b["metrics"]
    sens = a["sensitivity"]
    lower = all(x.get("sigma_at_lower_bound") for x in [pa, *(v for v in sens.values() if isinstance(v, dict))])
    rows = [["Primary set", pa["n_rows"], pa["n_participants"], pa["n_events"], f"{pa['lrt']['stat']:.2f}", f"{pa['lrt']['p']:.3f}"]]
    for key, lab in (("E2_drop_duplicate_folder_participants", "Participants with more than one session folder removed (E2)"),
                     ("S4_at_least_200_valid_gaze_samples", "At least 200 valid gaze samples in the window (S4)"),
                     ("S3_drop_rag_contaminated_sessions", "Sessions with a contaminated assistant memory removed (S3)")):
        x = sens[key]
        rows.append([lab, x["n_rows"], x["n_participants"], x["n_events"], f"{x['lrt_stat']:.2f}", f"{x['p']:.3f}"])
    md = ["## 2. Primary hypothesis H1: does gaze add to behaviour and exposure?", "",
          "H1 was fixed in Protocol v1 before the analysis and has two parts, both of which must hold: (A) a likelihood-ratio test of the six gaze features in a random-intercept "
          "logistic model that already contains the exposure offset, the design variables and the behaviour variables, and (B) a participant-grouped out-of-sample comparison of behaviour "
          "plus gaze against behaviour alone. Methods: marginal maximum likelihood with Gauss-Hermite quadrature [CITE: mixed-effects logistic regression], repeated nested "
          "participant-grouped cross-validation, participant-level bootstrap [CITE: cluster bootstrap], block permutation of gaze across participants.", "",
          f"- Claim A: LRT chi-square {pa['lrt']['stat']:.2f} on {pa['lrt']['df']:.0f} df, p = {pa['lrt']['p']:.3f}; participant-block permutation p = {a['permutation_lrt']['p']:.3f} (run `h1_claim_a`).",
          f"- Claim B: mean out-of-fold AUROC {ci(m['B']['auroc'], m['B']['auroc_ci'])} for behaviour and {ci(m['BG']['auroc'], m['BG']['auroc_ci'])} for behaviour plus gaze; "
          f"difference {d['point']:+.3f} [{d['ci'][0]:+.3f}, {d['ci'][1]:+.3f}]; permuted-gaze control p = {b['permutation']['p_auc_BG_ge_obs']:.3f} (run `h1_claim_b`).",
          "- By the rule in the protocol, H1 is supported only if both claims hold. Neither does: **H1 is not supported.**", "",
          "Pre-specified sensitivity analyses (likelihood-ratio test of the same six gaze features):", "",
          *table(["Subset", "Rows", "Participants", "Events", "LRT chi-square", "p"], rows), "",
          "The subset without contaminated assistant memory has fewer rows, a higher test statistic and a smaller p-value than the primary analysis. This is one of three pre-specified "
          "sensitivity analyses and is not corrected for multiple comparisons; it is reported as a hypothesis for new data, not as a finding. "
          + ("In every one of these fits the random-intercept variance estimate is at its lower bound, so the models are close to ordinary logistic regression." if lower else
             "The random-intercept variance estimate is above its lower bound in some of these fits."), ""]
    return md


def s3_ml(c):
    """ML benchmark (Gate 3)."""
    g3 = {k: c.get(f"g3_grid_{k}") for k, _ in LEARNERS}
    s1, s2, s8 = c.get("g3_secondary_S1"), c.get("g3_secondary_S2"), c.get("g3_exploratory_S8")
    names = dict(LEARNERS)
    rows, cand = [], []
    for k, name in LEARNERS:
        m = g3[k]
        for st in SETS:
            pt, ic = m["point"][st], m["ci"][st]["auroc"]
            rows.append([name, st, ci(pt["auroc"], ic), f(pt["brier"]), f(pt["calib_slope"], 2), f(pt["false_safe_B"], 2), f(pt["false_warning_B"], 2)])
            cand.append(dict(learner=k, set=st, auroc=pt["auroc"], ci=ic))
    best = max(cand, key=lambda x: x["auroc"])
    tied = [x for x in cand if x["ci"][1] >= best["ci"][0] and x["ci"][0] <= best["ci"][1]]
    simple = min(tied, key=lambda x: (SIMPLE_SET[x["set"]], SIMPLE_LEARNER[x["learner"]]))
    pr, neg = [], []
    for k, name in LEARNERS:
        for key, lab in (("B_minus_B0", "B - B0"), ("G_minus_B0", "G - B0"), ("BG_minus_B0", "BG - B0")):
            x = g3[k]["paired"][key]["auroc"]
            if x["ci"][1] < 0:
                neg.append(f"{name}, {lab}")
            pr.append([name, lab, f"{x['mean']:+.3f} [{x['ci'][0]:+.3f}, {x['ci'][1]:+.3f}]"])
    md = ["## 3. Machine-learning benchmark", "",
          "Three learners (ridge with the exposure offset, random forest, gradient boosting) were compared on four feature sets with the same participant-grouped nested cross-validation: "
          "B0 (exposure and design only), B (adds behaviour), G (adds gaze to B0) and BG (behaviour and gaze). Metrics are mean out-of-fold AUROC with a 95% participant-level bootstrap "
          "interval; Brier score and calibration slope describe probability quality; the last two columns give the error rates at the operating point chosen for a recall of 0.80 "
          "in the training folds, reported together because lowering one raises the other.", "",
          *table(["Learner", "Set", "AUROC [CI]", "Brier", "Calibration slope", "False-safe at recall-0.80 point", "False-warning at that point"], rows), "",
          "Paired AUROC differences to the exposure-only set B0 (participant bootstrap):", "",
          *table(["Learner", "Contrast", "Difference [CI]"], pr), "",
          f"- The highest mean AUROC is {names[best['learner']]} with set {best['set']}, {ci(best['auroc'], best['ci'])}. {len(tied)} of {len(cand)} model-set pairs have an interval that overlaps it. "
          f"Under the tie rule fixed in the protocol (simpler model wins) the **best predictive model is {names[simple['learner']]} with set {simple['set']}**, AUROC {ci(simple['auroc'], simple['ci'])}"
          + (", which is the exposure-only reference: it contains no behaviour, gaze or EEG feature." if simple["set"] == "B0" else "."),
          f"- Gaze alone against exposure (S1): LRT p = {s1['lrt']['p']:.3f}, AUROC difference {s1['delta_auroc']['mean']:+.3f} [{s1['delta_auroc']['ci'][0]:+.3f}, {s1['delta_auroc']['ci'][1]:+.3f}], permutation p = {s1['permutation']['p']:.3f}.",
          f"- Early window only, the first {s2['early_window_s']:.0f} s of the decision window (S2): LRT p = {s2['lrt']['p']:.3f}, AUROC difference {s2['delta_auroc_BGE_minus_BE']['mean']:+.3f} "
          f"[{s2['delta_auroc_BGE_minus_BE']['ci'][0]:+.3f}, {s2['delta_auroc_BGE_minus_BE']['ci'][1]:+.3f}].",
          f"- Does any pre-specified model beat B0 with an interval above zero? {'Yes' if s8['any_prespecified_model_beats_B0_with_ci_above_zero'] else 'No'}.", "",
          (f"Contrasts with an interval entirely below zero: {', '.join(neg)}; in these cases the extra features are associated with a lower AUROC than B0 in this sample, "
           "which is what fitting noise features would look like, not evidence that the features are harmful. " if neg else "No contrast to B0 has an interval entirely below zero. ")
          + "The error rates at the recall-0.80 point show that every model pays for its recall with a high false-warning rate, "
          "and no operating point was validated on separate data.", ""]
    return md


def s4_eeg(c):
    """EEG on the matched subset (Gate 4, exploratory) and the selection-bias report."""
    s6, sel, det = c.get("g4_s6_ridge"), c.get("g4_selection_bias"), c.get("g6_eeg_detrended")
    cv, cn = sel["coverage"], sel["counts"]
    row = {x["variable"].split(" (")[0]: x for x in sel["row_level"]}
    pl = {x["variable"]: x for x in sel["participant_level"]}
    tr, per = row["trial_index"], pl["period"]
    pe = s6["point"]
    pairs = [(k, s6["paired"][k]["auroc"]) for k in s6["paired"] if k.startswith("BGE") or k == "BG_minus_B"]
    d_ = det["primary_BGE_detrended_minus_BG"]["auroc"]
    md = ["## 4. EEG on the matched subset (exploratory)", "",
          "EEG was never a primary question. The four-channel consumer headset gives a minimal feature set (relative band power per channel in low-motion samples), and EEG exists "
          "only for part of the sessions. The comparison is therefore restricted to **primary-set rows that also have EEG features**, so every feature set is evaluated on identical rows: "
          f"{s6['n_rows']} rows from {s6['n_participants']} participants and {s6['n_events']} events (run `g4_s6_ridge`). The full cohort funnel is in `docs/audit/EEG_COHORT_FUNNEL.md`.", "",
          *table(["Feature set", "AUROC [CI]"], [[st, ci(pe[st]["auroc"], s6["ci"][st]["auroc"])] for st in ("B0", "B", "BG", "BGE") if st in pe]), "",
          *[f"- {k.replace('_minus_', ' minus ')} ({'primary contrast' if k == 'BGE_minus_BG' else 'exploratory, not corrected for multiple comparisons'}): {x['mean']:+.3f} [{x['ci'][0]:+.3f}, {x['ci'][1]:+.3f}]" for k, x in pairs],
          f"- Likelihood-ratio test of the EEG block (descriptive only, {s6['lrt_BGE_vs_BG']['df']:.0f} df on {s6['n_events']} events): p = {s6['lrt_BGE_vs_BG']['p']:.3f}; Holm upper bound "
          f"{s6['holm_provisional']['S6']['holm_adjusted_upper_bound']:.3f}; permutation p for the BGE AUROC = {s6['permutation']['p']:.3f}.",
          f"- With each EEG feature detrended on trial index inside the training folds (a post-hoc check, Gate 6): BGE minus BG {d_['mean']:+.3f} [{d_['ci'][0]:+.3f}, {d_['ci'][1]:+.3f}].", "",
          "**Selection.** The matched rows are not a random subset of the primary set:", "",
          f"- {100 * cv['share_after_eeg_end']:.1f}% of the decision windows of the {cv['n_participants']} participants with a confirmed recording start after that recording ended; "
          f"the median trial index is {cv['median_trial_usable']:.0f} for rows with usable EEG and {cv['median_trial_after_end']:.0f} for rows after the end.",
          f"- Standardised mean difference in trial index, matched minus other primary rows: {tr['smd']:+.2f} [{tr['smd_ci'][0]:+.2f}, {tr['smd_ci'][1]:+.2f}].",
          f"- Collection period differs between matched and other participants (Benjamini-Hochberg adjusted p = {per['fdr_bh']:.3f}) [CITE: Benjamini-Hochberg false discovery rate].",
          f"- Matched and other primary rows share {cn['participants_in_both']} participants; outcome rates are {sel['outcome']['event_rate_matched']:.3f} (matched) and {sel['outcome']['event_rate_other']:.3f} (other).", "",
          "**Reading.** Adding EEG to behaviour and gaze is associated with a small positive difference in AUROC whose interval includes zero, and the one contrast whose interval excludes zero "
          "(BGE minus B) is exploratory and was not designated primary. With " + str(s6["n_events"]) + f" events the bootstrap standard error of the primary contrast is {s6['paired']['BGE_minus_BG']['auroc']['se']:.3f}, "
          "so differences of a few hundredths of AUROC cannot be told apart from zero and the result is **not established**, which is different from \"no effect\". Whether EEG adds information would need whole-session recordings and a pre-registered analysis; consumer-grade EEG "
          "during driving and head movement is also exposed to motion and muscle artefacts [CITE: consumer EEG artefacts in mobile settings].", ""]
    return md


def s5_slm(c):
    """Small language models (Gate 5): detection, recommendation, consistency and the malicious-override condition."""
    M = {m: c.get("g5_slm_" + m.replace(":", "_")) for m in SLMS}
    X = {m: c.get("g5_malicious_" + m.replace(":", "_")) for m in SLMS}
    m0 = M[SLMS[0]]
    d1, d2 = m0["detection"]["V1|all"], m0["detection"]["V2|excl_label"]
    rec = m0["recommendation"]["V1|all"]
    ref_names = ["always SAFE", "always UNSAFE", "deepfake-image rule", "discount-badge rule", "random (expected)"]

    def det_rows(key):
        out = []
        for m in SLMS:
            d = M[m]["detection"][key]
            out.append([m, pp(d["false_safe"], 2), pp(d["false_warning"], 2), f(d["balanced_accuracy"]), "yes" if d["degenerate"]["flag"] else "no", pp(d["failed_replies"], 2)])
        return out

    def ref_rows(d):
        return [[n, pp(d["references"][n]["false_safe"], 2), pp(d["references"][n]["false_warning"], 2), f(d["references"][n]["balanced_accuracy"])] for n in ref_names if n in d["references"]]

    n_st = rec["mixed"]["n"] + rec["benign"]["n"] + rec["all_attacked"]["n"]
    fw2 = [M[m]["detection"]["V2|excl_label"]["false_warning"]["p"] for m in SLMS]
    md = ["## 5. Small language models as kiosk-risk detectors and recommenders", "",
          f"This track is separate from the machine-learning track and is never pooled with it. Five locally run models ({', '.join(SLMS)}) received a text description of a charging station and "
          f"answered two tasks: **detection** (mark each kiosk SAFE or UNSAFE) and **recommendation** (choose a kiosk or skip). The scenario set has {n_st} stations "
          f"({rec['benign']['n']} benign, {rec['all_attacked']['n']} with every kiosk attacked, {rec['mixed']['n']} mixed) and {d1['n_kiosks']} kiosks, was quota-sampled from the experiment "
          "and is text-only; the labels come from the simulator ground truth. Two prompt variants are reported separately: **V1** is cue-free (no image description), **V2** adds a description "
          "of each kiosk image produced by another model. Results are not averaged across variants.", "",
          "Detection is judged by the false-safe rate (an attacked kiosk called SAFE) and the false-warning rate (a legitimate kiosk called UNSAFE) **together**, and by balanced accuracy, "
          "against simple rule baselines and constant answers, with 95% Wilson intervals [CITE: Wilson score interval].", "",
          "**Detection, V1 (cue-free)**", "",
          *table(["Model", "False-safe", "False-warning", "Balanced accuracy", "Degenerate", "Failed replies"], det_rows("V1|all")), "",
          "**Reference answers on the same V1 kiosks**", "",
          *table(["Reference", "False-safe", "False-warning", "Balanced accuracy"], ref_rows(d1)), "",
          f"The best reference is the {d1['best_reference']} (balanced accuracy {f(d1['best_reference_balanced_accuracy'])}). No model reaches it: the highest model balanced accuracy is "
          f"{f(max(M[m]['detection']['V1|all']['balanced_accuracy'] for m in SLMS))}, and a constant answer of SAFE scores {f(d1['references']['always SAFE']['balanced_accuracy'])}. "
          "Without a description most attacked kiosks are called SAFE, so the models are not useful detectors in this setting.", "",
          "**Detection, V2 (image descriptions; kiosks whose description names the attack label are excluded; this is the pre-committed headline)**", "",
          *table(["Model", "False-safe", "False-warning", "Balanced accuracy", "Degenerate", "Failed replies"], det_rows("V2|excl_label")), "",
          *table(["Reference", "False-safe", "False-warning", "Balanced accuracy"], ref_rows(d2)), "",
          f"The best reference here is again the {d2['best_reference']} ({f(d2['best_reference_balanced_accuracy'])}). **Caveat on V2:** the description can state or hint at the image type, "
          "which is itself a strong cue and is the basis of the best rule, so V2 does not measure detection from the screen alone. The false-safe rate falls in V2 "
          f"but the false-warning rate rises to between {f(min(fw2), 2)} and {f(max(fw2), 2)}: the models warn on most kiosks that have a description. "
          "**No model showed reliable detection above the rule baselines in either variant**, and no best model is claimed (the model that the pre-committed rule selects differs between the variants).", ""]
    above = any(M[m]["recommendation"][k]["mixed"].get("safe_choice_interval_above_random") for m in SLMS for k in ("V1|all", "V2|excl_label"))
    max_skip = max(M[m]["recommendation"][k]["all_attacked"]["skip"]["p"] for m in SLMS for k in ("V1|all", "V2|excl_label"))
    rows = []
    for m in SLMS:
        for key in ("V1|all", "V2|excl_label"):
            r = M[m]["recommendation"][key]
            mx = r["mixed"]
            rows.append([m, key.split("|")[0], pp(mx["safe"], 2), pp(mx["attacked"], 2), pp(mx["skip"], 2), f(mx["random_choice_safe_rate"]), pp(r["all_attacked"]["attacked"], 2)])
    md += ["**Recommendation.** At mixed stations a recommender that ignored the content would choose a safe kiosk at the random-choice rate shown. At stations where every kiosk is attacked, "
           "the last column shows how often an attacked kiosk was still chosen instead of skipping.", "",
           *table(["Model", "Variant", "Safe kiosk chosen", "Attacked kiosk chosen", "Skip", "Random-choice safe rate", "All-attacked: attacked kiosk chosen"], rows), "",
           ("The pre-committed comparison finds no model whose interval for the share of safe choices lies above the random-choice rate" if not above else
            "In the pre-committed comparison some interval for the share of safe choices lies above the random-choice rate (see the table)")
           + f"; at all-attacked stations the highest skip share is {max_skip:.2f}. "
           + ("The recommendation task therefore also shows no reliable benefit." if not above else "This needs a separate reading."), ""]
    rows = []
    for m in SLMS:
        for v in ("V1", "V2"):
            cs = M[m]["consistency"].get(v)
            if not cs or not cs["detection_per_seed"]:
                continue
            fs = [x["false_safe"] for x in cs["detection_per_seed"]]
            rows.append([m, v, len(fs), f"{sum(fs) / len(fs):.3f} [{min(fs):.3f}, {max(fs):.3f}]", f"{sum(x['degenerate'] for x in cs['detection_per_seed'])}/{len(fs)}", f"{cs['agreement']['detection']['mean_pairwise_agreement']:.3f}"])
    md += ["**Consistency.** The detection task was repeated with five seeds at temperature 0.3 on the same items:", "",
           *table(["Model", "Variant", "Seeds", "False-safe mean [min, max]", "Degenerate seeds", "Mean pairwise agreement"], rows), "",
           "Rates are stable across seeds, so the results above do not depend on one sampling draw; stability does not make a detector accurate.", ""]
    rows = []
    for m in SLMS:
        for v in ("V1", "V2"):
            x = X[m][v]
            dd = x["difference_in_compliance"]
            rows.append([m, v, pp(x["with_override"]["target"], 2), pp(x["without_override"]["target"], 2), f"{dd['point']:+.2f} [{dd['lo']:+.2f}, {dd['hi']:+.2f}]", x["label"]])
    md += ["**Malicious-override condition (instruction-following only).** On 60 designated mixed stations the prompt was run with and without an experimenter instruction to recommend a named attacked kiosk. "
           "This measures whether a model follows an instruction placed in its prompt. It says nothing about the in-game assistant, which was not tested, and nothing about whether participants would follow such advice.", "",
           *table(["Model", "Variant", "Target chosen with the instruction", "Target chosen without", "Difference [CI]", "Label"], rows), "",
           "The override condition was rerun under a scoring rule written before scoring (Amendment A2) after a provisional look at an earlier run; see the deviations below.", ""]
    return md


def s6_limits(c):
    """Limitations, written as statements of what the design allows."""
    return ["## 6. Limitations", "",
            "- **No untouched test set.** Earlier analysis rounds (D045 to D063) iterated on the same participants, and the later gates reuse the same rows. Every result here is pre-specified but exploratory, "
            "and a confirmatory claim would need new data or a pre-registered analysis.",
            "- **The target was redefined after the data had been seen** (Gate 0), so the redefinition was not blind. The choice was motivated by the audit finding that the original label follows exposure.",
            "- **The best predictive model is the exposure-only reference.** No behaviour, gaze or EEG feature set was associated with better out-of-sample discrimination than exposure and design alone, "
            "so the benchmark does not support any learned detector.",
            "- **Power.** The primary set has a few hundred rows and a couple of hundred events; the EEG subset has about a third of the rows. Intervals around AUROC differences are wide, so the results are "
            "\"not detected\", which is different from \"no effect\".",
            "- **EEG selection and quality.** The matched subset favours early stations and a particular collection period; the headset has four channels, minimal preprocessing was applied, and the "
            "window is defined by the decision event.",
            "- **The decision window ends at the choice.** Window duration and gaze counts are therefore mechanically linked to skip versus charge, which is why the redefined target conditions on a charge.",
            "- **The assistant was not logged.** The in-game assistant replies and the benign or malicious condition are not in the data, so their association with decisions cannot be assessed.",
            "- **Several grids chose their weakest setting**; a wider ridge grid gave the same conclusion, but tuning remains a limited part of the picture.",
            "- **Language-model scenario set.** Quota-sampled, text-only, one main decoding setting, image descriptions written by another model; the investigators were not blind to the labels. "
            "The results do not transfer to a deployed assistant or to human behaviour.",
            "- **Multiplicity.** Many strata and sensitivity runs were made; unadjusted p-values are descriptive. Where a Holm bound or an FDR value is given, it covers only the family named.",
            ""]


def s7_design(c):
    """Recommended design for the next data collection."""
    return ["## 7. Recommended design for new data collection", "",
            "The existing data cannot answer whether gaze, EEG or an assistant changes risky decisions. A new study could:", "",
            "1. Pre-register the scenario set, the primary outcome, the exclusion rules and the analysis, and keep a held-out set of participants untouched until the analysis is fixed.",
            "2. Randomise three assistant conditions (no assistant, correct recommendation, malicious recommendation) and **log the assistant replies and the condition for every decision**.",
            "3. Log head pose and the world positions of the kiosks, so gaze can be mapped to areas of interest without video.",
            "4. Record decision latency and pre-decision gaze as defined measures with the decision window fixed before the outcome is known.",
            "5. Record EEG for the whole session with start and end markers, check signal quality online, and report the usable sample before analysis.",
            "6. Counterbalance trial order and kiosk layout so exposure is not confounded with position, time or collection period.",
            "7. Use a sample size justified by the smallest difference of interest rather than by availability.",
            "8. Evaluate any language-model assistant with people, not only with scripted prompts [CITE: automation bias in decision support].",
            ""]


SECTIONS = [s1_audit, s2_h1, s3_ml, s4_eeg, s5_slm, s6_limits, s7_design]


def build(results_dir=None, out=None, audit=None):
    """results_dir, out and audit default to the repository's files; a test passes a frozen fixture."""
    c = Ctx(results_dir, audit)
    body = []
    for sec in SECTIONS:
        body += sec(c)
    head = ["# Results chapter (draft, generated)", "",
            "Generated by `backend/pipeline/gate7/build_results_chapter.py` from `results/registry.csv` and the run folders; do not edit by hand. "
            "No result number is typed in; the Gate 0 audit figures are parsed from `docs/audit/GATE0_audit.md`. "
            "All statements are associations in a small, mostly exploratory sample; the wording follows the claims register of `FINAL_REPORT.md`.", "",
            "Registry runs used: " + "; ".join(f"`{v}`" for v in c.runs.values()), ""]
    md = head + body
    text = "\n".join(md) + "\n"
    cites = sorted(set(re.findall(r"\[CITE[^\]]*\]", text)))
    if cites:
        text += "\n## Citation placeholders\n\n" + "\n".join(f"- {x}" for x in cites) + "\n"
    out = out or REPO_ROOT / "docs" / "report" / "RESULTS_CHAPTER_DRAFT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))      # bytes, so the file (and its checksum) is the same on every platform
    print("wrote", out)


if __name__ == "__main__":
    build()
