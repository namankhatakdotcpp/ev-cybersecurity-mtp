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
    pr = []
    for k, name in LEARNERS:
        for key, lab in (("B_minus_B0", "B - B0"), ("G_minus_B0", "G - B0"), ("BG_minus_B0", "BG - B0")):
            x = g3[k]["paired"][key]["auroc"]
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
          "The random forest with behaviour or gaze features is associated with a lower AUROC than B0 in this sample, which is what over-fitting to noise features would look like; "
          "it is not evidence that the features are harmful. The error rates at the recall-0.80 point show that every model pays for its recall with a high false-warning rate, "
          "and no operating point was validated on separate data.", ""]
    return md


SECTIONS = [s1_audit, s2_h1, s3_ml]


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
