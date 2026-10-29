"""Results chapter draft, generated from the experiment registry.

Every number in the chapter is read from `results/registry.csv` and the run folders, or (for the Gate 0 audit figures, which predate
the registry) parsed from `docs/audit/GATE0_audit.md`; the static text contains no result numbers. Wording follows the claims register
of `FINAL_REPORT.md`: associations only, no causal language.

  python -m backend.pipeline.gate7.build_results_chapter     ->  docs/report/RESULTS_CHAPTER_DRAFT.md
"""
import re

from ..gate2.benchmark import load_gate3
from ..gate2.config import REPO_ROOT
from .build_final_report import LEARNERS, SETS, SLMS, Reg, ci, f, pp, table


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


SECTIONS = [s1_audit]


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
