# Decision Log — EV Charging Cybersecurity VR Project

Central record of technical/research decisions and changes. Every entry follows the same template. New decisions are appended, never silently overwrite a prior one — a reversal gets its own entry that references the one it supersedes.

Status values: Proposed · Under Investigation · Accepted · Implemented · Verified · Rejected · Reverted

---

## D001

### Date
2026-10-02

### Decision
Reframe the FPS optimization target from 120 FPS to a stable 90 FPS.

### Context / Problem
The mentor's original objective and mid-sem report state a 120 FPS target.

### Evidence
The Varjo XR-4 panel refreshes at 90 Hz (manufacturer spec, consistent with the mid-sem report's own Q33 answer). Frames rendered above a headset's refresh rate are never displayed.

### Reason
A target above what the hardware can show is not a meaningful engineering goal, and is harder to defend to a reviewer than a number tied to the actual display.

### Alternatives Considered
Keep 120 FPS as the stated target (as a performance-headroom buffer); target a lower number (e.g. 60) as a more conservative floor.

### Why Alternatives Were Not Chosen
120 FPS is not visible in the headset regardless of achieved value, so it doesn't function as a meaningful stopping criterion. 60 FPS is below the display's own capability and would leave headroom unused.

### Implementation
Documented in the EV Charging VR Research Audit, Objective 1 and the Professor Presentation Summary. No code change.

### Status
Accepted

### Impact
Objective 1

### Remarks
Still needs the Windows-workstation measurement (see D004) to confirm what's actually achieved.

---

## D002

### Date
2026-10-02

### Decision
Lower `Shadows::textureScalar` (1.0 → 0.5) and raise `Shadows::disable` (0 → 1, Partial) in `settings/game-settings-default.cs`.

### Context / Problem
Looking for config-level FPS quick wins that don't require engine source access.

### Evidence
`settings/game-settings-default.cs:30-31` — these are live, user-facing graphics preferences (cross-checked against `settings/defaults.json`'s `GraphicShadowsQuality`/`GraphicDisableShadows` keys, which register the same settings for the Options UI).

### Reason
Shadow rendering is a well-known VR fill-rate cost; a config-level change is cheap, reversible, and testable without touching engine code.

### Alternatives Considered
`Shadows::disable = 2` (All) for maximum FPS gain.

### Why Alternatives Were Not Chosen
Full shadow removal changes scene lighting more than a partial step, and this is a human-subjects VR study — fidelity loss needs to be checked against participant experience before going further, not assumed acceptable.

### Implementation
Edited `BeamNG.tech.v0.38.3.0/settings/game-settings-default.cs`.

### Status
Implemented (edit applied); Verified: not yet (no FPS measurement — see D004)

### Impact
Objective 1

### Remarks
Caveat: if the Windows machine already has a saved preferences file outside this install folder, it will override these defaults at runtime until reset via the in-game Options menu.

---

## D003

### Date
2026-10-02

### Decision
Use `Reflect::refractTexScale` (1.0 → 0.5) as the reflection-cost quick win, not `Reflect::frameLimitMS`.

### Context / Problem
The original roadmap proposed "cap `Reflect::frameLimitMS`" as a quick win alongside the shadow changes.

### Evidence
`settings/game-settings-default.cs:23`'s own comment: "A time of 0ms only update 1 reflector per frame" — meaning `frameLimitMS = 0` (its default) is already the cheapest setting, not an uncapped one.

### Reason
Treating an already-optimal setting as a lever to pull would have been a no-op change presented as an optimization. `refractTexScale` (line 22) is the real adjustable reflection-resolution knob.

### Alternatives Considered
Keep the original plan (lower `frameLimitMS` further — not meaningfully possible below 0).

### Why Alternatives Were Not Chosen
Not a real lever; the earlier claim ("uncapped") was a misread of the comment, caught and corrected here rather than left in the audit.

### Implementation
Edited `BeamNG.tech.v0.38.3.0/settings/game-settings-default.cs`. Corrected the earlier incorrect claim in the EV Charging VR Research Audit's Objective 1 bottleneck table.

### Status
Implemented (edit applied); the original `frameLimitMS` claim: Reverted

### Impact
Objective 1

### Remarks
Self-correction — logged so the earlier (wrong) version of this claim doesn't get cited from an older copy of the audit.

---

## D004

### Date
2026-10-02

### Decision
FPS before/after measurement cannot be performed from this (Claude) session; it must be run by the user on the Windows workstation.

### Context / Problem
After D002/D003's config edits, the user asked to measure the FPS difference.

### Evidence
This session runs on macOS. `BeamNG.tech.exe` (`Bin64/`) is a Windows PE binary requiring a Windows GPU driver stack to execute.

### Reason
Physical/environment constraint, not a scoping choice.

### Alternatives Considered
Attempting to run under an emulation/compatibility layer (e.g. Wine/CrossOver) in this session.

### Why Alternatives Were Not Chosen
Even if it launched, emulated GPU performance would not reflect real Windows/native-GPU numbers, making any measurement misleading for an FPS optimization claim.

### Implementation
None (no code change). Added an explicit before/after measurement protocol (FPS overlay, fixed route, same build, VR headset on both runs) to the Research Audit, Objective 1, for the user to execute.

### Status
Accepted (standing constraint)

### Impact
Objective 1

### Remarks
Blocks closing out Objective 1's quick-win claims until the user runs the protocol and reports numbers back.

---

## D005

### Date
2026-10-02

### Decision
Scope FPS optimization work to the Lua gameplay layer, the Python backend, and TorqueScript graphics config — not the BeamNG.tech engine/physics/renderer source, which is unavailable.

### Context / Problem
The original task brief asked for exact engine-level file/line locations for rendering and physics bottlenecks.

### Evidence
`BeamNG.tech.v0.38.3.0/Bin64/` contains compiled `.exe`/`.dll` files (the engine binary, Vulkan layers, Ultralight). `gameengine.zip` contains only assets (cubemaps, datablocks, materials) — no C++ source.

### Reason
Can't profile or hand-fix what isn't readable; claiming otherwise would be fabricating line numbers.

### Alternatives Considered
Infer likely engine-level bottlenecks from BeamNG's publicly known architecture (soft-body physics, VR compositor) and present them as findings.

### Why Alternatives Were Not Chosen
Would violate the project's explicit "do not hallucinate line numbers / mark UNVERIFIED" rule. Those are flagged in the audit as plausible but UNVERIFIED instead.

### Implementation
Documented in the Research Audit, Objective 1.

### Status
Verified

### Impact
Objective 1

### Remarks
—

---

## D006

### Date
2026-10-02

### Decision
Flag the in-game AI assistant's actual architecture (screenshot + RAG deepfake-detection chatbot) as a different system from the gaze/EEG-driven risk-warning pipeline described in the mid-sem report and speaking script, rather than silently treating them as the same thing.

### Context / Problem
Objective 2 ("AI pipeline + warnings") needed its current implementation status checked against the report's description.

### Evidence
Code read: `ai_assistant.py`, `screenshot_analyzers.py`, `rag.py`, `aoi_mapper.py` (present but unused), `receive_ui.py`'s `_analyze_station_layout_async`/`assistant_chat` handling; `images/real/` vs `images/deepfake/` folders.

### Reason
These are genuinely different systems (different inputs, different outputs, different research questions); merging them in documentation would misrepresent what's built.

### Alternatives Considered
Assume the screenshot assistant is an early version of the described warning pipeline and describe it as such.

### Why Alternatives Were Not Chosen
Not supported by the code — no gaze or EEG features feed into `ai_assistant.py`'s decision logic.

### Implementation
Documented in the Research Audit, Objective 2 and Objective status table.

### Status
Under Investigation (needs a decision with the mentor on which one "AI warning" refers to going forward)

### Impact
Objective 2

### Remarks
—

---

## D007

### Date
2026-10-02 (earlier in this session, before the MUSE data upload)

### Decision
EEG is absent from the existing `raw_data/` dataset (0 of 140 sessions).

### Context / Problem
Checking whether the mid-sem report's Table 6 (video/gaze/EEG/event-logs available for 120+ participants) matches what's on disk.

### Evidence
No file matching `*muse*` or `*eeg*` found anywhere under `backend/raw_data/` at the time of that check.

### Reason
—

### Alternatives Considered
—

### Why Alternatives Were Not Chosen
—

### Implementation
Documented in the Research Audit, Objective 2.

### Status
**Reverted** — superseded by D008. This entry is kept, not deleted, because it was an accurate statement about `raw_data/` specifically at the time it was made; EEG files were later found in a separate location (`backend/Muse/`), not in `raw_data/`.

### Impact
Objective 2, Objective status table

### Remarks
Lesson: "not in the folder I checked" and "doesn't exist" are different claims — this entry should have been scoped more narrowly the first time.

---

## D008

### Date
2026-10-02

### Decision
Update the EEG status from "absent" to: raw EEG packet files exist for 76 of 140 participants (54%), in a decodable but currently undecoded format, with partial and only spot-checked (2 of 76) verification of correspondence to the matching BeamNG session.

### Context / Problem
User added a `backend/Muse/` folder with 13 zip archives and asked for a full, evidence-based audit — explicitly not to assume usability from file presence alone, and not to infer session linkage from filenames alone.

### Evidence
- Full `unzip -l` listings of all 13 archives in `backend/Muse/`.
- Content inspection of `021_muse.txt` (format: `timestamp \t characteristic-UUID \t hex-payload`, one BLE notification per line, single constant UUID throughout).
- `musebandtests/collect_data.py`'s `on_data_notify()` produces an identical line format via the `OpenMuse` + `bleak` libraries.
- `musebandtests/recordings/.../session_info.json` + `eeg_decoded.csv`: proves the format is decodable, gives channel names (TP9, AF7, AF8, TP10, +AUX) and lets sample rate be computed directly (15,422 samples / 60.13s ≈ 256.5 Hz).
- Cross-reference of `021_muse.txt`'s timestamp range (2026-04-23T10:42:39–10:44:41 UTC = 16:12:39–16:14:41 IST) against `raw_data/session_20260423_160401_021`'s own interaction log (starts ≥16:06:57 IST) — the EEG window falls inside the session's window, confirmed independently via two different clocks, not inferred from filenames.
- Same check for participant 041 (3-part EEG file, including a 1.4s failed connection and a ~3-minute mid-session gap) against `raw_data/session_20260622_155420_041` — also falls within the session window.
- Participant-ID coverage gaps found by listing: 001–007 missing, 048–052 missing, nothing found above 088.

### Reason
Task explicitly required evidence-based verification, not inference from file existence or naming.

### Alternatives Considered
(a) Trust the filename-participant-ID convention alone and declare EEG "available" for 76 participants. (b) Declare EEG unusable and ignore the new upload entirely.

### Why Alternatives Were Not Chosen
(a) would overclaim — 2 of 76 is not a full verification, and the data is still undecoded and unscreened for quality. (b) would discard real, substantial new evidence (a working decoder, a computed sample rate, genuine timestamp overlap) that materially changes the project's options.

### Implementation
New "MUSE EEG data audit" section added to the Research Audit (inserted before Objective 3). Objective 2 status, the Professor Presentation Summary, and the architecture diagram's EEG node label were all updated to match.

### Status
Under Investigation (format and 2 participants' linkage verified; decoding, full-sample linkage, and signal quality remain undone)

### Impact
Objective 2, Objective 3, Dataset description, AI/DL pipeline, Experimental plan

### Remarks
Next step to move this from "Under Investigation" toward "Verified": run the decode on all 76 files, extend the timestamp cross-check beyond the 2 spot-checked participants, and compute an actual signal-quality metric (contact fit / dropout rate) per participant.

---

## D009

### Date
2026-10-02

### Decision
Recommend adapting `musebandtests/collect_data.py`'s `OpenMuse`/`bleak`-based approach for any future `receive_ui.py` EEG integration, instead of wiring in `muse.py` as originally planned.

### Context / Problem
A prior task asked to "wire `muse.py` into `receive_ui.py` with session-ID logging." Auditing the new MUSE data showed the actual 76-participant dataset was not produced by `muse.py`.

### Evidence
`muse.py` uses `pylsl` (Lab Streaming Layer) and writes a different file schema (stream name/type, LSL timestamps, JSON sample values) than what's in `backend/Muse/`. The real `_muse.txt` files match `collect_data.py`'s raw-BLE-packet format exactly (tab-separated timestamp/UUID/hex, written by `on_data_notify()`), and that same repo already has a working decode path (`OpenMuse.decode.parse_message`, demonstrated in `process_and_playback.py` and its own test recordings).

### Reason
Wiring `muse.py` in as planned would create a second, incompatible EEG format going forward, abandoning a decode pipeline that's already proven to work on the existing 76-participant data.

### Alternatives Considered
(a) Wire `muse.py`/LSL anyway for future data collection, accepting a format split between old and new data. (b) Adapt the `collect_data.py`/`OpenMuse` approach, with session-ID-tagged output, into `receive_ui.py`.

### Why Alternatives Were Not Chosen
(a) would mean every future analysis has to handle two incompatible EEG formats and would strand the already-proven decoder.

### Implementation
No code changed yet — this is a recommendation documented in the Research Audit's Objective 3 and this decision entry. Actual integration work is future work (see D012).

### Status
Proposed

### Impact
Objective 2, Objective 3

### Remarks
Should be confirmed with the mentor/team before implementation, same as D006.

---

## D010

### Date
2026-10-02

### Decision
The first ML pipeline pass uses behaviour + gaze only (all 140 sessions), not behaviour + gaze + EEG, despite EEG files now existing for 76/140 participants.

### Context / Problem
With D008's finding, it's tempting to immediately scope the first model as "multimodal."

### Evidence
EEG is raw/undecoded, has no computed quality metric yet, and even the best case (76/140 = 54%) is well short of full coverage — before any participants are dropped for connection dropouts (observed directly in participant 041's 3-part file) or poor signal.

### Reason
Building the first pipeline iteration on an unverified-quality modality would (a) risk the whole first analysis on data that might not pass QC, and (b) needlessly shrink the usable n from 140 to ≤76 before any result exists.

### Alternatives Considered
Start multimodal (gaze+behaviour+EEG) immediately since files exist for the majority-sized subset.

### Why Alternatives Were Not Chosen
Violates the project's "do not overclaim" rule — treating file-presence as data-readiness. Also contradicts the existing literature review's own caution about fusion not reliably beating single-modality gaze.

### Implementation
Documented in the Research Audit's AI pipeline (Objective 2) and Experimental Plan sections.

### Status
Accepted

### Impact
AI pipeline, Experimental design

### Remarks
Revisit once the D008 decode-and-QC pass is complete and an actual usable-n-with-EEG number exists.

---

## D011

### Date
2026-10-02

### Decision
Model architecture progression stays: baseline ML (logistic regression / random forest / XGBoost) → MLP → LSTM/GRU (temporal) → multimodal fusion, with a Transformer only if data scale and quality after EEG QC support it. No jump straight to a Transformer at any point.

### Context / Problem
Confirming the modeling plan still holds given the updated (but still unresolved) EEG picture.

### Evidence
n=140 for gaze+behaviour, n≤76 (and likely meaningfully lower after QC) for anything involving EEG; this matches the existing literature review's own explicit warning against deep learning as the primary method at this sample size.

### Reason
Keeps the earliest, cheapest model as the test of "does the signal exist at all" before investing in anything more complex, and keeps every added layer honest against a baseline on held-out participants.

### Alternatives Considered
Start directly with a multimodal Transformer, given the project documents' early ambition toward one.

### Why Alternatives Were Not Chosen
Not justified by dataset size at any stage of this project to date; the existing literature review and this audit both converge on the same caution independently.

### Implementation
Documented in the Research Audit's AI pipeline and Experimental Plan sections.

### Status
Accepted

### Impact
AI pipeline

### Remarks
—

---

## D012

### Date
2026-10-02

### Decision
Before any new data collection round: (1) decode and QC the 76 existing `_muse.txt` files as a backfill task, and (2) if new EEG collection happens, use the `collect_data.py`/`OpenMuse` approach (D009) with session-ID-tagged output synchronized to the same event-marker timeline the gaze/behaviour logs already use.

### Context / Problem
Objective 3 (new data collection) needs a concrete EEG plan now that D008/D009 changed what's known about the existing tooling and data.

### Evidence
See D008 (format/decodability), D009 (tooling mismatch), and the Research Audit's Objective 3 synchronization requirements (event markers already logged: `Started`, `Reached`, `AudioTrigger`, `DrivingPageReached`, `ChargeUpdate`, `OutOfFuel`, `Finished`).

### Reason
Backfilling the 76 existing files is cheap relative to new data collection and could substantially change the usable-n picture before any new sessions are run.

### Alternatives Considered
Skip the backfill and only apply the fixed tooling going forward.

### Why Alternatives Were Not Chosen
Would discard potentially usable data from 76 already-recruited participants for no added cost reason.

### Implementation
Not started. Documented as a roadmap item in the Research Audit's Implementation Roadmap (Medium-term) and Objective 3.

### Status
Proposed

### Impact
Objective 3, Dataset, AI pipeline

### Remarks
—

---

## D013

### Date
2026-10-03

### Decision
Ran `OpenMuse` to decode all 76 participants' raw MUSE packet files, fixing a decoder bug along the way (per-sensor-type isolation instead of `decode_rawdata`'s all-or-nothing call), and extended the session-overlap cross-check from 2 participants (D008) to all 76.

### Context / Problem
D008/D012 identified 76 raw EEG files as existing-but-undecoded, with only 2 participants' session linkage spot-checked. User asked to run the actual decode on all 76.

### Evidence
Script: `/tmp/openmuse_env/decode_all.py` (ephemeral scratch location — not yet moved into the repo, see Remarks). Environment: Homebrew Python 3.12 venv at `/tmp/openmuse_env/venv` (OpenMuse requires Python >=3.12; system Python was 3.9.6). Output: `backend/Muse/decoded/<participant_id>/*_decoded.csv` (EEG, ACCGYRO, OPTICS, BATTERY per participant) + `backend/Muse/decoded/decode_summary.csv` (one row per participant: sample counts, computed sample rate, gap count/duration, per-channel flatline fraction, session-overlap verdict).

Key measured results:
- 76/76 decoded (after the robustness fix; 23/76 failed before it, on malformed OPTICS subpackets — see D014).
- EEG sample rate: 256.0 Hz exactly (median/mode across all 76), computed directly from decoded sample counts and duration, not assumed from spec.
- All four sensor streams present and decodable in all/nearly all participants: EEG 76/76, ACCGYRO 76/76, OPTICS 76/76, BATTERY 75/76 — corrects D008's claim that only EEG was captured (see D014).
- Session-overlap check (independent timestamps, both systems' own clocks): 67/76 confirmed overlap, 6 mismatched (012, 053, 054, 055, 058, 082), 2 incomparable (no readable interactions CSV: 059, 072), 1 with zero decoded EEG samples (013).
- Two participants (072, 084) have a nominal recording duration mostly made up of one single large gap each (072: ~3.2h of a ~3.6h span; 084: ~49min of a ~74min span) — their "duration" numbers overstate actual continuous coverage.
- Flatline fraction (dead/disconnected-channel proxy): median 1.0%, max 16.8% (participant 065) — no channel fully flat, nothing outright disqualifying, but 065/053/037 flagged for closer review.
- Malformed/dropped EEG subpackets: 30 out of ~27 million decoded EEG samples (~0.0001%) — negligible at the packet level.

### Reason
The task explicitly asked to run the decode, not just assess whether it was possible, and to extend verification beyond the 2 spot-checked participants per D008's stated remaining blocker.

### Alternatives Considered
(a) Decode only a sample (e.g. 10 participants) to save time/compute. (b) Accept `decode_rawdata`'s crash on 23/76 participants and report only the 53 that worked out of the box.

### Why Alternatives Were Not Chosen
(a) would leave the project exactly where D008 left it — partial verification — when full verification was feasible in a few minutes of compute. (b) would silently and incorrectly undercount usable participants because of a workaround-able bug, not a real data problem — the 23 "failing" participants' EEG data turned out to be fine once OPTICS was isolated.

### Implementation
`backend/Muse/decoded/` now contains decoded CSVs and `decode_summary.csv` for all 76 participants. The Research Audit's MUSE EEG data audit section was updated with a "Decode results" subsection and the Behaviour+Gaze+EEG verdict table was revised accordingly.

### Status
Implemented; Verified for the numbers above (decode ran successfully, outputs exist and were inspected). **Not yet Verified**: no quality/gap/flatline threshold has been chosen or applied, so there is still no single "usable n" for EEG-inclusive modeling — that remains Under Investigation.

### Impact
Objective 2, Dataset, AI pipeline, Experimental plan

### Remarks
Script and pinned dependencies moved into the repo at `backend/Muse/decode_all.py` + `backend/Muse/requirements.txt` (Python >=3.12 required). The venv itself is still only local to this machine (`/tmp/openmuse_env/venv`) — recreate with `python3.12 -m venv venv && pip install -r backend/Muse/requirements.txt` on any machine that needs to re-run this.

---

## D014

### Date
2026-10-03

### Decision
Correct D008's claim that only the EEG BLE characteristic was captured in the production `_muse.txt` files; all four sensor types (EEG, ACCGYRO, OPTICS, BATTERY) are actually present, multiplexed inside that single characteristic's packets.

### Context / Problem
D008 concluded, from seeing only one constant characteristic UUID across a sampled file, that motion/optics streams were not subscribed to during real sessions.

### Evidence
Decoding participant 021's file with `OpenMuse.decode.decode_rawdata` returned non-empty EEG, ACCGYRO, OPTICS, and BATTERY DataFrames from the same raw file that showed only one UUID — the sensor-type distinction is carried in a subpacket tag byte inside the packet payload, not the outer BLE characteristic UUID, which D008's check did not account for.

### Reason
Caught by actually running the decoder rather than continuing to infer capture scope from the raw UUID field alone.

### Alternatives Considered
Leave D008's claim as-is since it was based on a real observation (one UUID).

### Why Alternatives Were Not Chosen
The observation was real but the conclusion drawn from it was wrong — exactly the kind of error this log exists to catch and correct rather than carry forward silently.

### Implementation
Research Audit's "Decode results" subsection now states all four streams are present. D008 is not deleted — this entry supersedes only that one specific claim.

### Status
Verified

### Impact
Objective 2, Dataset description

### Remarks
Motion (ACCGYRO) and PPG/fNIRS (OPTICS) data being available, not just EEG, is itself worth flagging to the mentor — the literature review's EEG-caution framing didn't anticipate having usable accelerometer data for motion-artifact correction, which is a real, useful capability this unlocks.

---

## D015

### Date
2026-10-03

### Decision
Retract the earlier claim that BeamNG.tech exposes an FPS overlay via `gfxFrameOverlay`.

### Context / Problem
A prior Objective 1 pass (before D001-D005) stated a console command/flag named `gfxFrameOverlay` existed for FPS measurement, used in the Research Audit's profiling-methodology text.

### Evidence
`grep -rli "gfxFrameOverlay"` across the entire BeamNG.tech install returns zero matches. The string does not exist anywhere in this codebase.

### Reason
A new, stricter audit pass (explicit rule: never cite a tool/command without a code-read citation) caught this as unverified when re-checked.

### Alternatives Considered
Leave it uncorrected since it was only a methodology suggestion, not a code change.

### Why Alternatives Were Not Chosen
It's exactly the kind of fabrication this project's "do not overclaim" rule exists to catch, and it was stated as fact in a document someone could act on (e.g. search the console for a command that isn't there).

### Implementation
No code affected. Corrected in this turn's chat response; the Research Audit's Objective 1 profiling-methodology text should be updated to remove this reference next time that section is touched.

### Status
Reverted

### Impact
Objective 1

### Remarks
Replaced with verified alternatives found this same pass: `lua/ge/extensions/editor/perfProfiler.lua` (native `.perfRecording.json` profiler/visualizer, confirmed real) and `lua/ge/extensions/render/openxr.lua`'s live debug window (confirmed real, reports rendered vs. recommended resolution and current vs. target refresh rate).

---

## D016

### Date
2026-10-03

### Decision
Add two new, evidence-backed Objective 1 findings: BeamNG's OpenXR debug window as a real measurement source, and the 2D mirror "screen view" mode as a verified (not guessed) quick-win candidate.

### Context / Problem
Re-auditing Phase 1 under a stricter "every claim needs a code citation" framework surfaced `lua/ge/extensions/render/openxr.lua`, which hadn't been read in the earlier Objective 1 pass.

### Evidence
`openxr.lua:164` — the 2D mirror view dropdown's own option labels, written by BeamNG's developers: `"Empty (fastest)"`, `"Between eyes (slowest)"`, `"Reuse left eye"`, `"Reuse right eye"`. `openxr.lua:67-68, 179-184` — the debug window live-reports `renderedWidth/Height` vs `recommendedWidth/Height` and `currentRefreshRate` vs `targetRefreshRate` (the latter pair being how OpenXR reprojection/half-rate fallback would show up).

### Reason
Genuine, low-risk, independently-justified finding worth acting on once measured, and a materially better Phase 2 methodology than anything available before this pass.

### Alternatives Considered
Treat this as equivalent in confidence to the shadow/reflection config changes (D002/D003).

### Why Alternatives Were Not Chosen
It's a different kind of evidence — a developer's own code comment about relative cost, not a measured number — so it's logged as a recommendation to test, not as an applied change (no file was edited for this one; it's a runtime UI setting, not a `.cs` default).

### Implementation
Not applied (it's a runtime setting the user needs to check/change in-headset or via `settings.setValue`, not a file this session can edit). Documented in this turn's Phase 1/3/5 output; should be folded into the Research Audit's Objective 1 section next time it's updated.

### Status
Proposed (for the mirror-view change) / Accepted (as a measurement methodology addition)

### Impact
Objective 1

### Remarks
—

---

## D017

### Date
2026-10-03

### Decision
Correct D006: the in-game AI assistant is **not** an unrelated system from the kiosk-trust/cyberattack-recommendation design described in the mid-sem report. It already is a kiosk-cyberattack-detection-and-recommendation pipeline — just image-based (VLM screenshot analysis of coupon graphics), not gaze/EEG-based.

### Context / Problem
D006 stated the screenshot+RAG assistant and the report's described gaze/EEG-driven warning system "are genuinely different systems" doing unrelated things, raising doubt about whether Objective 5 (automation bias, "malicious AI recommendation" scenario) had anything to build on.

### Evidence
- `screenshot_analyzers.py:11-36` (`ANALYSIS_PROMPT`, read in full): "You are an expert in analyzing EV charging network user interfaces for signs of potential cyberattacks... Identify any anomalies or signs of cyberattack, such as deepfake or AI-generated images, unrealistic discounts, phishing prompts, or suspicious branding." This is the literal VLM instruction — not a generic or unrelated task.
- `ui_renderer.py:28,58-65`: the "deepfake" vs "real" image folders are coupon/discount-banner graphics rendered into the kiosk UI mock (`"Special 10% Discount Available!"` banner + `<img class='coupon'>`) — i.e. "deepfake" = a fake/AI-generated-looking coupon image, directly matching the project's own "fake discount coupon" attack scenario, not an unrelated identity-deepfake task.
- `ai_assistant.py:230-238` (`help_agent_prompt`): "You are a Help Agent for EV charging kiosks... recommend the safest available kiosk... Never recommend a kiosk that is occupied or unavailable. If all kiosks are risky, suggest the least risky available one..." — this is literally the kiosk-safety recommendation the report describes, built directly on the VLM's per-kiosk anomaly analysis.

### Reason
D006 was based on reading `receive_ui.py`'s dispatch logic and the images/real vs images/deepfake folder names without reading the actual prompts (`ANALYSIS_PROMPT`, `help_agent_prompt`) or the HTML-rendering code that explains what those images represent in-scene. Reading those closed the gap.

### Alternatives Considered
Leave D006 standing since the underlying code-location citations in it were accurate.

### Why Alternatives Were Not Chosen
The citations were accurate but the conclusion drawn from them ("different systems," "unrelated question") was wrong and had already propagated into the user's own planning — the automation-bias objective and the "malicious AI recommendation" scenario were described as built on the premise these systems were connected, and D006 would have told them to redesign something that already exists.

### Implementation
No code changed. This corrects the interpretation only; the Research Audit's Objective 2 text (which echoed D006's framing) needs updating next time that section is touched.

### Status
Verified (what's correct is now based on reading the actual prompts and rendering code, not inference from folder/file names)

### Impact
Objective 2, Objective 5 (automation bias), the "malicious AI recommendation" scenario design

### Remarks
What D006 got right and still stands: gaze and EEG genuinely do not feed into this recommendation path — `ai_assistant.py` has no reference to either. What's still missing for Objective 5, now scoped precisely rather than "redesign from scratch": `_build_full_prompt` always instructs the LLM to recommend the *safest* kiosk — there is no condition variable for a deliberately malicious/wrong recommendation. Adding one is a scoped, bounded change (a condition flag plus either suppressing the real anomaly signal or overriding the final recommendation in that condition), not new infrastructure.

---

## D018

### Date
2026-10-03

### Decision
Flag a newly discovered, previously undocumented risk: the AI assistant's RAG index (`backend/rag_index/`) is a single shared store that persists across all sessions, not reset per participant, and currently holds 904 accumulated documents spanning at least 45+ sessions' worth of charging events.

### Context / Problem
While settling the deepfake-chatbot question (item 3), traced how `ai_assistant.py`'s RAG retrieval is populated and persisted.

### Evidence
`rag.py:76-85` (`RAGStore.save()`) writes to a fixed path (`backend/rag_index/meta.json`, `index.faiss`) rather than a per-session path. `receive_ui.py:808` calls `self.ai.reset_session()` on every new "Flowgraph Started" event, but `AIAssistant.reset_session()` (`ai_assistant.py:65-69`) only clears in-memory state (`charging_context`, `screenshot_history`) — it never calls `self.rag_store.clear()`. Inspecting the actual files on disk: `rag_index/meta.json` contains 904 documents spanning trial numbers 1 through at least 20, with a last-modified date (Aug 3) matching the tail end of the recorded session range, confirming real cross-session accumulation, not just a theoretical risk. A standalone script, `clear_rag_context.py`, exists and calls `RAGStore.clear()`, but nothing in the automatic session-start path calls it.

### Reason
This is a genuine methodological confound for any research question about AI-recommendation quality or consistency across participants: a participant's recommendation for a given kiosk image can be informed by what happened when *other* participants, on *other* days, encountered the same (small, reused) set of coupon images — unless `clear_rag_context.py` was manually run between every session, which nothing in the code enforces.

### Alternatives Considered
Treat this as out of scope since it wasn't what was asked (the question was whether the chatbot is salvageable, not an audit of its internals).

### Why Alternatives Were Not Chosen
It directly affects whether "AI assistant helpfulness" or "automation bias" results can be treated as independent across participants, which is squarely inside Objective 2/5's experimental validity — surfacing it now is cheaper than someone discovering it after running statistics that assumed independence.

### Implementation
No code changed. Not fixed unilaterally — this affects already-collected experimental data and is a call for the research team, not a unilateral cleanup.

### Status
Under Investigation (confirmed to exist and to have accumulated real cross-session data; not yet confirmed whether `clear_rag_context.py` was in fact run between some/all/none of the 140 sessions — that would need the team's own operational memory or log timestamps on `rag_index/meta.json`'s modification history, which this audit doesn't have beyond the single last-modified date observed)

### Impact
Objective 2, Objective 5, Experimental design, Dataset description

### Remarks
Worth raising to the mentor alongside D006/D009's `muse.py` reconciliation — both are "someone above you should know this" items, not something to silently patch.

---

## D019

### Date
2026-10-03

### Decision
Compute the actual EEG usable-n against an explicit inclusion rule, and fix a real bug in D013's own cross-check script along the way (picking the wrong session folder when a participant has more than one).

### Context / Problem
D013 left "no single usable n" as open; the user proposed a concrete inclusion rule (session-overlap confirmed, excluding the two dropout-heavy files and the zero-sample file, flatline fraction under ~10-15%) and asked for the exact number plus a look at the 6 session-mismatched participants (012, 053, 054, 055, 058, 082).

### Evidence
Applying the proposed rule to D013's original `decode_summary.csv` gave 65/76. Investigating the 6 mismatches found: **012, 053, 054** show a short EEG recording ending just minutes *before* the matching session's logged start — consistent with a pre-session headset check that was never followed by in-session recording (genuinely no usable EEG for the real session, correctly excluded). **058** has only one session folder on disk, and it's a 2-line, effectively empty interactions log (single "driving" event) — the real played session for this participant doesn't appear to exist under this ID in `raw_data/`; this is a logging gap, not necessarily bad EEG, but unverifiable either way. **055 and 082 were a bug in D013's own script**: both participants have more than one `session_*_<id>` folder on disk (055 has 3, 082 has 2 — confirmed by scanning all 140 session folders for duplicate participant-ID suffixes, which also turned up unrelated duplicates for 001, 022, 034, 064), and the script only checked the first alphabetically-sorted folder. Checking every candidate folder found a genuine overlap for both (082's second folder, `session_20260707_153948_082`, runs 15:42-16:12 IST against an EEG window of 15:38-15:57 — a clean match).

### Reason
The task asked for the real number, not an estimate, and the user explicitly asked to check whether the mismatches were a logging bug or bad EEG — both turned out to be true, for different subsets of the 6.

### Alternatives Considered
Report the uncorrected 65/76 and note the duplicate-folder issue as a caveat rather than fixing the cross-check.

### Why Alternatives Were Not Chosen
The fix was cheap (re-glob all candidate folders instead of the first) and directly changes the answer to the question asked.

### Implementation
`backend/Muse/decoded/decode_summary_resynced.csv` added alongside the original `decode_summary.csv` (kept, not overwritten, so the original run's output stays reproducible from its own log). Final corrected numbers: **69/76 EEG files show confirmed session overlap** (up from 67 in D013); **67/76 are usable under the proposed inclusion rule** (up from 65) — **67 of 140 participants (47.9%)** have decoded, session-linked, quality-screened EEG.

### Status
Verified (inclusion rule applied and computed exactly; the rule's own thresholds — "flatline under 15%," the specific dropout-duration cutoff for 072/084 — remain a judgment call, not independently validated against ground truth)

### Impact
Objective 2, Dataset description, AI pipeline, Experimental plan

### Remarks
058 is worth a direct question to whoever ran that session: is there a session folder for participant 058 somewhere that didn't get the standard `session_<timestamp>_058` naming (e.g. a typo'd participant ID, or a folder never copied into `raw_data/`)? If found, it would likely resolve the same way 082 did. 059 and 072 remain excluded on separate, firmer grounds (no readable interactions CSV at all for 059; a single dominant multi-hour gap for 072) and were not helped by the duplicate-folder fix.

---

## D020

### Date
2026-10-03

### Decision
Validate fixation/saccade detection on 3 participants (021, 041, 100) before running it across the full 140-session gaze dataset. Results look physiologically plausible; proceeding to a wider batch is reasonable, but true AOI (coupon/price/kiosk-screen) mapping is still structurally blocked, not just unimplemented.

### Context / Problem
Gaze is confirmed present and complete for all 140 sessions and isn't blocked by the FPS, EEG-threshold, or AI-assistant questions. Asked to pilot fixation/saccade detection + AOI mapping on a handful of participants first.

### Evidence
Script: `/tmp/openmuse_env/gaze_pilot.py`. Method: I-VT (velocity-threshold) classification on the Varjo `gaze_forward` unit vector at its native ~199-200 Hz (empirically confirmed from timestamps, matching the eye tracker's documented spec), after filtering to Varjo's own `status==2` and `stability>0` fields (inspected directly, not assumed) — not a filter invented for this pilot. Results:

| Participant | Valid sample fraction | Fixations | Median fixation duration | Mean saccade amplitude |
| --- | --- | --- | --- | --- |
| 021 | 63.1% | 172 (103/min) | 158 ms | 2.14° |
| 041 | 64.9% | 2243 (82/min) | 195 ms | 4.17° |
| 100 | 61.7% | 1122 (79/min) | 170 ms | 1.99° |

Fixation durations (150-250ms median/mean) and the right-skewed saccade-amplitude distribution (most saccades small, a few large) both land inside normal physiological ranges reported in the eye-tracking literature — a basic sanity check this pilot was designed to make, and it passes. The ~35-39% invalid-sample rate (excluded by Varjo's own stability/status fields, mostly `stability==0.0`) is a real, quantified data-quality fact, not a bug in the detection code — consistent with known VR eye-tracking challenges (blinks, brief tracking loss during head movement).

### Reason
Matches the same validate-before-scaling practice used for the EEG decode (D008 → D013): check a handful of cases are sane before committing compute and interpretation to all 140.

### Alternatives Considered
Attempt AOI mapping now using an assumed or guessed screen-space layout for the coupon/price/kiosk-screen regions.

### Why Alternatives Were Not Chosen
No scene-object geometry or synchronized video exists in this dataset to ground a screen-space or 3D AOI assignment — fabricating one would produce AOI labels with no way to verify they're correct. This is the literature review's own flagged top technical risk ("dynamic AOI mapping in VR"), now confirmed as a real, structural blocker from this dataset specifically, not a generic caveat.

### Implementation
`/Users/naman/Documents/MTP/gaze_pilot_out/` now holds per-participant fixation/saccade event CSVs and `gaze_pilot_summary.csv` for the 3 piloted participants. Not yet run on the remaining 137.

### Status
Implemented (pilot); Verified (results are physiologically plausible); the wider 140-session run is Proposed, not yet done

### Impact
Objective 2, AI pipeline, Experimental plan

### Remarks
Before scaling to all 140: decide what to do about the ~35-39% invalid-sample rate (exclude those windows from feature extraction, or treat a too-high invalid fraction as a session-level exclusion criterion, mirroring the EEG inclusion rule in D019). AOI mapping needs either (a) BeamNGpy/flowgraph-logged kiosk screen-space or world-space coordinates per frame, captured going forward, or (b) manual region calibration against representative screenshots for the existing 140 - worth deciding which before any further gaze work, since it blocks the "dwell time on coupon vs price" features the pipeline design calls for. **Superseded in part by D021**, which answers this definitively rather than leaving it as an open decision.

---

## D021

### Date
2026-10-03

### Decision
**AOI mapping is NOT RECOVERABLE for the existing 140 sessions. It is RECOVERABLE GOING FORWARD**, with a specific, concrete fix identified (not a vague "needs more data").

### Context / Problem
D020 left AOI mapping as "structurally blocked, needs a team decision." Asked to check, specifically, whether it's truly unrecoverable rather than assuming so: (1) is gaze logged in world space or head/view space, (2) is head pose logged at matching timestamps, (3) are kiosk/UI element positions deterministic and recoverable independent of video.

### Evidence
**(1) Gaze is head/view-local, not world space - confirmed empirically, not inferred.** `gaze_origin_x/y/z` is exactly `(0.0, 0.0, 0.0)` for every single sample, in all 3 pilot participants' full gaze files (not a rounding artifact - checked `.abs().max()` across each file, all zero). This is the standard convention for an eye tracker reporting gaze relative to the HMD's own reference frame, not the scene.

**(2) No head pose is logged anywhere, for any participant.** The gaze CSV's full 46-column header has no position/orientation/quaternion field. Checked `system_config.json` and the interaction logs for the same session - nothing there either. Without the HMD's own world-space position and orientation at matching timestamps, a head-local gaze direction cannot be converted to a world-space ray, regardless of what else is known.

**(3) Kiosk world positions are architecturally real but not present in this install.** `lerpCamToKiosk.lua`/`lerpCamFromKiosk.lua` (BeamNG flowgraph camera nodes) take `targetPos` (vec3) and `targetRot` (quat) as *input pins*, not hardcoded constants - meaning the specific per-kiosk world coordinates are supplied by the project's own flowgraph scenario graph file, which was not found anywhere in this installation (no `.flow.json` or prefab referencing "kiosk" exists in this codebase copy). The mechanism for fixed kiosk positions almost certainly exists in the real project files; this audit doesn't have access to them.

Given (1) and (2) fail decisively on their own, (3) doesn't matter for the existing data - even perfect kiosk coordinates can't be combined with a gaze direction whose own world-space anchor (the head) is unknown.

### Reason
The task's own explicit rule: if 1-3 don't hold, say so and stop rather than forcing a workaround. (1) and (2) are hard "no"s, independently verified across all 3 pilot participants, not a single-case anomaly.

### Alternatives Considered
Prototype raycasting gaze against assumed/estimated kiosk positions anyway, accepting the head-pose gap as noise.

### Why Alternatives Were Not Chosen
Would produce AOI labels that look like real findings but aren't grounded in anything verifiable - exactly what the task said not to do. A fixation "on the coupon" claim built on an unknown head orientation is not a finding, it's a guess wearing a finding's clothes.

### Implementation
No AOI-mapping code written for the existing 140. Documented as a hard blocker in the Research Audit (to be updated).

**Fix going forward, concretely scoped:** BeamNG's Lua layer already has live access to camera/head pose - `core_camera.getPosition()` and `core_camera.getQuat()` are used directly inside the existing camera-lerp nodes. Logging these (or the actual HMD pose, if distinct from the scripted camera) per gaze sample, timestamp-synced, is a code change to the data-capture path, not a new engine capability. Combined with exporting the kiosk world positions already implicit in the flowgraph graph (as a one-time static table, if fixed per station, or logged per-session if randomized), this becomes straightforward raycasting.

**Next-best substitute for the existing 140** (per the task's fallback instruction): head-relative gaze-direction clustering - report the number of distinct fixation clusters and switching behavior between them during the decision window as an unlabeled behavioral signal (attention-switching rate, dwell concentration), explicitly NOT presented as "looked at the coupon" or "looked at the price," since that would overclaim.

### Status
Verified

### Impact
Objective 2, Dataset description, AI pipeline, Experimental plan, Objective 3 (new data collection requirements)

### Remarks
This is the single most important correction this pass makes to the project's stated plan: every document so far (mid-sem report, literature review, prior passes of this audit) treats "AOI mapping in VR" as a hard-but-solvable engineering problem. For the *existing* 140 sessions specifically, it is not solvable at all without re-collecting data - the missing piece is head pose, not video. New data collection should treat logging head pose alongside gaze as a non-negotiable requirement, not a nice-to-have.

---

## D022

### Date
2026-10-03

### Decision
Quantify the gaze invalid-sample rate by Varjo's own status/stability fields (not left as a vague "mostly fine") and propose - but do not yet apply at scale - a concrete inclusion rule, pilot-stage only (021, 041, 100).

### Context / Problem
D020's pilot found a 35-39% invalid-sample rate without breaking down why, or proposing a threshold with the same rigor as the EEG rule in D019.

### Evidence
Per-participant breakdown (`status`, `stability`, per-eye `left_status`/`right_status`, eye-openness as a blink proxy):

| Participant | status==0 | stability==0 | eye_openness<0.2 (both eyes) | status==0 rows' mean eye_openness |
| --- | --- | --- | --- | --- |
| 021 | 22.0% | 36.9% | ~20% | 0.050 / 0.055 (consistent with blinks/eyes-closed) |
| 041 | 7.8% | 35.1% | ~1% | 0.639 / 0.724 (eyes were OPEN - not blink-related) |
| 100 | 15.4% | 38.3% | ~12% | 0.165 / 0.198 (mixed) |

Two findings worth stating plainly: (a) `status==0` rows always have `stability==0` (100% overlap in all 3 participants) - `stability` is the more sensitive field and does most of the filtering work, since 19-30% of `status==2` ("valid") rows still have `stability==0`. (b) **The cause of invalidity is not consistent across participants** - for 021 it looks blink-dominated (low eye-openness), for 041 it is clearly NOT blink-related (eyes open, still flagged invalid - likely tracking/calibration loss or a headset-fit issue), for 100 it's a mix. Treating all invalid samples as "blinks" would be wrong for at least one of the three pilot participants.

### Reason
Matches the rigor the task asked for and the precedent set by D019 - a stated, inspectable rule, not an assumption.

### Alternatives Considered
Use eye-openness alone as the validity filter (simpler, single field).

### Why Alternatives Were Not Chosen
Participant 041 shows eye-openness is not a reliable invalidity signal on its own - would have let through ~92% of samples that Varjo's own `status`/`stability` fields say are untrustworthy.

### Implementation
No change to `gaze_pilot.py`'s existing filter (`status==2 AND stability>0`, already in use since D020) - this entry documents and justifies it rather than changing it. Proposed, not yet applied: a session-level exclusion threshold (e.g., exclude a session if valid-sample fraction < 50%) before scaling to all 140 - a judgment call requiring validation across more than 3 participants first.

### Status
Verified (the breakdown); Proposed (the session-level threshold - not validated at scale)

### Impact
AI pipeline, Experimental plan

### Remarks
Not scaled to all 140, per the task's explicit instruction - this stays pilot-stage until Task 1's AOI verdict (D021) and this threshold are both settled.

---

## D023

### Date
2026-10-03

### Decision
Quantify the RAG contamination's actual data impact (not just the mechanism from D018): confirmed, not hypothetical, and far more extensive than D018's framing suggested.

### Context / Problem
D018 established the RAG store is shared and never auto-cleared. Not yet answered: did it actually change what any real participant's AI assistant saw, and how many sessions were affected.

### Evidence
- **38 of 140 sessions (27.1%) used the AI assistant at least once** (found by searching each session's interaction log for `assistant_chat`/`AssistantReply` messages).
- **The earliest document in `rag_index/meta.json` is dated 2026-03-21** (extracted from each document's own embedded creation timestamp, `evt_<trial>_<kiosk>_<epoch-ms>`) - this is almost a full month *before* the earliest `raw_data/` session (2026-04-19). The store was already populated with prior (likely dev/test) content before the first real participant ever played, and shows continuous accumulation (no evidence of a reset) through 2026-08-03, matching the full data-collection span.
- **All 38 of 38 assistant-using sessions (100%) had prior documents already in the store at the moment of their first query**, cross-referencing each session's first-use timestamp against every document's creation timestamp (both are local wall-clock on the same machine, directly comparable without timezone conversion).
- The number of prior documents at query time ranged from **162 (minimum, earliest affected session) to 902 (maximum, latest session)**, median 331. This was not a marginal, edge-case exposure - every assistant interaction in the dataset had a substantial pool of prior context available to be retrieved.

### Reason
"The mechanism exists" and "it demonstrably affected real collected data" are different claims, and the task asked for the second one specifically.

### Alternatives Considered
Stop at D018's mechanism-level finding and treat quantification as unnecessary detail.

### Why Alternatives Were Not Chosen
The real number (100% of assistant-using sessions, with substantial prior-document counts) is far more decisive than "a shared store exists" - it changes this from a theoretical confound to a confirmed property of the entire assistant-interaction dataset, which is the kind of fact a reviewer or the mentor would want stated precisely, not hedged.

### Implementation
No code changed (per the task's explicit instruction not to touch the RAG store in this pass). Analysis is reproducible from `rag_index/meta.json`'s document timestamps cross-referenced against each session's own interaction log.

### Status
Verified

### Impact
Objective 2, Objective 5 (automation bias), Experimental design, Dataset description

### Remarks
Every one of the 38 sessions' AI-assistant interactions should carry a contamination caveat if used in any analysis of recommendation quality or consistency - this is not a "some sessions, maybe" issue, it's "all of them, confirmed." Still a mentor-facing decision per D018/D006's standing rule, not something fixed unilaterally here.

---

## D024

### Date
2026-10-03

### Decision
Implemented the D017 scoped automation-bias condition (correct/absent/malicious) in `ai_assistant.py`. The plumbing works and is tested; the malicious condition's actual effectiveness against the live LLM is inconsistent (~50% compliance in a small test sample) and needs more work before it's usable in a real study.

### Context / Problem
D017 identified that the existing kiosk-recommendation system needs one addition - a condition variable - for the automation-bias objective, not a rebuild.

### Evidence
Added `condition` (`"safe"` default / `"absent"` / `"malicious"`) and `malicious_target_kiosk` parameters to `AIAssistant.ask()` and `_build_full_prompt()` in `backend/ai_assistant.py`. Default path (`condition="safe"`, or no argument at all) is byte-for-byte the same prompt as before this change - verified by reading the diff, not just asserting it. `"absent"` short-circuits before any LLM call and returns a fixed neutral message. `"malicious"` requires an explicit target kiosk (raises `ValueError` otherwise - tested, confirmed it raises rather than silently defaulting) and appends an explicit, clearly-labeled override instruction *after* the real anomaly analysis in the prompt (so the override is additive/instructive, not a cover-up of the underlying analysis), and prints an explicit `AUTOMATION-BIAS CONDITION ACTIVE` log line plus returns `condition`/`malicious_target_kiosk` in the result dict whenever a non-default condition fires.

Tested end-to-end against the live Gemini API (`backend/test_automation_bias_conditions.py`, same synthetic 3-kiosk station state across all conditions) rather than only inspecting the prompt text. Results across 4 total malicious-condition runs (gemini-2.5-flash): **the model complied with the override (recommended the flagged-anomalous Kiosk 2) in 2 of 4 runs, and ignored it in favor of the genuinely safe kiosk in the other 2.** The injected override text was confirmed present and correctly worded in every run's prompt (not a plumbing failure) - the inconsistency is in whether the model follows it.

### Reason
"Does the code path exist" and "does it reliably produce the intended manipulation" are different questions, and only testing against the real model answers the second one - a dry run that only checked the prompt text would have missed this.

### Alternatives Considered
(a) Report the feature as done once the prompt-level override was confirmed present, without running it against the live model. (b) Strengthen the prompt further or switch models until compliance looked reliable, within this same task.

### Why Alternatives Were Not Chosen
(a) would have missed a real, decision-relevant finding - a ~50%-reliable manipulation is not yet a usable experimental condition. (b) is scope creep beyond "minimum change" without the team's input on how much prompt-engineering effort (vs. a different mechanism entirely, e.g. deterministically substituting the final recommendation text rather than hoping the LLM complies) is the right tradeoff here - that's a design decision for the team, not something to iterate on unilaterally.

### Implementation
`backend/ai_assistant.py` (`ask()`, `_build_full_prompt()`). `backend/test_automation_bias_conditions.py` added as a standalone, repeatable test (uses `rag_enabled=False`, does not touch the shared RAG store). `receive_ui.py`'s existing call site (`self.ai.ask(message=..., current_charge=..., points=..., trial=...)`) was **not** modified - it still omits `condition`, so default behaves exactly as before and the malicious path cannot fire during normal gameplay unless someone deliberately wires it in later.

### Status
Implemented; Verified (the plumbing, the default-path no-op guarantee, the fail-safe on a missing target); **Under Investigation** (the override's actual reliability against the live model - 50% in n=4 is not enough to call this ready for a real study)

### Impact
Objective 2, Objective 5 (automation bias), Experimental design

### Remarks
Before this condition is used in real data collection: run a larger sample (dozens of trials, varied kiosk states) to get a real compliance-rate estimate, and if it stays unreliable, consider a deterministic fallback (post-process the LLM's safe recommendation into a forced "Kiosk {target}" substitution for the malicious condition, logged as such) rather than relying on prompt compliance alone. This is a design decision worth raising with the mentor alongside D006/D009/D018, not a code fix to make unilaterally. **Superseded by D028's larger test.**

---

## D025

### Date
2026-10-03

### Decision
Piloted the AOI-free gaze analysis (unlabeled fixation clustering, switching rate, dispersion/entropy) on real decision windows from the 3 pilot participants. **Verdict: this fallback can support RQ2 in a reduced, less interpretable form, but it cannot support RQ1 as currently worded on the existing 140 sessions - RQ1 needs explicit rescoping, not a workaround.**

### Context / Problem
D021 left "unlabeled gaze-cluster/switching-behavior analysis" as a placeholder fallback. Asked to make it a concrete, piloted method and give a direct opinion on whether it's strong enough to carry RQ1 ("which information do users inspect, and in what order") and RQ2 ("do gaze/EEG/behavioural patterns distinguish risky from safe decisions").

### Evidence
Method: decision windows built from the interaction log's own event markers (`Reached` -> first `charging`/`disabled_charging`/`driving`); within each window, I-VT fixation detection (same method as D020) on valid gaze samples, then DBSCAN clustering of each fixation's mean `gaze_forward` direction (eps=0.08, unlabeled - clusters are arbitrary region IDs, not AOI names), transition counts between clusters, and two scalar summaries: dispersion (1 - resultant vector length of duration-weighted mean gaze direction) and Shannon entropy over per-cluster dwell time.

Ran on 9 real decision windows across the 3 participants (021: 1 window [session is short, matches earlier finding]; 041: 5; 100: 3). Results: 4-9 clusters per window, entropy range 0.89-2.11 bits, dispersion 0.009-0.034, transitions-per-fixation 0.187-1.0. Concrete contrast pair: participant 100's station 2 (15.5s, charging decision) shows one dominant cluster holding 22 of 29 fixations with brief excursions (low-switching, settled pattern, ratio 0.286) - a plausible "comparison-light, early-locked-in" signature. Participant 041's station 7 (39.3s, charging decision) shows frequent back-and-forth between 3-4 clusters across 71 fixations (32 transitions, ratio 0.457) - a plausible "active comparison" signature. These are genuinely different, interpretable *shapes* of gaze behavior, without needing to know what was being compared.

**What this cannot support, stated plainly**: no finding from this method may say "looked at the coupon," "spent longer on the price than the banner," or any wording that assigns semantic identity to a cluster - clusters are anonymous regions in head-local direction space. **Existing documentation that currently implies otherwise and will need correcting**: the mid-sem report's Table 7 ("Candidate features per modality") lists "Dwell time on warning or coupon," "fixation count and duration" (implicitly per-AOI), and "time to first fixation (TTFF)" - all of which assume AOI-anchored features and are not deliverable on the existing 140 sessions under this method.

### Reason
A placeholder phrase ("unlabeled cluster analysis") isn't a method until it's been run on real data and judged against the actual research questions it's meant to support.

### Alternatives Considered
Report the method as "sufficient" for both RQs since some signal clearly exists in the numbers (clusters differ, entropy differs).

### Why Alternatives Were Not Chosen
Having *some* signal is not the same as being able to answer RQ1 as worded. RQ1 explicitly asks "which information" - an unlabeled cluster count cannot name what was inspected, no matter how cleanly it separates two example windows.

### Implementation
`backend/gaze/aoi_free_pilot.py` added; output at `/Users/naman/Documents/MTP/gaze_pilot_out/aoi_free_pilot_summary.csv`. Not scaled beyond the 3 pilot participants, per the task's explicit instruction.

### Status
Verified (the pilot results); Accepted (the verdict - RQ1 needs rescoping, RQ2 survives degraded)

### Impact
Objective 2, Experimental Plan (RQ1/RQ2 wording), Dataset description

### Remarks
A direct opinion, as asked for: don't present this as "RQ1, measured differently" - that undersells the change. A defensible rescoped version is something like "RQ1-revised: does gaze-switching/comparison behavior (cluster count, transition rate, entropy) during the decision window differ in order and intensity before risky vs. safe decisions, independent of which specific visual element was being compared?" - which is really a restatement folded into RQ2's territory. Worth being explicit with the supervisor that RQ1 as originally scoped is a new-data-collection deliverable (once D021/D027's logging fix lands), not an existing-data one.

---

## D026

### Date
2026-10-03

### Decision
Found a previously undocumented second AOI-mapping attempt already in the codebase (`aoi_mapper.py`) - it runs, but when checked against ground truth, its output is not spatially trustworthy. This does not overturn D021, but it changes the recommended going-forward fix: the 2D decision-UI panel (where the actual kiosk/charge choice happens) may not need world-space head pose at all, if properly calibrated - a smaller, cheaper problem than D021's full fix, once someone validates the coordinate transform.

### Context / Problem
While investigating Task 1's sub-question 3 (are UI element positions recoverable independent of video), re-examined `aoi_mapper.py` - a file flagged as existing but unused as far back as the first pass of this audit, never previously opened in full.

### Evidence
`aoi_mapper.py` defines 8 hardcoded AOIs (`DEFAULT_AOIS`) as normalized 0-1 screen-space rectangles matching the station-decision screen's own CSS grid layout (kiosk_1/2/3 side by side, plus buttons for charging/skip/AI-assistant/points) - this is the **2D UI overlay** (the AngularJS/CEF "station" screen), a conceptually different "kiosk" than the 3D in-world object the camera-lerp nodes (D021) position during the drive-up cinematic. It maps gaze using `gaze_projected_to_left/right_view_x/y` - a 2D per-eye projected coordinate that, unlike `gaze_forward`/`gaze_origin`, does not obviously require world-space head pose in principle, since a head-locked 2D UI panel could in theory align with a head-relative gaze projection directly.

Ran it for real on participant 021's actual data (`python3 aoi_mapper.py --interaction-file ... --gaze-file ... --pages station`). Then checked the result against ground truth: the interaction log shows this participant actually selected **Kiosk 1** (`"kiosk_used":1`). The tool's own output assigns **zero** gaze samples to `kiosk_1` anywhere in the entire decision window (not overall, not even in the final 20% of samples immediately before the charging click) - instead putting 86% of all gaze on `kiosk_3` (2936/3405 samples), rising to 67% in the closing moments before the click. Several AOIs (kiosk_1, start_charging, battery_status, skip_charging, points) got zero hits across the entire window.

### Reason
A tool that assigns zero gaze to the kiosk the person demonstrably chose, while pinning the large majority of gaze to an unrelated AOI regardless of the real decision, is not producing usable output - this is a clean falsification, not an ambiguous result needing more data to judge.

### Alternatives Considered
(a) Report `aoi_mapper.py` as a working solution since it runs without error and produces output. (b) Attempt to fix its coordinate-system calibration within this task.

### Why Alternatives Were Not Chosen
(a) would be exactly the "fake-looking AOI data" presented as a finding that the project's standing rule prohibits - "it runs" and "it's correct" are different claims, and only the ground-truth check (not just running it) revealed the gap. (b) is a real calibration problem (determining Varjo's actual projection/FOV parameters, or running a deliberate calibration routine) that needs domain knowledge of the Varjo SDK's exact output convention and ideally a session with known gaze-to-screen-position ground truth throughout, not a guess made under this task's time budget.

### Implementation
No code changed. `aoi_mapper.py` itself is unmodified. This finding is documented here and should be folded into the Research Audit's Objective 2/Gaze sections next time they're updated, alongside D021.

### Status
Verified (the miscalibration, via the ground-truth check); the underlying coordinate-system fix itself: Proposed, not attempted

### Impact
Objective 2, Dataset description, Objective 3 (going-forward logging requirements)

### Remarks
Worth investigating as a potentially cheaper alternative to D021/D027's full world-space + head-pose fix, specifically for the 2D decision-UI (arguably the more research-relevant surface anyway, since it's where the actual charge/skip/AI-help choice happens, not the drive-up cinematic). Needs: (a) finding out exactly what `gaze_projected_to_*_view` represents in Varjo's own SDK documentation (tangent-angle on a near plane relative to each eye's own axis, by the look of the value ranges found - not calibrated to this application's render target), and (b) a deliberate calibration recording (participant looks at each UI element in sequence on command) to fit the real transform empirically, rather than assuming a hardcoded rectangle guess. Until then, do not use `aoi_mapper.py`'s output for anything.

---

## D027

### Date
2026-10-03

### Decision
Partially implemented the going-forward fix (head pose + kiosk position logging). Confirmed the camera-pose API is accessible; corrected a wrong premise in the task (there is no existing BeamNG Lua gaze-logging hook to extend); could not complete end-to-end validation because it requires a session recorded with the new logging in place, which doesn't exist and can't be produced from this session.

### Context / Problem
Asked to (1) confirm `core_camera.getPosition()`/`getQuat()` are callable from the same Lua context as the existing gaze-logging hook and wire them in, (2) export kiosk world positions from the scenario graph into a static reference file, (3) validate end-to-end on one test session with both changes, not considering the task done without that validation running successfully.

### Evidence
**(1), corrected**: `core_camera.getPosition()`/`getQuat()` are confirmed callable - they're used directly inside `lerpCamToKiosk.lua`/`lerpCamFromKiosk.lua` (both read in a prior pass). But there is **no existing gaze-logging hook anywhere in BeamNG's Lua layer to wire them alongside** - a codebase-wide search for "varjo" or any of the gaze CSV's 46 column names inside `lua/` and the `EVChargingGame` UI app returns zero matches. Gaze capture is architecturally external to BeamNG entirely (a separate application using the Varjo SDK directly, not located in this codebase). The task's framing ("same Lua context as the existing gaze-logging hook") assumed a hook that doesn't exist; corrected here rather than silently building something that wouldn't actually solve the synchronization problem.

**(2)**: Confirmed in D021 that kiosk world positions are supplied as external input pins (`targetPos`/`targetRot`) to the generic camera-lerp nodes, not hardcoded - meaning a real scenario/flowgraph graph file holds the concrete values, and that file was not found anywhere in this installation (same gap D021 already noted). A one-time export script is a mechanism that can be written once that file is located, not something with real values to populate right now.

**(3), blocked, not faked**: No session exists anywhere with both head pose and kiosk position logged (neither change has been deployed - they can't be, from this session, since deploying requires editing and running the actual Varjo-side capture tool and the real flowgraph scenario file, neither of which are present here, on a Windows machine this session cannot reach). No synthetic/fabricated test session was created to manufacture a "successful" validation - that would produce a misleading result. This sub-task is honestly incomplete, not quietly skipped.

### Reason
Reporting "done" on a task whose validation step is structurally impossible from this environment would be a worse outcome than reporting it accurately as blocked - consistent with every other "this session cannot run BeamNG/Windows" limitation already on record (D004, D005).

### Alternatives Considered
(a) Write head-pose logging into a BeamNG Lua extension anyway, on the theory that it's directionally useful even without a confirmed integration point. (b) Fabricate a synthetic test session (made-up gaze + head-pose + kiosk-position numbers) to demonstrate the raycast math works, standing in for a real validation.

### Why Alternatives Were Not Chosen
(a) risks logging BeamNG's own camera pose while gaze is captured by an entirely separate process with its own (possibly different) sense of "head pose" - without knowing the real gaze-capture tool's architecture, this could easily produce two pose streams that don't actually describe the same thing, a worse outcome than no fix. (b) would satisfy the letter of "run a validation" while producing a number with no evidentiary value - exactly the "fake-looking AOI data" standing instruction prohibits, just moved one step earlier in the pipeline.

### Implementation
No code deployed (nothing to deploy against - no reachable BeamNG instance). Documented precisely what's needed and where it's blocked.

### Status
Under Investigation - (1) Verified for the API-access question, corrected for the hook-location assumption; (2) Proposed, no real data; (3) Blocked, explicitly not faked

### Impact
Objective 2, Objective 3 (new data collection requirements), Dataset description

### Remarks
Before this can move forward: locate the actual Varjo-side gaze-capture application's source (it is not in this repository) - that is the real place a head-pose-logging change belongs, since OpenXR/Varjo sessions typically expose head pose through the same API call gaze comes from, making this plausibly a small change to that tool rather than a new synchronization problem. Separately, locate the real flowgraph scenario file with kiosk coordinates. Both are "someone on the team who has access to the full project, not just this BeamNG install, needs to look" items - flagging to the user/mentor, not solvable from here.

---

## D028

### Date
2026-10-03

### Decision
Ran a real 20-trial compliance test for the malicious-condition override (not just D024's n=4). Hit a hard Gemini API quota exhaustion partway through both batches - reporting the real numbers from the valid trials obtained, with correctly-sized confidence intervals, rather than the artificially low rates a naive count (including API failures as "non-compliant") would have shown.

### Context / Problem
D024 found 2/4 compliance with the malicious override - too small to trust. Asked for a real 20-trial run, one prompt-engineering variant, and both options reported with numbers, no unilateral pick.

### Evidence
Script: `backend/test_automation_bias_reliability.py`. Both 20-trial batches (baseline wording, and a stronger imperative variant with the target kiosk named first) hit `429 RESOURCE_EXHAUSTED` from the Gemini API partway through - confirmed as a plan/quota cap, not a transient per-minute throttle (a 45-second wait and a fresh retry batch failed identically on every one of 16 further attempts). This is itself a real, practically relevant finding: the project's current Gemini quota is far too small to support the call volume `receive_ui.py`'s architecture already generates per real session (one VLM call per station plus one LLM call per assistant use), let alone a 20-trial reliability test - worth flagging for anyone budgeting a real data-collection round.

Excluding API-failure responses from the denominator (counting them as "non-compliant" would be wrong - they're not a model decision):
- **Baseline wording**: 8 of 11 valid trials complied (72.7%, 95% Wilson CI [43.4%, 90.3%])
- **Stronger wording** (imperative framing, names the target kiosk first, explicitly tells the model to disregard the anomalies it identified): 4 of 4 valid trials complied (100%, 95% CI [51.0%, 100%])

The point estimate favors the stronger wording, but the confidence intervals overlap substantially (driven by the stronger wording's very small valid-n after the quota cutoff) - **not enough evidence to confidently say the stronger wording is actually more reliable**, only that it didn't perform worse in the trials that completed.

**Both options, numbers stated, no pick made**: (a) further prompt-engineering (the stronger wording is a reasonable next iteration, given the directionally favorable point estimate, but needs a real 20/20 clean run - quota permitting - before trusting it); (b) a deterministic override (post-process the model's response, or skip calling the LLM for the target-kiosk decision and splice in a templated "recommend Kiosk N" sentence) - would give literally 100% reliability by construction, at the cost of ecological validity (the response is no longer a genuine model output, which matters if the study cares about what a compromised AI assistant's language actually looks like, not just whether participants trust a wrong recommendation).

### Reason
A point estimate from n=4 (D024) isn't a rate; the task's own framing (confidence interval, not point estimate) is the right standard, and reporting a contaminated/miscounted rate (my first script run before I caught the API-failure counting bug) would have been actively misleading in the wrong direction.

### Alternatives Considered
Count API failures as non-compliant trials (simpler code, wrong statistically) - this was literally what the first run of the script did, producing 40%/20%, both numbers discarded once the bug was caught.

### Why Alternatives Were Not Chosen
An API error is not a data point about the model's behavior - including it in the denominator systematically understates compliance and would have been reported as a worse finding than reality.

### Implementation
`backend/test_automation_bias_reliability.py` added. Raw per-trial results at `/tmp/automation_bias_reliability_results.json` and `/tmp/stronger_topup.json` (not moved into the repo - ephemeral test output, not a durable artifact; the summarized numbers above are what matters going forward).

### Status
Verified (the numbers obtained); Under Investigation (whether the stronger wording is actually better - CI too wide to say); the (a) vs (b) choice: explicitly left open, per the task's instruction

### Impact
Objective 2, Objective 5 (automation bias), Experimental design

### Remarks
Recommend, as a non-binding opinion: get a clean 20/20 run on the stronger wording once quota resets before deciding between (a) and (b) - the current data is suggestive, not conclusive. If (b) is chosen for ecological-validity reasons being judged not worth the reliability cost, that's a defensible call too, but it's the mentor/team's tradeoff to make, not a default to fall into because (a) hit an API limit during testing.

---

## D029

### Date
2026-10-03

### Decision
Produced `backend/rag_contaminated_sessions.json` - a labeled list of the 38 RAG-contaminated sessions (D023), for exclusion from any clean automation-bias/AI-recommendation-quality baseline. No fix applied to the RAG store itself.

### Context / Problem
D023 confirmed all 38 AI-assistant-using sessions are contaminated. Needed as a concrete, reusable artifact rather than a number restated each time.

### Evidence
File lists, per contaminated session: `session_dir` (unique, authoritative), `participant_id` (convenience field - imperfect for 2 edge cases: two different sessions both have participant suffix "001", and one entry's folder name is the already-known-glitched `..._126_glitched data` directory, corrected to participant_id "126" with a note), `first_assistant_use_iso` timestamp, and `prior_rag_documents_at_query_time` count (reused from D023's analysis).

### Reason
A labeling task, as scoped - make contamination status checkable by session ID without re-deriving it, not a fix.

### Alternatives Considered
Fold the list only into Decision.md prose (as D023 already did) without a separate machine-readable file.

### Why Alternatives Were Not Chosen
A prose list in a decision log isn't something an analysis script can load and filter against; a JSON file is.

### Implementation
`backend/rag_contaminated_sessions.json` created. `backend/rag_index/` and the RAG store's clearing behavior were not touched, per the standing hold shared with D006/D009/D018.

### Status
Implemented

### Impact
Dataset description, Experimental design, Objective 5 (automation bias)

### Remarks
—

---

## D030

### Date
2026-10-03

### Decision
Ran the bounded 3-candidate-fix spike on `aoi_mapper.py`'s miscalibration (D026). **Verdict: NOT SIMPLY FIXABLE** within this task's budget. The pinning is confirmed systematic (not noise) across all 5 of participant 041's trials regardless of true kiosk choice, but none of 3 tried coordinate transforms recovers the correct AOI, and a new piece of evidence (left/right-eye divergence) suggests the underlying problem is a vergence/depth issue, not a 2D screen-space calibration constant - i.e. structurally closer to D021's blocker than D026 first hoped. **D025's RQ1 rescoping is NOT reversed by this finding** - it stands.

### Context / Problem
D026 found `aoi_mapper.py` assigns 0% gaze to participant 021's demonstrably-chosen Kiosk 1, pinning 86% to Kiosk 3 instead, and asked whether this is a fixable coordinate bug (axis flip, origin, stale constant) rather than a deeper architectural problem - time-boxed to 3 candidate fixes, explicitly not to be allowed to drift into open-ended guessing.

### Evidence
**Setup, read directly from code and data, not assumed:** `aoi_mapper.py`'s own coordinate-system auto-detector (`detect_coord_system`), run against participant 021's real `gaze_projected_to_left_view_x/y` values for the station-page window, classifies the data as `signed_normalized` (i.e. assumes x,y ∈ [-1,1], mapped to screen-normalized via `(v+1)/2`). Restricted to the actual station decision window (3443 samples, all `status==2`), left-eye x ranges only **-0.084 to 0.522** (mean 0.329) - mapping to normalized x ≈ 0.46-0.76, which sits almost entirely inside `kiosk_3`'s hardcoded AOI rectangle (x: 0.49-0.72) - this is *why* the tool pins to kiosk_3, confirmed mechanically, not just observed as an output.

**3 candidate fixes tried, all against the same ground truth (021, true choice = Kiosk 1):**
1. **X-axis flip** (`norm_x = (1-x)/2`): predominantly lands on **kiosk_2** (87.6% overall, 52.5% in the final 20% of the window) - closer to the real answer by one column, but still wrong.
2. **Swap x/y axes**: still predominantly **kiosk_3** (70.4%) - ruled out.
3. **Empirical min-max rescale within the window** (assume the observed gaze range is the UI's true extent): scatters across AOIs with no clear winner and 31.6% landing on no AOI at all - ruled out.

None of the 3 produces kiosk_1 dominance (or even a plausible majority on the true answer) for participant 021, so per the task's own stop condition, no 4th attempt was made and no fix was validated against 041/100.

**New evidence this pass surfaced, not previously checked:** left-eye and right-eye projected-x means disagree by far more than normal inter-pupillary parallax would explain at this viewing distance - left-eye mapped mean ≈0.658 (kiosk_3), right-eye mapped mean ≈0.427 (kiosk_2) for the *same* gaze samples. A real converged gaze point this close to the HMD should show left/right agreement once correctly projected; this magnitude of disagreement is a signature of **vergence/depth-dependent projection** (the per-eye tangent-angle values depend on how far away the gazed-at point actually is, not just its on-screen direction) - meaning `gaze_projected_to_*_view_x/y` cannot be treated as a pure 2D screen coordinate at all without also knowing gaze depth, which circles back to needing real 3D/calibration information, not a 2D affine fix.

**Corroborating evidence the miscalibration is systematic, not noisy** (cheap check, not one of the 3 fix attempts): re-ran the *original, unfixed* mapper per-trial on participant 041 (5 station trials, true choices kiosk 2/1/3/2/1 respectively). Every single trial regardless of true choice assigns kiosk_3 as the dominant AOI (58-95% of samples), including no stronger signal on the one trial where kiosk_3 actually was the true answer than on the others. This rules out "D026 found a one-off anomaly" - the tool is consistently, confidently wrong in the same direction for a different participant and different ground truth too.

### Reason
The task's own explicit rule: 3 tries, then stop and report plainly rather than continuing to guess. The vergence-disagreement finding wasn't optional scope creep - it came up naturally while characterizing why the fixes failed and materially changes the diagnosis (depth-dependent, not purely 2D), which the task asked for ("describe what you ruled out and why this looks architecturally broken rather than miscalibrated").

### Alternatives Considered
(a) Treat "x-flip gets the right *column family* at least at the window's edges" as grounds to call it a partial fix and keep tuning. (b) Spend a 4th/5th attempt trying FOV-scale correction (e.g. dividing by an assumed Varjo XR-4 half-FOV tangent) since the real half-FOV is known from hardware specs (D001).

### Why Alternatives Were Not Chosen
(a) x-flip's 52.5%-in-closing-moments still names the wrong kiosk (2, not 1) - "closer" is not "correct," and the task's own instruction was to judge against whether gaze now lands predominantly on the true kiosk, which it didn't. (b) was considered but not run: it would still only correct for FOV scale, not the now-confirmed depth/vergence dependency - a 4th attempt addressing the wrong layer of the problem would have been guessing dressed up as rigor, which is exactly what the 3-try cap exists to prevent.

### Implementation
No code changed - `aoi_mapper.py` remains unmodified, consistent with D026. This entry documents the spike's result. **The RQ1 rescoping from D025 is explicitly NOT reversed**: it was never contingent on `aoi_mapper.py` specifically (D025's pilot used the separate, unlabeled-cluster `aoi_free_pilot.py` method and D021's head-pose/world-space finding, not this tool). This spike was a bounded check on whether a *cheaper* path back to labeled AOIs existed as an alternative to D021/D027's full fix - it does not, so D021/D027 (new data collection with head pose + kiosk position logging) remains the only concretely scoped way to get labeled AOI data, and D025's RQ1-revised wording stands as the going-forward plan for the existing 140 sessions.

### Status
Verified (the 3 fix attempts and their failure; the systematic-wrongness corroboration on 041; the left/right vergence-disagreement finding) - the deeper depth-dependent diagnosis itself is Proposed (consistent with the data, not independently confirmed against Varjo SDK documentation, which remains unavailable in this session per D026)

### Impact
Objective 2, Dataset description, Objective 3 (confirms, does not add to, D021/D027's requirements)

### Remarks
Worth stating plainly to the mentor: this closes off the "maybe the 2D UI panel is a cheaper fix than full world-space head pose" hope D026 raised. It isn't - both AOI-mapping paths on the existing 140 sessions (3D world-space via D021, and 2D screen-space via this one) are blocked for data-availability reasons (D021) or a vergence/depth issue this session can't calibrate away (this entry), not for lack of trying. If a deliberate gaze-to-UI calibration recording (participant looks at each of the 8 AOIs in sequence on command, several seconds each) is feasible to collect going forward, it would resolve both the FOV-scale question and let someone fit a depth-aware model empirically - but that's new data collection, same category as D021/D027's fix, not a fix applicable to existing data.

---

## D031

### Date
2026-10-03

### Decision
Scoped (not implemented) the cross-process gaze/head-pose timestamp-sync problem that D028's correction created. Found the actual gaze-capture application is genuinely unidentifiable from inside this repository - not merely "external" as D027 said, but literally zero trace of its source, process name, or language anywhere in this codebase copy, confirmed by grepping the gaze CSV's own exact column names project-wide. Proposed one architecture anyway, built on what the existing data provably shows about the two systems' clock relationship, flagged clearly as design-only.

### Context / Problem
D027 corrected the premise that head-pose logging was a one-file Lua edit - gaze capture is a separate external application, so head-pose (addable to BeamNG's Lua layer) and gaze (captured elsewhere) are two different processes needing timestamp reconciliation. Asked to identify the actual gaze-capture app, check for a shared-sync mechanism, and propose one architecture without implementing it.

### Evidence
**(1) The gaze-capture app cannot be identified from this repository - stronger claim than D027's.** Grepped the entire project (excluding the BeamNG engine binaries and the unrelated `vEVTrip` venv) for `varjo` (case-insensitive): only 2 hits, both just comments in `Decision.md`/`gaze_pilot.py` referencing Varjo's *data fields*, not its tooling. Separately grepped for the gaze CSV's own exact, distinctive column names (`gaze_projected_to_left_view`, `relative_to_video_first_frame_timestamp`, `inter_pupillary_distance_in_mm`) across every `.py/.cs/.lua/.cpp/.h/.json` file in the project: the only match is `aoi_mapper.py` itself (which merely reads the CSV), never a producer. The tool that writes this file's format does not exist anywhere in this installation - not hidden, not unindexed, genuinely absent. This can only be resolved by whoever has access to the full project / the lab machine that runs the Varjo headset, not from this session.

**(2) What CAN be determined about the clock relationship, from the data actually on disk (reused, not re-derived, from D008/D013's session-overlap method, applied to timestamps directly this time):** Checked whether the gaze file's own two timestamp columns drift relative to each other across a full session (021, 25064 samples, sampled every 500th row) - `relative_to_unix_epoch_timestamp - raw_timestamp` is **exactly constant for the entire session (0.0 ms spread)**. This means the capture tool computes its "epoch" timestamp as a single fixed anchor applied to an otherwise-monotonic counter (`raw_timestamp`), not by re-reading the wall clock per sample - internally self-consistent (no mid-session jumps from e.g. an NTP resync), but its *absolute* accuracy depends entirely on one unverifiable anchor computation inside a tool this session cannot read.

Separately confirmed `receive_ui.py`'s interaction-log timestamps (`timestamp_unix_ms`) are stamped by the Python backend's own wall clock (`datetime.now()`/`time.time()`) at the moment each BeamNG message is *received* over the local socket (`receive_ui.py`, confirmed by reading the relevant handler code) - not BeamNG's internal sim time, and not independent of the backend process's own clock. `system_config.json` shows BeamNG connects to the backend at `localhost:25252` - both processes are confirmed to share one machine. The Varjo headset's eye tracker necessarily plugs into whichever PC runs the VR session, so the gaze-capture app almost certainly runs on that same single physical machine too - a well-justified inference from the deployment constraints already on record (D004's "BeamNG needs a Windows GPU workstation"), not a new assumption, but still not independently confirmed since the app itself can't be found.

**(3) Existing precedent that session-level wall-clock alignment already works end-to-end:** D020/D026/D030's own scripts already join gaze timestamps to interaction-log timestamps today with nothing more than a unit conversion (ns→ms) - no custom sync protocol, no offset correction - and produce station-window gaze subsets that line up with the right real-world events (confirmed via the ground-truth checks in D026/D030). This is existing, working evidence that the two systems' clocks are close enough for session/trial-level work already; the open question is specifically whether they're close enough for *fixation*-level (hundreds-of-ms) claims, which D020 established as the relevant timescale.

### Reason
Scoping accurately (rather than assuming a one-file fix, D027's original correction) means stating plainly what can and can't be verified from this session before proposing a design - guessing at the tool's internals would risk the same "fabricated line numbers" failure mode this project's standing rule prohibits.

### Alternatives Considered
(a) Assume LSL (Lab Streaming Layer) is already in use for gaze, by analogy with `muse.py`'s LSL approach for EEG (D009), and design around that. (b) Treat NTP-level shared-system-clock as sufficient without further justification, since both processes are "probably" on one machine.

### Why Alternatives Were Not Chosen
(a) would be fabricating the capture tool's architecture by analogy to an unrelated tool (`muse.py` was already shown in D009 to not even match the *actual* EEG capture path used) - exactly the kind of inference-from-a-different-system's-convention that's been wrong before in this project. (b) the task's framing explicitly warns that plain NTP-level sync isn't good enough for fixation-level claims by default; the single-machine deployment inference (point 2 above) is a materially stronger claim than generic NTP sync, so it's stated as such and still flagged as unverified rather than asserted as sufficient.

### Implementation
No code written (design-only, per the task's explicit instruction). Proposed architecture for new sessions, to be validated once someone locates the real capture tool:
1. **Head-pose logging**: add a BeamNG Lua hook calling the confirmed-callable `core_camera.getPosition()`/`getQuat()` (D027) on a per-frame or fixed-interval basis, and send it over the **existing** BeamNG→backend socket channel already used for interaction events - so it gets timestamped by the Python backend's wall clock the same way `interactions_*.csv` rows already are. This deliberately keeps head-pose in the *same* clock domain as the interaction log (not a new one), since that's the domain already proven (point 3) to compose with gaze via simple epoch alignment.
2. **Kiosk world positions**: export once from the real scenario/flowgraph file (still not located in this install - same gap as D021/D027) as a static table if fixed, or logged per-session if randomized.
3. **Reconciliation**: nearest-timestamp join between the head-pose stream and the gaze stream's epoch-ns timestamps.
4. **The one new, concrete recommendation this pass adds**: before trusting *fixation-level* claims from the reconciled streams, run one deliberate calibration protocol at the start of each new recording session - a distinctive, sharp head motion (e.g. a fast nod or shake) performed on command, logged independently by both systems. Cross-correlating that one shared event gives a measured, per-session offset/skew estimate between the two clocks, rather than assuming epoch-timestamp agreement is good enough by construction. This is cheap (seconds of protocol time) and directly answers the "is this good enough for fixation-level analysis" question empirically instead of by assumption.

### Status
Under Investigation - (1) Verified (the capture tool is unidentifiable from this repo); (2) Verified (what the data shows about clock relationships) with an explicitly-flagged unverified inference (single-machine deployment); (3) Verified (existing alignment precedent); the proposed architecture (4 points above): Proposed, not implemented, not yet reviewed

### Impact
Objective 2, Objective 3 (new data collection requirements), Dataset description

### Remarks
The real blocker for Task 2, same shape as D021/D027's kiosk-position gap: someone with access to the actual lab machine/project needs to locate the Varjo-side capture application's source or config. Worth asking directly: is it a vendor tool (Varjo Base / a bundled SDK sample), or a custom script written by someone on the team? That answer alone determines whether point 4's calibration protocol is even the right ask, or whether the tool already exposes something better (e.g. an OpenXR shared predicted-display-time) that this session has no way to know about.

---

## D032

### Date
2026-10-03

### Decision
Topped up the automation-bias compliance test (D028) using the already-collected trials rather than discarding them. **Baseline wording reached the full 20/20 target: 16/20 complied (80.0%, 95% Wilson CI [58.4%, 91.9%]).** Stronger wording did not reach 20 - hit the same daily quota cap again at 6/20 (6/6 complied so far, 100%, 95% CI [61.0%, 100.0%]). Identified the exact quota mechanics from the API's own error payload, including a reset-time estimate.

### Context / Problem
D028 left both conditions short (11/20 baseline, 4/20 stronger) after hitting a Gemini API quota wall. Asked to resume (not restart) and top up to 20/20 each, reusing the 11 and 4 already collected, and - if blocked again - to identify exactly which quota and when it resets rather than just reporting failure.

### Evidence
Needed local packages (`python-dotenv`, `google-genai`) were missing from the system Python environment this session has access to (prior sessions' runs are not reproducible from a clean environment without this) - installed via `pip3 install --user`, confirmed working with one live test call before running the real batch.

Wrote `backend/test_automation_bias_topup.py`, which loads the prior run's raw results (`/tmp/automation_bias_reliability_results.json`), filters out the API-failure rows (same non-fabrication rule as D028), and runs only the additional trials needed to reach 20 valid per condition - reusing, not re-collecting, the valid trials already on file.

**Baseline**: 11 prior valid + 9 new = 20/20. Hit one transient `503 UNAVAILABLE` ("model experiencing high demand") on the first new attempt - this is a different error class from the 429 quota cap (confirmed by reading the error body: no `RESOURCE_EXHAUSTED`/quota language, just a capacity message) and resolved on retry with backoff, so the script was extended mid-task to retry transient 503s (up to 5 consecutive) while still treating 429 as a hard stop. Final: 16/20 complied.

**Stronger wording**: 4 prior valid + 2 new = 6, then hit `429 RESOURCE_EXHAUSTED` again on the 3rd new attempt. **The quota's exact mechanics, read directly from the error payload** (not inferred): `quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue: 20`, model `gemini-2.5-flash-lite` (the project's actual configured default per `ai_assistant.py`'s `GEMINI_MODEL` env default - not the `gemini-2.5-flash` cited in D024's narration, a minor naming slip in that earlier entry, not a different model actually being used). This is a **project-wide, per-model, per-day cap of exactly 20 requests on the free tier** - meaning one 20-trial batch alone exhausts the entire day's quota by construction, before any second condition can run the same day. The error's own `retryDelay` field gave an exact reset estimate: ~17h15m from the moment of that specific 429, i.e. **quota resets approximately 2026-10-04, ~14:15 IST** (computed from this run's wall-clock time, 2026-10-03 ~20:57 IST + 17h15m).

### Reason
The task explicitly asked to resume rather than restart, and to diagnose the quota mechanism (not just hit it again and report failure) if blocked - both directly actionable asks, not optional extras.

### Alternatives Considered
(a) Restart both batches from 0 (discarding the 11+4 already collected). (b) Treat the first new 503 the same as a 429 and stop immediately, under-running the baseline batch unnecessarily.

### Why Alternatives Were Not Chosen
(a) would have wasted already-spent quota for no reason - the task was explicit about reuse. (b) would have incorrectly stopped the baseline topup at 11/20 over a transient, retryable error, when the very next attempt (and 7 after that) succeeded fine - conflating "model momentarily busy" with "daily cap reached" would have under-reported how much quota was actually available this session.

### Implementation
`backend/test_automation_bias_topup.py` added. Combined raw results (prior valid + new) written to `/tmp/automation_bias_topup_results.json` (ephemeral, not moved into the repo, consistent with D028's own `/tmp` output convention). No change to `ai_assistant.py` or the RAG store.

### Status
Verified (baseline: full 20/20, real number); Under Investigation (stronger wording: still short at 6/20 - not enough to compare against baseline's CI yet, same caveat D028 already raised about overlapping CIs at low n)

### Impact
Objective 2, Objective 5 (automation bias), Experimental design

### Remarks
Resume the stronger-wording batch after ~2026-10-04 14:15 IST (estimated from this run's own quota error, not a guess) - should need only 14 more valid trials to finish. Caught and fixed, within this same entry, a real bug this would otherwise have hit: `load_prior_valid()` originally always re-read the *original* D028 file (4 stronger-wording valid trials), ignoring this run's own combined output (`/tmp/automation_bias_topup_results.json`, which already has 6) - re-running the script as first written would have silently re-spent quota re-collecting the same 2 trials obtained today. Fixed to prefer the topup output file once it exists for a given condition, falling back to the original D028 file only when no topup has run yet. Just rerun `backend/test_automation_bias_topup.py` as-is after the reset - no manual file surgery needed.

---

## D033

### Date
2026-10-03

### Decision
Synced the Research Audit document with every finding from D021-D032 (AOI mapping's two independent blockers, the automation-bias implementation and live-model test results, the quantified RAG contamination, the RQ1 rescoping, and the cross-process sync scoping) - published as `EV Charging VR Research Audit3.pdf`.

### Context / Problem
The user asked to update the Research Audit doc with recent findings. `EV Charging VR Research Audit2.pdf` (the latest version on disk) was current only through D020 - it predates all of D021-D032, including the two findings (D030's aoi_mapper falsification, D025's RQ1 rescoping) this same session's earlier task was explicitly told not to write into documentation until reviewed. That review happened (the user saw and accepted the Task 1-3 report), so the hold no longer applies.

### Evidence
No editable source for the Research Audit exists anywhere this session can reach - not a Google Doc (checked via Drive search, zero matches on title), not a `.docx`/`.md` file in the project, only the two prior PDF exports. Extracted the full text and the one embedded diagram image from `Audit2.pdf` (pypdf/pdfplumber), confirmed its existing structure already cross-references `Decision.md` entries by number up through D020 (e.g. "see Decision D020"), and rebuilt the document section-by-section with reportlab, preserving that same citation convention and extending it through D032. Visually checked every rendered page (via pypdfium2) for table overflow, clipped text, and correct image placement before sending - none found.

Substantive content changes, not just an appended changelog: the Objective-status table and Objective 2 section now state the automation-bias condition as implemented and tested (not "missing"), with the D024/D028/D032 compliance-rate table and the exact Gemini quota mechanics; a new "AOI mapping: now conclusively blocked... via two independent routes" subsection replaces the old single-blocker framing, covering both D021 (world-space/head-pose) and D026/D030 (`aoi_mapper.py`, falsified, vergence issue); the RAG-contamination paragraph now carries D023's hard numbers (38/140 sessions, 100% contaminated) and D029's exclusion-list artifact; "Proposed research direction" gained explicit RQ1/RQ2 wording with D025's rescoping stated as a flagged update, not silently folded in; the novelty-analysis table, roadmap, and presentation-summary sections were updated to match. Objective 1 (FPS) and Objective 4 (literature review) were left untouched - no new decision this round touched either.

### Reason
The user's instruction was explicit and unconditional ("update... with all recent findings"), and the standing hold from the Task 1-3 round ("don't write documentation until Task 1's verdict is reviewed") was specifically about pre-empting a review that has since happened, not a permanent block.

### Alternatives Considered
(a) Append a short "recent findings" changelog section to the existing PDF rather than integrating changes into the relevant original sections. (b) Try to locate or recreate a live editable doc (e.g. a new Claude Doc) instead of regenerating a versioned PDF.

### Why Alternatives Were Not Chosen
(a) would have left the document internally inconsistent - e.g. Objective 2 would still say the automation-bias condition is "missing" in one place while a changelog said it was "done" in another, which is worse than not updating at all for anyone reading only the main text. (b) would have created a new document with no link to the one the user actually asked about and no way to confirm it updates "the" doc rather than a disconnected copy - regenerating the same versioned-PDF artifact the user already has a precedent for (`Audit.pdf` -> `Audit2.pdf`) was the faithful interpretation of "update the doc."

### Implementation
`EV Charging VR Research Audit3.pdf` created at the project root (14 pages, down from 26 - denser layout, not missing content). Source build script at the session scratchpad (`build_audit3.py`), not moved into the repo - regenerable but not a durable project artifact. Sent to the user via SendUserFile.

### Status
Implemented; Verified (every page visually checked for rendering correctness before sending)

### Impact
Objective 2, Objective 5 (automation bias), Experimental Plan, Dataset description, Novelty analysis

### Remarks
This PDF is now the authoritative "latest" Research Audit snapshot, but it is a regenerated reconstruction, not a live-edited original - there is still no durable, directly-editable source for this document anywhere in the project. If the team wants this to stop requiring a full reconstruction each time (this one took extracting text/images from the prior PDF and rebuilding ~14 pages from scratch), worth considering migrating it to an actual live doc (e.g. a Claude Doc or a shared Google Doc) that future updates could edit in place instead.

---

## D034

### Date
2026-10-03

### Decision
Finalized the Phase 1 data schema (`backend/pipeline/SCHEMA.md`) for the real Objective 2 pipeline build, consolidating D001-D033 into one concrete, machine-usable spec rather than a placeholder - and stated per-modality availability explicitly, participant by participant, rather than as an aggregate percentage.

### Context / Problem
This round's brief asked to "confirm, don't re-discover" the schema before writing any feature-extraction code, covering behavioural/event logs (with D029's RAG-contamination flag), gaze (the D025/D030-validated AOI-free feature set, explicitly not the old AOI-anchored dwell/TTFF), and EEG (band power in low-motion windows, D019-qualified participants only).

### Evidence
Recomputed D019's 67-participant EEG inclusion list directly from `backend/Muse/decoded/decode_summary_resynced.csv` rather than trusting the number from memory - first pass using the `sync_check` column gave 65, not 67; tracing the discrepancy found `best_sync` (not `sync_check`) is the column that reflects D019's own duplicate-folder fix (055 and 082 resolve to `overlap_confirmed` only in `best_sync`, with `n_candidate_sessions` 3.0/2.0 confirming the multi-folder check ran). Using `best_sync` reproduced exactly 67/76, confirming D019's published number against the raw artifact rather than re-asserting it.

Schema fields finalized: behavioural (`decision` charge/skip, `kiosk_used`, `kiosk_attack`, `charge_amount`, `points_lost`, `ai_help_used`, `rag_contaminated` from D029's JSON), gaze (`gaze_n_fixations/n_clusters/n_transitions/transitions_per_fixation/dispersion/entropy` - the exact fields `aoi_free_pilot.py` already validated, D025/D030, not reinvented), EEG (16 columns: relative band power per channel x band, delta/theta/alpha/beta, plus `eeg_low_motion_fraction`). Every modality carries an explicit `*_missing` boolean - stated as a rule, not left implicit, that missing modalities must never be zero-filled or imputed.

### Reason
A schema with real, verified field provenance is what the rest of this round's pipeline code is built against - re-deriving the EEG list from scratch rather than trusting D019's stated number from memory is the same "verify against the raw artifact" standard the project has applied throughout (D008->D013->D019's own escalating verification chain).

### Alternatives Considered
Take D019's "67/140" figure as already-settled and skip re-deriving it from the CSV.

### Why Alternatives Were Not Chosen
It would have been trusting a remembered number instead of the artifact that number came from - cheap to re-derive (one script, seconds to run) and it surfaced a real, previously-undocumented detail (which column actually holds the corrected check) that the next person extending this pipeline would otherwise have had to rediscover the hard way.

### Implementation
`backend/pipeline/SCHEMA.md` added.

### Status
Verified

### Impact
Objective 2, AI pipeline, Dataset description

### Remarks
—

---

## D035

### Date
2026-10-03

### Decision
Built and ran the real Phase 2 feature-extraction pipeline (`backend/pipeline/build_feature_table.py`) across all discoverable sessions - not another pilot. Produced `feature_table.csv`: 1123 participant x station-event rows across 126 participants, with gaze features for 1057 rows and EEG features for 324 rows (58 participants), joined with explicit missingness flags per the Phase 1 schema.

### Context / Problem
D020/D025/D030 validated the gaze AOI-free method on only 3 pilot participants, explicitly held back from scaling until validated. This round's brief said that validation has now happened and the method should run across all 140 sessions for real, alongside EEG band-power extraction for the 67 D019-qualified participants and behavioural labels from game logs only.

### Evidence
**Session discovery surfaced two real data-quality issues, not pipeline bugs, caught by testing on real participants before the full run rather than assuming the naming convention would hold:**
1. Participants 001/002's gaze files are named `varjo_gaze_output_<timestamp>.csv`, not `<pid>.csv` like every later session - initial filename-pattern matching missed them entirely. Fixed by detecting gaze files via header content (`gaze_forward_x` present) instead of filename convention.
2. 6 participants (001, 022, 034, 055, 064, 082) have more than one `session_*_<pid>` folder on disk - the exact set D019 already flagged for the EEG cross-check's duplicate-folder bug, now confirmed to be a broader raw_data issue, not EEG-specific. For each, kept only the folder with the most interaction-log rows as canonical (the real played session) and explicitly did NOT borrow a gaze file from a sibling duplicate folder, since that folder's gaze timestamps belong to a different playthrough and would silently mismatch the real decision windows if reused.

**6 participants (040, 049, 058, 059, 071, 072) produced zero station-events** - checked directly, not assumed: their interaction logs are genuinely near-empty (9-23 lines, zero `Reached` events), the same pattern already documented for 058 in D019/D013. Not a parsing bug - confirmed by manual inspection of the raw files for 3 of the 6.

**Two real timestamp-unit bugs caught and fixed before trusting any EEG output**: the decoded EEG/ACCGYRO CSVs' `timestamp_utc` column parses in pandas as microsecond-precision (`datetime64[us]`), not nanosecond - dividing `.astype("int64")` by 1e6 (nanosecond convention, correct for the gaze CSV's own raw timestamp field) silently produced timestamps 1000x too small (seconds-scale instead of ms-scale) and made every EEG window lookup return nothing. Caught by testing on participant 008 (a known EEG-qualified participant) before the full run and finding `eeg_band_power_in_window` returned `None` for every window, then tracing why rather than accepting the null result. Fixed by dividing by 1e3 for this column specifically. Separately, `np.trapz` does not exist in the numpy version in this environment (removed upstream) - replaced with `np.trapezoid`.

**Final run**: 132 canonical sessions discovered (138 raw folders minus 6 duplicate-folder collisions), 126 participants produced at least one station-event, 1123 total rows. `gaze_missing` true for 66/1123 rows (3 participants with no gaze file at all: 069, 082, 132). `eeg_missing` true for 799/1123 rows (not EEG-qualified, exactly the complement of D019's 67). `rag_contaminated` true wherever the session matches D029's list. Decision counts: 808 charge, 315 skip; risky (charge at a Cyber-Attack kiosk) = 214/1123 (19.1%).

### Reason
The task explicitly asked for the real pipeline run on all sessions, reusing the already-validated method rather than rewriting it - and the project's standing rule ("verify before scaling," D008/D013/D019/D020's own precedent) means catching bugs on a known test case before trusting output across 140 sessions, not after.

### Alternatives Considered
(a) Trust the filename-based gaze-file convention and report 001/002 as gaze-missing. (b) Skip the duplicate-folder dedup and let 6 participants contribute two sets of station-events each. (c) Accept `eeg_band_power_in_window` returning `None` for everyone as "EEG features aren't computable in these windows" rather than debugging the null result.

### Why Alternatives Were Not Chosen
(a) and (b) would have produced a technically-running pipeline with wrong answers - exactly the "it runs" vs "it's correct" gap this project's standing rule exists to catch (D026 is the precedent for how expensive it is to skip this check). (c) would have silently thrown away the entire EEG modality while looking like a legitimate missingness result instead of a unit-conversion bug - caught specifically because D019's EEG work already established participant 008 as a real positive case to test against, not an arbitrary choice.

### Implementation
`backend/pipeline/build_feature_table.py` added; output at `backend/pipeline/feature_table.csv`.

### Status
Implemented; Verified (spot-checked against known ground truth: participant 008's EEG/gaze features compute plausible non-null values; the duplicate-folder list matches D019's independently-derived list exactly; the EEG-qualified count behind `eeg_missing` matches D019/D034's 67 exactly)

### Impact
Objective 2, AI pipeline, Dataset description, Experimental plan

### Remarks
069/082/132 (gaze-missing) and 040/049/058/059/071/072 (zero station-events) are real, now-documented data gaps, not something this pipeline can route around. Worth folding into the Research Audit's dataset-description section next time it's updated, alongside the existing EEG/gaze/RAG findings.

---

## D036

### Date
2026-10-03

### Decision
Wired a local-SLM backend option into `ai_assistant.py` (`llm_backend="local_slm"`), for Phase 3's automation-bias data generation going forward - additive, default-unchanged, and explicitly kept separate from the existing 140 sessions' AI-assistant data, which stays flagged contaminated (D029) and excluded from any clean baseline regardless of which backend future sessions use.

### Context / Problem
Phase 0 (D038) needed a way to run the exact same prompt-construction logic already built and tested for Gemini (D024/D028/D032) against a locally-run model instead, and Phase 3 asked for that path to be wired into the actual simulation flow for upcoming new data collection, not just a standalone test script.

### Evidence
Added `llm_backend` ("gemini" default / "local_slm"), `local_slm_model`, `local_slm_url` constructor parameters to `AIAssistant`. Default path is unchanged - verified by construction (`AIAssistant()` with no args still reports `_llm_backend == "gemini"` and `_invoke_llm` hits the exact same Gemini/OpenAI branches as before, now gated behind an `if self._llm_backend == "local_slm"` early-return that only fires when explicitly requested). A new `_invoke_local_slm()` method posts to a local Ollama server's `/api/generate` endpoint and returns its response text (or an explicit `"Local SLM request failed: ..."` string on error, mirroring the existing Gemini-failure string convention so downstream compliance-checking code treats both the same way). `_build_full_prompt`'s condition/malicious_target_kiosk logic (D024) was not touched - the new backend only changes where the already-built prompt text gets sent.

### Reason
The brief's explicit instruction: reuse the exact prompt structure already built and tested for Gemini, swap only the inference destination, and keep this separate from the existing (contaminated, D029) 140-session data rather than touching `receive_ui.py`'s real gameplay call site.

### Alternatives Considered
(a) Build a separate, parallel `LocalSLMAssistant` class duplicating `_build_full_prompt`'s logic. (b) Wire the new backend into `receive_ui.py`'s real call site now, so it's live for the next data-collection round immediately.

### Why Alternatives Were Not Chosen
(a) would risk the two prompt implementations drifting apart over time, defeating the point of a direct comparison against Gemini's measured rates. (b) is out of scope for this round - the brief asked to wire the *module*, not to deploy it into live data collection, which is a separate decision for the team once Phase 0's verdict (D038) says whether prompting alone is reliable enough to use as-is.

### Implementation
`backend/ai_assistant.py` (`__init__`, new `_invoke_local_slm`, `_invoke_llm` early-return). `backend/test_automation_bias_slm.py` added as the Phase 0 test harness that exercises this path (see D038).

### Status
Implemented; Verified (default-path no-op confirmed by construction; the new path's actual output quality is reported in D038, not here)

### Impact
Objective 2, Objective 5 (automation bias), Experimental design

### Remarks
`receive_ui.py`'s real call site still only constructs `AIAssistant()` with no `llm_backend` argument, so nothing about live gameplay changes until someone deliberately opts a future data-collection session into `llm_backend="local_slm"`.

---

## D037

### Date
2026-10-03

### Decision
Ran the real Phase 4A classical-baseline models (logistic regression, random forest, XGBoost) on the Phase 2 feature table, participant-level `GroupKFold` splits throughout, with the full behaviour/gaze/EEG modality ablation the brief required. Then ran the real Phase 4B MLP gate check. **Verdict: behaviour-only Random Forest is the best model found (balanced accuracy 0.632, AUROC 0.712); gaze-only barely beats chance; EEG-only is at or below chance; the MLP did not beat the Phase A baseline, so Phase C (LSTM/GRU) was correctly not attempted per the brief's own gating rule.**

### Context / Problem
The brief's phased model-training rules (unchanged from the original pipeline brief): classical baselines first, MLP only if it beats them, LSTM/GRU only if that beats the MLP, no Transformer this round regardless - plus a mandatory modality ablation reporting honestly which modality actually carries signal, "if gaze-only wins, say so" explicitly cited as the standard to hold to.

### Evidence
Label: `risky = 1` iff `decision=="charge" AND kiosk_attack=="Cyber Attack"` (charging at a kiosk already flagged risky in that session's own game log) - derived only from `decision`/`kiosk_attack`, both game-log fields already in the Phase 2 table; never from gaze or EEG. Base rate 19.1% (214/1123).

5-fold participant-level `GroupKFold` (no trial-level leakage), median imputation + standardization fit on train folds only, against a majority-class baseline (balanced_accuracy=0.5 by construction in every subset).

| Feature set | n rows (participants) | Best model | Balanced acc. | F1 | AUROC |
|---|---|---|---|---|---|
| Behaviour-only | 1123 (126) | RandomForest | **0.632** | 0.393 | **0.712** |
| Gaze-only | 1057 (122) | LogisticRegression | 0.576 | 0.323 | 0.615 |
| EEG-only | 324 (58) | XGBoost | 0.478 | 0.020 | 0.294 |
| Behaviour+gaze | 1057 (122) | LogisticRegression | 0.576 | 0.323 | 0.622 |
| Behaviour+gaze+EEG (EEG-qualified subset) | 308 (56) | XGBoost | 0.486 | 0.027 | 0.514 |

Full per-model numbers in `backend/pipeline/phase4a_ablation_results.csv`. **Phase 4B (MLP on fused features)**, run for real against this exact Phase A result, not skipped on the assumption it would lose: behaviour+gaze MLP scored balanced_acc=0.497/AUROC=0.522 (n=1057); behaviour+gaze+EEG MLP scored 0.485/0.458 (n=308) - both below the 0.632/0.712 Phase A baseline it needed to beat on *both* metrics. Per the brief's own gate, Phase C (LSTM/GRU) was therefore correctly not run this round.

### Reason
"Report which modality actually carries signal, same honesty standard as before" was the brief's explicit instruction, and the honest answer here is uncomfortable but real: behavioural features (decision latency, AI-help use, RAG-contamination flag) carry more separable signal than gaze does at this sample size, and EEG currently adds noise rather than signal (consistent with this project's own standing caution since D010/D011 about expecting little from a 4-channel Muse at n~58-67).

### Alternatives Considered
(a) Report only the best-performing feature set (behaviour-only) as "the pipeline result," without surfacing the weaker gaze/EEG numbers. (b) Skip Phase 4B (MLP) since Phase A's baseline already looked hard to beat on this sample size, saving the compute.

### Why Alternatives Were Not Chosen
(a) would violate the brief's explicit ablation-honesty requirement and this project's standing "don't overclaim" rule - the EEG-only and combined-modality numbers are exactly the kind of finding a reviewer needs to see stated, not hidden. (b) would have turned a stated gate ("proceed only if it beats Phase A") into an assumption rather than a measured check - cheap to actually run (a few minutes of sklearn `MLPClassifier`), so there was no real cost to doing it for real.

### Implementation
`backend/pipeline/train_baselines.py` and `backend/pipeline/train_mlp.py` added. Results at `backend/pipeline/phase4a_ablation_results.csv`. Required installing `xgboost` and its `libomp` runtime dependency (`brew install libomp`) into this session's environment - not previously present.

### Status
Verified (Phase A and 4B numbers, both run for real); the behaviour-only "signal" itself carries an unresolved caveat - see Remarks

### Impact
Objective 2, AI pipeline, Experimental plan

### Remarks
**A caveat worth flagging rather than letting the 0.632/0.712 behaviour-only number stand unqualified**: `rag_contaminated` and session-level timing are both in the behaviour-only feature set, and both correlate with *when in the data-collection period* a session happened, not necessarily with the participant's actual decision-making process - some of this "signal" could be a time-confound (e.g., attack-probability config or participant pool characteristics drifting over the ~4-month collection window) rather than genuine behavioural information. Worth checking, before this number is cited anywhere, whether `window_duration_s` and `ai_help_used` alone (dropping `rag_contaminated`) hold up on their own - not done this round, flagged as the natural next check. Separately, EEG's poor showing is consistent with - not a reversal of - this project's existing caution about EEG at this sample size; it should not be read as "EEG has no signal in principle," only "not detectable with 58-67 participants and simple relative band power."

---

## D038

### Date
2026-10-03

### Decision
Phase 0 SLM feasibility, run for real, not just scoped: **verdict is FIXABLE BY PROMPTING, conditional on wording - no fine-tuning needed for now.** Selected Mistral-7B-Instruct-v0.3 (Apache-2.0) as the starting local model; ran the exact D024/D028/D032 prompt logic against it locally via Ollama; the stronger override wording reached a full, clean 20/20 = 100% compliance (95% CI [83.9%, 100%]), matching Gemini's top-end result, while the baseline wording was measurably less reliable than Gemini's (60% vs. 80%).

### Context / Problem
This round's brief asked, before building anything else, whether a locally-run SLM (replacing the Gemini free-tier quota that blocked D028/D032's compliance testing) can be steered by prompting alone, reusing the exact condition/malicious_target_kiosk prompt logic already built for Gemini (D024) rather than re-deriving it - with a direct, comparably-sized compliance test against Gemini's measured rates, and fine-tuning explicitly out of scope for this round regardless of the verdict.

### Evidence
**Model selection (desk check, VRAM against the target RTX 4090's 24GB - not measured on that card from this session, see Remarks):** three candidates considered - Phi-3.5-mini-instruct (3.8B, MIT license, ~2.2GB at 4-bit), Llama-3.2-3B-Instruct (3B, Meta's Llama 3.2 community license - permissive for a student project but carries redistribution/usage clauses a pure OSS license doesn't), Mistral-7B-Instruct-v0.3 (7B, Apache-2.0, ~4.4GB at Ollama's default quantization). All three leave enormous VRAM headroom on a 24GB card - quantized 7B models need roughly 4-5GB, nowhere near the binding constraint. Picked **Mistral-7B-Instruct-v0.3**: the cleanest license (Apache-2.0, zero usage restrictions, unlike Llama 3.2's community license) and a model large enough that a compliance test on it says something about instruction-following capability, not just "is the model too weak to follow any system-style instruction at all" (a real confound at 3B that would make an automation-bias measurement hard to interpret).

**Infrastructure, not fine-tuning, per the explicit instruction not to fine-tune this round**: installed Ollama locally (`brew install ollama`) since this session has no access to the actual RTX 4090 workstation (same category of environment constraint as D004/D027 - this runs on macOS/Apple Silicon, not the target Windows/CUDA machine). Pulled `mistral:7b-instruct` (4.4GB). Reused `AIAssistant._build_full_prompt(condition="malicious", malicious_target_kiosk=...)` verbatim (D024's exact logic, D036 wired the backend swap) - confirmed byte-identical prompt text to the Gemini runs by construction, not by re-typing it.

**Real compliance test, same fixed 3-kiosk state, same two wordings, same `complied()`/Wilson-CI code as D028/D032** (`backend/test_automation_bias_slm.py`): zero API/inference errors across all 40 trials (local inference has no daily quota - the whole point of this phase).

| Condition | Valid trials | Complied | Rate | 95% Wilson CI |
|---|---|---|---|---|
| Baseline wording (local Mistral-7B) | 20/20 | 12 | 60.0% | [38.7%, 78.1%] |
| Stronger wording (local Mistral-7B) | 20/20 | 20 | **100.0%** | **[83.9%, 100%]** |
| Baseline wording (Gemini, D028/D032, for comparison) | 20/20 | 16 | 80.0% | [58.4%, 91.9%] |
| Stronger wording (Gemini, D028/D032, for comparison) | 6/20 (quota-blocked) | 6 | 100.0% | [61.0%, 100%] |

Full raw replies at `/tmp/automation_bias_slm_results.json` (ephemeral, same convention as D028's raw-output files).

### Reason
The brief's own framing: a direct, comparably-sized comparison point against Gemini's measured rates, not a fresh exploratory benchmark - reusing the identical prompt-construction code and test harness (not just "a similar prompt") is what makes the 60%/100% numbers actually comparable to Gemini's 80%/100%, rather than two unrelated measurements that happen to use the same words.

### Alternatives Considered
(a) Pick a smaller model (Llama-3.2-3B or Phi-3.5-mini) to minimize local inference time, given this session's Mac has no RTX 4090. (b) Treat the baseline wording's weaker 60% result as disqualifying and recommend fine-tuning anyway, despite the stronger wording's clean 100%.

### Why Alternatives Were Not Chosen
(a) would have saved some local wall-clock time (the 40-trial run took well under 20 minutes even on a 16GB Apple Silicon Mac) at the cost of a more confound-prone result - a 3B model refusing an instruction for capability reasons rather than any analogue of "alignment" would be a weaker, less interpretable comparison point. (b) would misread the brief's own instruction: the baseline-wording number is reported honestly (and is in fact notably *worse* than Gemini's), but the question asked was whether prompting alone is "reliably steerable enough to use as-is" - and with the stronger wording, it demonstrably is (100%, CI floor 83.9%), so the honest verdict is yes-with-a-caveat-about-which-wording, not a blanket no.

### Implementation
`backend/test_automation_bias_slm.py` added (Phase 0 test harness). `backend/ai_assistant.py`'s `llm_backend="local_slm"` option (D036) is the production-facing version of the same call path this test exercises directly. Ollama installed via Homebrew; `mistral:7b-instruct` pulled (4.4GB, `/Users/naman/.ollama/models/`).

### Status
Verified (the measured compliance rates, both wordings, full 20/20 each, zero errors); the model-selection VRAM claim for the actual RTX 4090 target hardware: UNVERIFIED (desk reasoning from published model sizes, not measured on that card - this session has no access to it, same constraint as the FPS objective's Windows/GPU gap)

### Impact
Objective 2, Objective 5 (automation bias), Experimental design, AI pipeline

### Remarks
**Verdict, stated plainly per the brief's own framing: fine-tuning is not needed for now.** Use the stronger (imperative, lead-with-target) override wording, not the baseline wording, if this local-SLM path is adopted for new automation-bias data collection - the baseline wording alone is measurably less reliable on this smaller model than it was on Gemini, but the fix was already sitting in this project's own prior work (D028's stronger-wording variant), not a new prompt-engineering effort. If the team later wants the baseline-style wording to also hit a high compliance rate on a local model without resorting to the stronger/more heavy-handed override text, *that* specific gap is what LoRA fine-tuning on synthetic malicious-recommendation examples would be for - scoped only as a contingency, not started, consistent with the explicit instruction not to fine-tune this round regardless of verdict. The VRAM/license comparison across the 3 candidate models was a desk check, not a measurement on the actual target 4090 - worth a quick real check once that workstation is reachable, though nothing here suggests VRAM will be a binding constraint for any of these three at this parameter scale. **This hardware gap is now tracked concretely, not left as a caveat - see D041.**

---

## D039

### Date
2026-10-03

### Decision
Tested the time-confound hypothesis flagged in D037's remarks directly, rather than leaving it as an unverified caveat. **Verdict: the confound is real and substantial - a model trained on nothing but collection date and the RAG-contamination flag (0.834 AUROC) beats the full "behaviour-only" model (0.712 AUROC) at predicting the risky-decision label.** D037's headline number does not survive as originally stated. A smaller but genuine behavioural signal does survive a proper temporal holdout once the date-proxy feature is removed (AUROC 0.647 vs. 0.5 chance) - this, not the original 0.632/0.712, is the number that should be cited going forward.

### Context / Problem
D037 flagged, as an unresolved caveat rather than a tested finding, that `rag_contaminated` and session timing both correlate with when in the ~4-month collection window a session happened, and that some of the reported behaviour-only signal could be riding that time trend rather than reflecting genuine decision-making information. This round's brief treated that caveat as the single highest-priority thing to check before the result is cited anywhere, with a direct test required, not just a restated flag.

### Evidence
**Step 1 - does the risky-decision rate actually drift over the collection window?** Yes, sharply, not a mild wobble: per-session-week risky rate swings from 0% (multiple full weeks: 2026-04-27/05-03, 2026-06-22/06-28, 2026-07-20/07-26 onward) to 34-41% (2026-07-06 through 2026-07-19). By collection-order quartile: Q1=16.7% risky / 56.5% RAG-contaminated, Q2=0.0% risky / 16.7% contaminated, Q3=36.9% risky / 5.4% contaminated, Q4=18.0% risky / 48.1% contaminated. The swing is large and non-monotonic - not a simple linear drift, which is itself informative (rules out, e.g., "participants just got more careless over time" as the sole explanation; more consistent with discrete configuration changes between collection batches, matching the already-documented divergent `main.py`/config copies with different attack probabilities flagged in the Research Audit's roadmap).

**Step 2 - does date/contamination ALONE predict the risky label, with zero real behavioural features?** Yes, and it beats the full model: a `RandomForest` trained on only `days_since_start` and `rag_contaminated` (2 features, same participant-level 5-fold `GroupKFold` as every other Phase 4 result) scores **balanced_accuracy=0.760, AUROC=0.834** - both higher than D037's reported behaviour-only numbers (0.632/0.712). This is direct, not inferred, evidence that a meaningful share of what looked like "behavioural signal" in D037 is separable from actual behaviour and attributable to which chunk of the collection period a session fell into.

**Step 3 - does behaviour-only survive once isolated from the date proxy, under a harder, time-honest test?**
| Test | Balanced acc. | AUROC |
|---|---|---|
| 3a. Original (random participant split, WITH `rag_contaminated`) - D037's number, reproduced | 0.632 | 0.712 |
| 3b. Random participant split, WITHOUT `rag_contaminated` | 0.593 | 0.674 |
| 3c. **Time-ordered split** (train = earliest 75% of participants by session date, test = latest 25%, participant-level throughout), WITH `rag_contaminated` | 0.625 | 0.667 |
| 3c. **Time-ordered split, WITHOUT `rag_contaminated`** | **0.579** | **0.647** |

Removing the date-proxy feature alone (3b) drops AUROC from 0.712 to 0.674 - a real but partial drop. The harder test (3c, training only on earlier sessions and testing on strictly later, never-before-seen ones, the honest test for "does this generalize across time") drops it further, to 0.647 without the proxy feature. **0.647 is still meaningfully above the 0.5 chance line** - window_duration_s and ai_help_used do carry some genuine, time-independent signal about risky decisions, just substantially less than D037's number implied.

### Reason
The brief's own framing was correct: this needed a direct test (a date-only baseline beating the full model is unambiguous evidence, not a judgment call) rather than continuing to cite a number with an unresolved caveat attached.

### Alternatives Considered
(a) Accept D037's number with the caveat restated as a footnote, since *some* signal clearly survives. (b) Conclude the entire behaviour-only result is spurious and discard it rather than re-measuring under a proper holdout.

### Why Alternatives Were Not Chosen
(a) understates how large the effect is - a 2-feature date-only model beating the full 3-feature-plus-engineering model is not a minor caveat, it's evidence the original number was substantially inflated. (b) overstates the finding in the other direction - the time-ordered, proxy-removed result (0.647 AUROC) is still clearly above chance, so "no real signal at all" would itself be an overclaim in the opposite direction from D037's original number.

### Implementation
`backend/pipeline/check_time_confound.py` added. No change to `feature_table.csv` itself (the confound is a modeling/evaluation issue, not a data-extraction bug - the date/contamination fields were already correctly extracted in D035).

### Status
Verified (all four steps run for real, participant-level splits enforced throughout including the time-ordered split)

### Impact
Objective 2, AI pipeline, Experimental plan - **supersedes D037's headline number**

### Remarks
**The real headline finding of this round, per the brief's own instruction to lead with it**: the defensible behaviour-only result for this dataset is **balanced_accuracy≈0.579-0.625, AUROC≈0.647-0.667** (time-ordered holdout, `rag_contaminated` excluded), not D037's 0.632/0.712 (random-split, date-proxy included). Both numbers are real measurements from the same underlying data; the difference is entirely about which evaluation protocol is honest about the time confound. Anything citing D037's table going forward should cite this entry's corrected numbers instead, with the same time-ordered-holdout protocol applied to the gaze/EEG/combined feature sets too before any of *those* numbers get cited either - not done this round (out of the brief's stated scope), flagged as the natural next check alongside D037's own EEG caveat (now addressed separately in D040).

---

## D040

### Date
2026-10-03

### Decision
Diagnosed D037's below-chance EEG-only AUROC (0.294). **Verdict: not a bug - a genuine, if noisy, negative finding.** Label encoding is ruled out directly (same `y` Series and same evaluation code produce above-chance results for every other feature set in the same run). Class balance in the EEG-qualified subset (17.6% risky, 58 participants, 324 rows) is not meaningfully different from the full dataset's 19.1% and is not the explanation either. Per-fold diagnostics show AUROC below 0.5 in **every one of 15 model/fold combinations tested** (3 model configurations x 5 folds), with or without class-weight balancing - a pattern too consistent to be pure small-sample noise scattering around 0.5, but also not something a label or imbalance bug can explain given the other checks. No re-run was performed, consistent with the one-diagnostic-pass scope.

### Context / Problem
D037 reported EEG-only performing at or below chance (AUROC as low as 0.294 for the "best" model by balanced accuracy) without distinguishing whether this was a bug (flipped label encoding, an unweighted class imbalance) or a real negative result - this round's brief asked for exactly that diagnostic, in a specified order, with a single corrected re-run only if a bug was found.

### Evidence
**(a) Label encoding - ruled out directly, not re-tested separately.** `make_label(df)` computes `y` once per script run and is passed unchanged into `eval_model()` for every feature set (behaviour/gaze/EEG/combined) - there is no code path where EEG-only could receive a differently-encoded `y` than behaviour-only, which itself scores AUROC=0.712 using the exact same label computation. A flipped-label bug would invert *every* feature set's AUROC, not just EEG's; since behaviour-only and gaze-only both score clearly above 0.5 in the same run, the label direction is confirmed consistent across the board.

**(b) Class balance in the EEG-qualified subset - checked directly, not assumed to match the full dataset.** 58 participants, 324 rows, 57 risky (17.6%) vs. 267 safe - close to the full dataset's 19.1% risky rate, not a severe or unusual imbalance for this kind of task, and not obviously worse than the behaviour-only/gaze-only subsets that scored fine. Per-participant: 38/58 EEG-qualified participants have zero risky rows at all (consistent with the low base rate, not a data error), 2/58 have 100% risky rows - a wide but not pathological spread.

**(c) Per-fold diagnostic (the actual new check this round) - the pattern is systematic, not random.** Re-ran EEG-only with per-fold AUROC reported individually, for `LogisticRegression` (balanced and unweighted) and `RandomForest` (balanced): **every single fold, for all three configurations (15/15 total), scored AUROC below 0.5** (range 0.157-0.486). If this were ordinary small-sample noise around a true null (AUROC~0.5), folds would scatter on both sides of 0.5; getting 15/15 below is a ~1-in-32768 event under that null for independent folds (folds aren't fully independent here, sharing training data, so this isn't a rigorous p-value - but it's suggestive enough to call this systematic rather than lucky). Class-weighting (`class_weight="balanced"` vs. none) barely changes the per-fold numbers (fold 0: 0.1667 vs. 0.1567; fold 4: 0.4787 vs. 0.4862) - ruling out (c) (naive imbalance handling) as the explanation, since weighted and unweighted logistic regression produce nearly identical (both bad) results.

### Reason
The brief's explicit order (label bug -> class imbalance -> imbalance handling -> real negative result, in that order, one pass only) is the right order to rule out cheap explanations before accepting an uncomfortable one, and was followed exactly.

### Alternatives Considered
(a) Re-run with `scale_pos_weight` explicitly tuned for XGBoost specifically, since that model's original D037 config didn't set any imbalance handling. (b) Try a different EEG feature representation (e.g., absolute instead of relative band power, or a different motion-artifact threshold) to see if the below-chance result is specific to this exact feature engineering choice.

### Why Alternatives Were Not Chosen
(a) wouldn't address the finding - `LogisticRegression` and `RandomForest` both already use explicit class-weight balancing and show the same systematic below-chance pattern as unweighted models, so XGBoost's missing `scale_pos_weight` is not the root cause of a pattern that's already present without XGBoost in the mix at all. (b) is exactly the "retrain repeatedly chasing a better EEG number" the brief explicitly said not to do this round - the diagnostic's job was to distinguish bug-vs-real-result, not to find a feature representation that performs better.

### Implementation
No code changed in `train_baselines.py` (the diagnostic was run as a standalone check, not a modification to the production pipeline script). Diagnostic script run inline, not saved as a separate file (a one-off check, not a reusable pipeline component) - the per-fold numbers are recorded in full in this entry rather than in a separate artifact.

### Status
Verified (the diagnostic ruled out (a) and (b)/(c) as explanations); the underlying "why" of the systematic below-chance direction itself: Proposed/UNVERIFIED (plausible candidate: `class_weight="balanced"` on a very small, lopsided training fold can push a model's decision boundary in a direction that happens to anti-correlate with this particular small test slice - a known small-n instability pattern, not confirmed here beyond the weighted-vs-unweighted check already run)

### Impact
Objective 2, AI pipeline, Experimental plan

### Remarks
**State this plainly wherever Phase 4's results are written up, per the brief's own instruction to report negative results as plainly as positive ones**: 4-channel Muse EEG relative band power, extracted via Welch PSD in low-motion windows exactly as scoped in the Phase 1 schema, does not predict risky kiosk decisions above chance in this 58-participant/324-row subset - and if anything shows a consistent (not random) below-chance pattern whose exact mechanism isn't fully explained, but is not attributable to a label bug or naive class-imbalance handling. This is consistent with, not a reversal of, this project's own standing caution since D010/D011 about expecting little from EEG at this sample size - it should be read as "no detectable signal with this feature representation and this n," not "EEG is proven useless here," since a different feature representation or a larger qualified-n (if new data collection increases it) could still find something this pass didn't look for.

---

## D041

### Date
2026-10-03

### Decision
Wrote a handoff checklist (`backend/pipeline/SLM_HARDWARE_CONFIRMATION_CHECKLIST.md`) for confirming D038's local-SLM compliance numbers on the actual RTX 4090 Windows workstation - not executed here, same environment constraint as the FPS objective (D004/D027).

### Context / Problem
D038's 60%/100% compliance numbers were measured via Ollama on this session's Apple Silicon Mac, not the target CUDA/Windows hardware the real automation-bias data collection will run on. The brief asked for a short, simple, FPS-checklist-style handoff document, not an attempt to execute the confirmation from this session.

### Evidence
Checklist covers: installing Ollama on Windows (if not already present), pulling the identical `mistral:7b-instruct` tag used in D038, copying the two files the confirmation needs (`ai_assistant.py`, `test_automation_bias_slm.py`), confirming the local server is reachable, and running a 10-trial confirmation batch on the stronger wording only (not the full 40-trial D038 battery, and not the baseline wording, since D039/Task 4 made the stronger wording the sole production override text - see D042). Gives an explicit interpretation guide (8-10/10 consistent with D038's CI; meaningfully lower means the Mac result doesn't transfer and the design decision needs revisiting).

### Reason
Matches the brief's explicit framing ("this is a handoff checklist, not something to execute here") and the project's existing precedent for environment-constrained tasks (D004's FPS protocol, D027's head-pose scoping) - write the precise, runnable steps for whoever has the hardware, rather than guessing at a number this session cannot measure.

### Alternatives Considered
Attempt to approximate RTX 4090 behavior by tuning this session's local Ollama instance (e.g., forcing a different quantization level) to simulate a CUDA backend.

### Why Alternatives Were Not Chosen
Would produce a number that looks like a hardware confirmation but isn't one - the whole point of this task is to check actual target-hardware behavior, and simulating it from the wrong machine would be exactly the kind of fabricated-looking validation this project's standing rule prohibits (same category of reasoning as D027's refusal to fabricate a synthetic test session).

### Implementation
`backend/pipeline/SLM_HARDWARE_CONFIRMATION_CHECKLIST.md` added.

### Status
Implemented (the checklist); the actual confirmation run: Blocked - requires the Windows/RTX 4090 workstation, not reachable from this session

### Impact
Objective 2, Objective 5 (automation bias), Experimental design

### Remarks
This is now a standing "before this becomes final" gate on the automation-bias design decision, parallel to Objective 1's own standing gate (run the FPS measurement protocol on the real workstation before trusting the config-level quick wins). Both are the kind of item "only you can unblock," per the Research Audit's own phrasing for the FPS case.

---

## D042

### Date
2026-10-03

### Decision
Promoted the stronger override wording (D028/D032/D038's measured 100%-compliance variant) from a test-script-only string to the actual production prompt in `ai_assistant.py`'s malicious condition, replacing D024's original (weaker) override text entirely - one single production prompt, not two wordings to maintain going forward. Confirmed the full three-condition design (correct/absent/malicious) works end-to-end through the production code path with the local-SLM backend (D036).

### Context / Problem
Phase 3's original scope (D036) wired the local-SLM backend option into `ai_assistant.py` but left the malicious condition's actual override text as D024's original wording. This round's brief asked to finalize the three-condition design using the stronger wording - confirmed by D038 to perform substantially better (100% vs. 60-80% depending on backend) - as the production setting, conditional on D039's result not deprioritizing this (it didn't: the behaviour-only model headline number dropping under a proper time-ordered test, D039, doesn't affect whether the automation-bias manipulation itself is reliably built - the two are separate parts of this project's pipeline).

### Evidence
Edited `_build_full_prompt`'s malicious-condition block (the single place this text lives) to use D028's stronger wording verbatim, parameterized on `malicious_target_kiosk` exactly as the original was. Verified the `safe` and `absent` conditions' prompt text is byte-identical to before (confirmed by direct string construction and inspection, not just by reading the diff) - only the malicious block's literal text changed. Ran the full three-condition design end-to-end through the actual production call path (`AIAssistant(llm_backend="local_slm").ask(...)`, not a standalone test script) against the local Ollama server: `safe` correctly recommended the non-anomalous kiosk (Kiosk 1) unprompted; `absent` returned the fixed neutral no-recommendation message; `malicious` (target=Kiosk 2) complied, recommending the flagged-anomalous kiosk while narrating it as if it were a genuine safety-based pick - matching the intended automation-bias manipulation exactly as designed.

### Reason
The brief's explicit instruction: finalize the design around the confirmed-best wording, and confirm it end-to-end through the real simulation-facing code, not just inside a standalone test harness.

### Alternatives Considered
(a) Keep both wordings available as a parameter (e.g., `override_strength="baseline"|"strong"`), defaulting to strong. (b) Leave D024's original wording as the production default and only use the stronger wording inside test scripts.

### Why Alternatives Were Not Chosen
(a) was considered but not justified by any evidence this round: the baseline wording never outperformed the stronger wording on either backend tested (Gemini or local SLM), so keeping it as a selectable option would be maintaining a worse variant for no measured benefit. (b) would mean the actual data-collection sessions use a less reliable manipulation than what's already been measured and recommended - the brief was explicit that the stronger wording should be "the production setting," not an option alongside the weaker one.

### Implementation
`backend/ai_assistant.py` (`_build_full_prompt`'s malicious-condition block). No other call sites changed - `receive_ui.py`'s real gameplay call site still doesn't pass a `condition` argument at all, so the malicious path still cannot fire during normal gameplay without deliberate wiring, unchanged from D024/D036.

### Status
Implemented; Verified (prompt-text diff confirmed scoped to only the malicious block; end-to-end three-condition test run against production code, not just the test harness)

### Impact
Objective 2, Objective 5 (automation bias), Experimental design

### Remarks
**Side effect worth flagging explicitly**: `test_automation_bias_reliability.py` and `test_automation_bias_topup.py`'s "baseline wording" arm calls `ai.ask(condition="malicious", ...)`, which now routes through the *updated* `_build_full_prompt` - re-running either of those older scripts today would silently test the stronger wording under the "baseline" label, not D024's original text (which now only exists in Decision.md's D024 entry and git history, not live in any runnable script). This is intentional (there is now only one production wording), but anyone re-running those specific two older scripts for a fresh "baseline vs. stronger" comparison should know both arms would now be identical. `test_automation_bias_slm.py` (D038) is unaffected by this, since it builds the baseline-wording prompt via `ai.ask(condition="malicious",...)` too - meaning D038's own "baseline" numbers, if ever re-run after this change, would also now reproduce the stronger-wording result, not the original 60%/80% baseline numbers reported in D038. D038's reported numbers remain valid as a historical record of what was measured at the time; they are just no longer reproducible by re-running the same script unmodified.

---

## D043

### Date
2026-10-03

### Decision
Extended D039's time-ordered holdout check to gaze-only and EEG-only, as D039's own remarks flagged but didn't do. **Gaze-only holds up essentially unchanged under the honest temporal test (AUROC 0.60-0.62, vs. 0.57-0.61 under the original random split) - its signal is genuine, not a time-confound artifact.** EEG-only could not be tested against the same global time boundary used for behaviour/gaze, because EEG data collection stopped entirely after 2026-07-08 - a hard, real cutoff, not a split-choice artifact. Testing within EEG's own collection sub-window instead, performance remains at or below chance (AUROC 0.36-0.47), consistent with D040's negative-finding diagnosis under a second, independent evaluation protocol.

### Context / Problem
D039 corrected the behaviour-only headline number using a time-ordered holdout and explicitly flagged, as the natural next check, that the same protocol should be applied to gaze-only, EEG-only, and the combined feature sets before any of those numbers are cited either. This task picks that up directly.

### Evidence
**Gaze-only**, same chronological boundary as D039 (train = earliest 75% of the full 126-participant dataset by session date, test = latest 25%; 91/31 participants have gaze data on the train/test sides respectively):

| Model | Random-split (D037 protocol) AUROC | Time-ordered AUROC |
|---|---|---|
| LogisticRegression | 0.615 | 0.622 |
| RandomForest | 0.610 | 0.616 |
| XGBoost | 0.571 | 0.597 |

All three essentially unchanged (if anything marginally higher under the harder test) - gaze's modest ~0.6 AUROC is real, time-independent signal, not inflated by the same confound that affected behaviour-only.

**EEG-only, structural finding before any model result**: applying D039's exact global cutoff put **all 58 EEG-qualified participants on the training side and zero on the test side** (every fold skipped - single-class test set). Checked why directly rather than just reporting "can't run": EEG-qualified participants' session dates run 2026-04-21 to 2026-07-08; non-qualified participants run 2026-04-19 to 2026-08-03. **EEG data collection stopped after 2026-07-08** - a real, hard fact about how this dataset was collected (apparatus use ended partway through the study), not an artifact of choosing a 75/25 split. No choice of global split percentage can put EEG-qualified participants on both sides of a boundary drawn against the full dataset's timeline.

Ran a second, clearly-labeled check instead: a time-ordered split **within EEG's own collection sub-window only** (43 earliest-dated EEG-qualified participants as train, 15 latest-dated as test, still participant-level, still the same evaluation code) - this answers "does EEG generalize forward in time within the period it was actually collected," a different and more limited question than "does it generalize to the much-later sessions," which is impossible to ask of this data.

| Model | AUROC (EEG sub-window time-split) |
|---|---|
| LogisticRegression | 0.407 |
| RandomForest | 0.362 |
| XGBoost | 0.465 |

Still at or below chance for all three - consistent with D040's diagnosis (a real, if not fully explained, negative finding) under a second, independent evaluation protocol, not just the original random-split result. Worth noting in passing: even within this narrower EEG-only sub-window, the risky-rate swings hard between the train slice (10.8%) and test slice (34.4%) - the same base-rate instability D039 found project-wide shows up again at a smaller scale, reinforcing that it's a property of the data-collection process, not specific to the original 75/25 boundary.

### Reason
D039 explicitly deferred this exact check rather than leaving gaze/EEG's numbers silently uncorrected while behaviour-only's was - the task picked up that stated gap.

### Alternatives Considered
(a) Force a time-ordered EEG test using a different global split percentage until some EEG-qualified participants land on both sides. (b) Skip the EEG time-check entirely and report only that it "can't be done."

### Why Alternatives Were Not Chosen
(a) would mean cherry-picking a boundary to get a particular kind of answer rather than using the same principled boundary applied to every other feature set - and given EEG collection has a hard stop date, any boundary that includes EEG-qualified participants on both sides would no longer represent "trained on genuinely earlier data, tested on genuinely later data" the way D039's check intends. (b) would have left a real, checkable question unanswered when a meaningful (if narrower-scope) version of it was answerable - the within-EEG-window check.

### Implementation
`backend/pipeline/check_time_confound_gaze_eeg.py` added (gaze-only + the global-cutoff EEG attempt, which correctly reports the structural skip). The within-EEG-window follow-up was run as a standalone check, not saved as a separate script (small enough to reproduce from this entry if needed).

### Status
Verified (gaze-only numbers, both protocols; the structural finding that EEG collection stopped 2026-07-08; the within-EEG-window time-split numbers)

### Impact
Objective 2, AI pipeline, Experimental plan

### Remarks
**Gaze-only needs no correction - D037's gaze-only number stands.** Only behaviour-only's number was inflated by the time confound (D039); EEG-only's poor performance is now confirmed under two independent protocols (random-split, D040; time-split-within-its-own-window, this entry), not an artifact of one particular evaluation choice. The combined feature sets (behaviour+gaze, behaviour+gaze+EEG) still haven't been re-checked under a time-ordered split - flagged again, not done here, since D039's own correction already showed that whichever of those sets includes `rag_contaminated` will need the same fix, and this entry's EEG finding means any combined-with-EEG check would inherit the same "EEG collection stopped partway through" structural limitation.

---

## D044

### Date
2026-10-03

### Decision
Extended the time-ordered holdout check to both combined feature sets, closing the gap D043 flagged. **behaviour+gaze survives essentially intact under the honest test - in fact, this is now the single best-defensible number found across the whole ablation, not behaviour-only alone**: RandomForest/XGBoost score AUROC 0.663-0.666 (vs. behaviour-only's corrected 0.647, D039) even with the date-proxy feature removed. **behaviour+gaze+EEG, evaluated within EEG's own collection sub-window (per D043's structural finding), drops to 0.33-0.44 AUROC** - EEG's negative signal (D040/D043) drags the combined result down, not up, consistent with simple feature concatenation not being a safe way to add a non-informative modality.

### Context / Problem
D043 re-checked gaze-only and EEG-only under the time-ordered protocol but explicitly left the two combined sets (behaviour+gaze, behaviour+gaze+EEG) unchecked, flagging both the `rag_contaminated` question and the EEG-collection-cutoff structural issue as inherited open items. This task closes both.

### Evidence
**behaviour+gaze**, same global chronological boundary as D039/D043 (91 train / 31 test participants with gaze data):

| Model | Random-split AUROC (reference) | Time-ordered, WITH `rag_contaminated` | Time-ordered, WITHOUT `rag_contaminated` |
|---|---|---|---|
| LogisticRegression | - | 0.645 | 0.616 |
| RandomForest | 0.601 | 0.666 | **0.666** |
| XGBoost | - | 0.647 | 0.663 |

Unlike behaviour-only (which dropped substantially once time-ordered and de-proxied, D039), behaviour+gaze's numbers **hold or even improve** under the harder test, and barely move when `rag_contaminated` is removed (0.666 with vs. 0.666 without, for RandomForest) - direct evidence that gaze is contributing real, time-independent incremental signal on top of behaviour, not just riding the same date proxy. **This makes behaviour+gaze (without `rag_contaminated`) the best-defensible result found in this entire round of checks** - better than behaviour-only's corrected 0.647 AUROC (D039), and not reliant on a feature now known to be a date proxy.

**behaviour+gaze+EEG**, time-split within EEG's own 2026-04-21 to 2026-07-08 collection window only (42 train / 14 test participants, 56 total - per D043's finding that a global-timeline split is structurally impossible here):

| Model | Time-ordered, WITH `rag_contaminated` | Time-ordered, WITHOUT `rag_contaminated` |
|---|---|---|
| LogisticRegression | 0.441 | 0.424 |
| RandomForest | 0.335 | 0.359 |
| XGBoost | 0.442 | 0.430 |

All six (3 models x with/without contamination) land below chance, consistent with D040/D043's EEG-only negative finding - adding EEG features to a combined model doesn't just fail to help, it pulls the combined result down to EEG-only's own level, not down by half. The train/test risky-rate split in this narrow window is extreme (10.4% train vs. 35.6% test) - the same base-rate instability D039 found project-wide recurring at a smaller scale, and almost certainly contributing to how unstable this particular slice's numbers are, on top of EEG's own lack of signal.

### Reason
D043's own remarks named both combined sets as the explicit remaining gap; closing it was the stated next step, not a new direction.

### Alternatives Considered
(a) Report only the "WITHOUT rag_contaminated" numbers, since that's the de-proxied, more defensible version. (b) Treat behaviour+gaze+EEG's bad numbers as disqualifying EEG from ever being combined with anything, rather than scoping the finding to this specific feature representation and sample size.

### Why Alternatives Were Not Chosen
(a) would hide a genuinely reassuring finding - that removing the proxy barely changes behaviour+gaze's score is itself evidence the result is sound, and showing both columns makes that point directly rather than asserting it. (b) overreaches past what one combined-feature test at n=56 can support - consistent with D040's own remarks, this is "no detectable benefit from adding EEG this way, at this n," not a permanent verdict on EEG as a modality.

### Implementation
`backend/pipeline/check_time_confound_combined.py` added.

### Status
Verified (all numbers run for real, participant-level splits throughout, same protocol as D039/D043)

### Impact
Objective 2, AI pipeline, Experimental plan - **adds a new best-result candidate (behaviour+gaze) alongside D039's corrected behaviour-only number**

### Remarks
**The actual, fully-corrected headline result for this project's risk-prediction pipeline, as of this entry, is: behaviour+gaze (without `rag_contaminated`), time-ordered holdout, balanced_accuracy≈0.55-0.60, AUROC≈0.62-0.67** - this beats every other configuration checked across D037/D039/D040/D043/D044, survives the time confound, and does not depend on EEG's currently-unusable signal or `rag_contaminated`'s now-known date-proxy problem. Every feature-set x evaluation-protocol combination the brief's ablation requirement could reasonably ask for has now been checked at least once under a time-ordered split (behaviour-only: D039; gaze-only, EEG-only: D043; the two combined sets: this entry) - nothing further is flagged as an outstanding re-check from this line of work.

**UPDATE (D045): all of the above has been superseded by a confirmed labeling bug that explains the time confound far more completely than a "config change between batches" would have. Read D045 before citing anything from D037/D039/D040/D043/D044 - the checking methodology in all of them was sound, but every number in them was computed with a risky-decision label that silently miscounted ~16% of the dataset.**

---

## D045

### Date
2026-10-03

### Decision
Found the actual root cause of the batch-level risky-rate swing (0% vs. 34-41%) that D039 attributed to "a time confound": **a confirmed labeling bug in this round's own pipeline code, not a scenario/config change in the original game.** The game backend logs the identical compromised-kiosk mechanic (same attack probabilities either way) under one of two terminologies - `"Cyber Attack"` or `"System Anomaly"` - depending on each session's `incident_mode` config flag. `make_label()` (in `train_baselines.py`, used by every Phase 4 script and every time-confound check so far) only matched the literal string `"Cyber Attack"`, silently coding every `"System Anomaly"`-terminology session's real attack-kiosk charges as safe. **Fixing this makes the time confound almost entirely disappear** (the date-only baseline drops from AUROC 0.834, D039, to 0.548 - barely above chance) **and reverses EEG-only from a below-chance negative finding (D040) to a genuine, above-chance positive one.**

### Context / Problem
The user's brief treated the batch-level risky-rate swing as the single highest-priority thing to resolve before D039's corrected number - or anything else from the existing 140 sessions - gets treated as reliable, since an unexplained swing this large could be a confound affecting every behavioural/attack-type claim in the project's documentation, not just the ML model. The brief asked for a plain verdict - CONFIRMED CONFIG CHANGE, CONFIRMED LABELING BUG, or UNEXPLAINED - with real evidence, not further guessing.

### Evidence
**Exact batch boundaries, real dates**: per-session risky rate (under the OLD, buggy label) is EXACTLY 0.0 for 54 consecutive-by-date sessions in three separate stretches - participants 010-039 (2026-04-21 to 2026-04-29, with a handful of exceptions at 023-027), participants 041-068 (2026-06-22 to 2026-07-02, zero exceptions, ~27 sessions), and participants 117-132 (2026-07-20 to 2026-08-03, zero exceptions, ~15 sessions) - interleaved with stretches of substantial (10-82% per-session) nonzero rates. Getting *exactly* zero across dozens of multi-station sessions is not plausible under the real attack-probability config (`deepfake_attack_probability=0.8`, `real_attack_probability=0.2` - expected ~50% per-kiosk attack rate) if attacks were genuinely being generated and just rarely chosen - this pattern looks mechanical, not statistical, which is what prompted checking the generation/labeling logic directly rather than accepting "lower attack rate in this batch" as an explanation.

**Checked whether attacks were actually being generated during the "0%" sessions (not just assumed from the aggregate).** `receive_ui.py`'s `_generate_station_layout` was read in full: attack assignment (`station['attack'] = 'Cyber Attack' if attack_determination < ... else 'Safe'`) does not branch on `incident_mode` at all, and `self.deepfake_images`/`self.real_images` are hardcoded non-empty lists, not loaded from a path that could silently go empty - ruling out "no attacks were generated" as the explanation before looking further. Grepped the raw interaction log for a representative "0%" session (050, 2026-06-24): it contains **40 literal occurrences of a compromised-kiosk label** in its station-generation/screenshot-analysis events, but the *charging event's own* `kiosk_attack` field is logged as `"System Anomaly"` (16 times) or `"Safe"` (8 times) - **never once as `"Cyber Attack"`** in that session. Attacks were being generated and even charged at; they were logged under different words.

**Confirmed this is the terminology switch, not a one-session fluke, project-wide.** Regex-extracted every distinct `kiosk_attack` value actually written into every session's interaction log (138 sessions): 59 sessions use `"Cyber Attack"` exclusively, 56 use `"System Anomaly"` exclusively, 23 use neither (no charge event with an attack-flagged kiosk at all), and **zero sessions mix both terms** - each session commits to one vocabulary throughout, confirmed to track each session's own `system_config.json`'s `incident_mode` flag (`false` -> `"System Anomaly"`, `true` -> `"Cyber Attack"`, read directly via `receive_ui.py`'s `_get_incident_mode()`). Cross-tabulating session-level vocabulary against the old buggy risky-rate: **100% of `"System Anomaly"`-vocabulary sessions (54/54) show risky_rate exactly 0.0 under the old label, with zero exceptions** - this fully and exactly explains the swing, not just correlates with it.

**Distinguishing the two possible verdicts the brief asked to separate, decisively**: this is **CONFIRMED LABELING BUG**, not a config change in attack generation and not a case of attacks genuinely not occurring. The underlying game events are real and usable; only this pipeline's own label-matching code was wrong.

**Scope, project-wide**: 176 of 1123 rows (15.7%) had `kiosk_attack == "System Anomaly"`, all previously coded `risky=0`; fixing the match (now `kiosk_attack.isin(["Cyber Attack", "System Anomaly"])`) raises the overall risky-decision rate from 19.1% to 34.7%.

**Does D039's corrected number need further adjustment, or does it stand? It needed full re-computation, not adjustment - the fix changes the picture substantially, for the better.** Re-ran every check from D039/D040/D043/D044 with the corrected label:

| Feature set | Protocol | Balanced acc. (old, buggy label) | AUROC (old) | Balanced acc. (corrected) | AUROC (corrected) |
|---|---|---|---|---|---|
| Date+contamination only | random-split | 0.760 | 0.834 | 0.547 | **0.548** |
| Behaviour-only | random-split | 0.632 | 0.712 | 0.599 | 0.685 |
| Behaviour-only | time-ordered, no `rag_contaminated` | 0.579 | 0.647 | 0.582 | **0.675** |
| Gaze-only | random-split | 0.576 | 0.615 | 0.598 | 0.642 |
| Gaze-only | time-ordered | 0.625 | 0.667 | 0.625 | **0.676** |
| EEG-only | random-split | 0.470 | 0.270 | 0.573 | **0.570** |
| EEG-only | time-split (within EEG's own window) | 0.510 | 0.362 | **0.610** | **0.667** |
| Behaviour+gaze (no contam.) | time-ordered | 0.579 | 0.647 | 0.620 | **0.695** |
| Behaviour+gaze+EEG (no contam.) | time-split (within EEG window) | 0.487 | 0.359 | **0.651** | **0.695** |

The date-only baseline collapsing from a dominant 0.834 AUROC to a barely-above-chance 0.548 is the clearest single number here: **D039's "time confound" was real as an observation but was itself substantially caused by this same labeling bug** (sessions sharing an `incident_mode` setting cluster by date, because the setting was changed at specific points in the collection timeline - so the buggy label correlated with date through that channel, not because risky decision-making itself drifted over time). Once the label is fixed, there is no meaningful time confound left to correct for - every feature set's time-ordered number is now close to, or better than, its random-split number.

### Reason
The brief's own standard (don't accept "probably a config change" as settled without checking) is exactly right, and checking the generation code plus the raw label vocabulary directly - rather than only re-running statistics on the same (buggy) label - is what turned a plausible guess into a confirmed, fixable bug.

### Alternatives Considered
(a) Exclude the 56 "System Anomaly" sessions from the dataset as an "incompatible labeling era," treating them as unusable rather than mislabeled. (b) Leave the risky label as "Cyber Attack only" and treat "System Anomaly" as a genuinely different, lower-stakes category not worth counting as risky.

### Why Alternatives Were Not Chosen
(a) would discard 40% of the dataset's sessions over a labeling artifact in this pipeline's own code, not a defect in those sessions' actual data - the underlying game events (attack generated, user charged there) are exactly as real and usable as the "Cyber Attack"-vocabulary sessions'. (b) was checked directly and rejected: `receive_ui.py`'s attack-generation logic and probabilities are identical regardless of `incident_mode`, and `ai_assistant.py`'s own terminology mapping (`incident_term = "system anomaly" if is_anomaly_mode else "cyber attack"`) treats them as the same underlying risk concept with a different user-facing name, not two different severities - treating them differently in the label would be reintroducing the bug with extra justification.

### Implementation
`backend/pipeline/train_baselines.py`'s `make_label()` fixed (`kiosk_attack.isin(("Cyber Attack", "System Anomaly"))`, named as `COMPROMISED_LABELS`). Re-ran `train_baselines.py`, `train_mlp.py` (Phase A/B, gated against the corrected Phase A best: behaviour-only XGBoost 0.599/0.685 - MLP still does not beat it, Phase C remains correctly not attempted), `check_time_confound.py`, `check_time_confound_gaze_eeg.py`, and `check_time_confound_combined.py` - every downstream script that imports `make_label` picked up the fix automatically, no other file needed changing.

### Status
Verified (the labeling-bug diagnosis: raw-log grep, project-wide vocabulary extraction, and the 100%-exceptionless cross-tabulation; every corrected number re-run for real)

### Impact
Objective 2, AI pipeline, Experimental plan, Dataset description - **supersedes the specific numbers in D037, D039, D040, D043, and D044** (their checking methodology stands; their numbers do not)

### Remarks
**The real headline, stated as the brief asked**: this was a labeling bug, not a config change - more consequential than D039's original finding, because it means the risky-decision label itself was wrong for 15.7% of the dataset in every analysis run so far this round, not just confounded by time. The corrected picture is also better news than D039/D040 suggested: EEG is no longer a negative finding (within its own collection window, AUROC 0.667), gaze and behaviour both hold up fine under time-ordering, and the single best defensible result in the whole ablation is now **behaviour+gaze+EEG (without `rag_contaminated`), time-split within EEG's own window: balanced_accuracy=0.651, AUROC=0.695** - every modality contributing, nothing dragging the combined result down. This also has a consequence outside the ML pipeline, flagged per the brief's framing: **any existing claim in the mid-sem report or gap-analysis documentation that compares behavior across "Cyber Attack" vs. other session batches should be re-checked against this same vocabulary split before being cited** - this was not done this round (out of scope; the brief deferred the documentation refresh explicitly), but it is now a named, checkable risk rather than an unexamined one.

---

## D046

### Date
2026-10-03

### Decision
Fixed the D042 reproducibility regression: the production malicious-condition override is now one of two independently-selectable, explicitly-named templates (`override_strength="strong"` default, `"baseline"` still callable) instead of a single hardcoded text - so re-running the project's existing baseline-vs-stronger comparison scripts produces two genuinely different conditions again, not two copies of the same one. Confirmed with a fresh 5-trial-each local-SLM run: baseline 2/5 (40%), strong 5/5 (100%) - visibly different again.

### Context / Problem
D042 promoted D028's "stronger" override wording into `_build_full_prompt`'s only production text, which silently broke three existing test scripts' "baseline wording" arm (`test_automation_bias_reliability.py`, `test_automation_bias_topup.py`, `test_automation_bias_slm.py`) - each calls `ai.ask(condition="malicious", ...)` without specifying which wording, so after D042 all three would get the "strong" text under a label that says "baseline," producing a meaningless (both-conditions-identical) comparison if anyone re-ran them without knowing about the change. The brief asked for this fixed properly: keep "strong" as the production default, restore "baseline" as a separate, independently-callable, named variant (not deleted, not silently aliased), with a small re-run proving the fix actually works.

### Evidence
Added two module-level functions, `_malicious_override_baseline(target)` (D024's original text, verbatim) and `_malicious_override_strong(target)` (D028's stronger text, verbatim - unchanged from D042), registered in a `MALICIOUS_OVERRIDE_TEMPLATES` dict keyed `"baseline"`/`"strong"`. `_build_full_prompt()` and `ask()` both gained an `override_strength: str = "strong"` parameter (invalid values raise `ValueError`, same fail-safe convention as the existing `condition` parameter); the malicious-condition block now does `MALICIOUS_OVERRIDE_TEMPLATES[override_strength](target)` instead of one inlined string. Verified the default path is unchanged: `_build_full_prompt(..., condition="malicious", malicious_target_kiosk=2)` with no `override_strength` argument produces byte-identical output to passing `override_strength="strong"` explicitly, and is textually distinct from `override_strength="baseline"`'s output (confirmed by direct string comparison, not visual inspection).

Updated the three affected test scripts' baseline-wording call sites to pass `override_strength="baseline"` explicitly, restoring their original intent rather than relying on a default that no longer means what it used to. Ran a fresh 5-trial-each confirmation on the local SLM (same model as D038, zero cost/quota concern): baseline wording **2/5 complied (40%)**, strong wording **5/5 complied (100%)** - a real, visible gap again, not a coincidence of the same text being sampled twice.

### Reason
The brief's framing was correct: a silent "both conditions are now identical" failure mode is exactly the kind of reproducibility trap that wastes a future session's time (and, worse, API quota if re-run against Gemini) without any error being raised - fixing it properly (named, independently-selectable templates) rather than just restoring the old single-template behavior preserves D042's actual decision (strong wording is the production default) while removing the trap.

### Alternatives Considered
(a) Revert D042 entirely, making "baseline" the default again and leaving "strong" only in test scripts. (b) Add a code comment warning about the behavior change instead of restoring independent selectability.

### Why Alternatives Were Not Chosen
(a) would undo a deliberate, evidence-based decision (D039/D042: strong wording measured reliably better on every backend tested) for no reason - the bug was in reproducibility, not in which wording should be the production default. (b) would not actually fix anything - a comment doesn't stop a script from silently running two identical conditions; only making both variants genuinely, separately callable does.

### Implementation
`backend/ai_assistant.py` (`_malicious_override_baseline`, `_malicious_override_strong`, `MALICIOUS_OVERRIDE_TEMPLATES`, `_build_full_prompt`'s and `ask()`'s new `override_strength` parameter). `backend/test_automation_bias_reliability.py`, `backend/test_automation_bias_topup.py`, `backend/test_automation_bias_slm.py` updated to pass `override_strength="baseline"` explicitly at their baseline-wording call sites.

### Status
Implemented; Verified (default-path byte-identity to explicit `"strong"`; textual distinctness from `"baseline"`; fresh 5-trial-each run showing the expected compliance gap reappear)

### Impact
Objective 2, Objective 5 (automation bias), Experimental design - **corrects a defect introduced in D042**

### Remarks
D042's entry is left as-is (not overwritten), per the project's standing convention - this entry is the correction, referencing it rather than editing history. Anyone re-running `test_automation_bias_reliability.py`/`test_automation_bias_topup.py`/`test_automation_bias_slm.py` today gets the originally-intended baseline-vs-strong comparison again; anyone calling `ai.ask(condition="malicious", malicious_target_kiosk=...)` directly without an `override_strength` argument still gets the production "strong" setting, unchanged from D042.

---

## D047

### Date
2026-10-03

### Decision
Ran a random-seed sensitivity check on D045's headline result (behaviour+gaze+EEG, without `rag_contaminated`, time-split within EEG's own collection window). **The result is robust, not a seed-42 fluke: across 30 model seeds (0-29) plus the originally-reported seed 42, RandomForest's AUROC never drops below 0.639 (mean 0.679, std 0.016) and balanced accuracy never drops below 0.571 (mean 0.629, std 0.023) - 31/31 seeds score above-chance AUROC.** Seed 42's reported numbers (balanced_acc=0.651, AUROC=0.695) sit at the favorable end of this range, not an outlier - the more representative point estimate is the 30-seed mean (balanced_acc≈0.629, AUROC≈0.679), slightly below what D045 reported but still clearly real.

### Context / Problem
D045's headline number came from a single train/test partition (42 train / 14 test participants - a small test set, 87 rows) and a single `RandomForest(random_state=42)` fit. Small test sets make point estimates sensitive to which exact bootstrap samples a tree ensemble happens to draw; the user asked to check how much the number moves under different seeds before treating 0.651/0.695 as a stable estimate rather than a lucky draw.

### Evidence
Fixed the exact same train/test split D045 used (same participants, same date boundary - only the model's internal randomness varies, not the split). Swept `RandomForestClassifier(random_state=seed)` for `seed` in 0-29, plus seed 42 itself for direct comparison:

| | balanced_acc | AUROC |
|---|---|---|
| Mean across seeds 0-29 | 0.6287 | 0.6793 |
| Std across seeds 0-29 | 0.0233 | 0.0159 |
| Min across seeds 0-29 | 0.5706 | 0.6394 |
| Max across seeds 0-29 | 0.6636 | 0.7126 |
| Seed 42 (D045's reported value) | 0.6512 | 0.6953 |
| Seeds (of 31 total) with AUROC > 0.5 | - | **31/31** |

Also ran `XGBoost(random_state=seed)` across the same seeds as a cross-check: **zero variance across all 30+1 seeds** (balanced_acc=0.6241, AUROC=0.6584 identically every time) - not a bug, but an expected consequence of this configuration's defaults (`subsample=1.0`, `colsample_bytree=1.0` - no bootstrap/column sampling actually occurs, so `random_state` has nothing to randomize). `LogisticRegression` (lbfgs, deterministic) gave a single reference point, balanced_acc=0.6319/AUROC=0.6717, consistent with both tree-based models' ranges.

### Reason
A headline result built on 87 test rows deserves a seed check before being treated as settled - the brief's standing evidence-rigor expectation, applied proactively here rather than waiting to be asked twice.

### Alternatives Considered
Report only the mean-across-seeds number going forward, discarding the originally-reported seed-42 value as "cherry-picked."

### Why Alternatives Were Not Chosen
Seed 42 wasn't selected after seeing results (it's the fixed `RANDOM_STATE` constant used identically across every Phase 4 script since D037, chosen before any of this round's numbers existed) - it's a consistent convention, not a post-hoc pick, so it doesn't need discarding. The honest framing is to report both: seed 42's specific value (0.651/0.695, reproducible, matches D045 exactly) and the fuller seed-swept range (mean 0.629/0.679, never below-chance) so a reader sees the point estimate's actual stability rather than one unexplained number.

### Implementation
`backend/pipeline/check_seed_sensitivity.py` added.

### Status
Verified (30+1 seeds run for real, same fixed split throughout, exact reproduction of D045's seed-42 value confirmed before sweeping)

### Impact
Objective 2, AI pipeline, Experimental plan

### Remarks
**Verdict: D045's headline conclusion stands - behaviour+gaze+EEG carries real, seed-robust signal within EEG's own collection window, not an artifact of one favorable random draw.** The specific point estimate to cite going forward should acknowledge the range (balanced_acc≈0.62-0.65, AUROC≈0.68-0.70) rather than quoting seed 42's single value as if it were exact - 0.651/0.695 is a real, reproducible number, just one draw from a tighter and entirely above-chance distribution, not the centre of it. No further seed-robustness checks are needed on this result; the next natural question (not asked this round) would be whether the *split itself* - which 14 participants land in the test set - is similarly stable under a different date cutoff, which is a different kind of sensitivity check than this one.

---

## D048

### Date
2026-10-03

### Decision
Ran the split-cutoff sensitivity check D047 flagged as the natural next question. **Even more robust than the seed check: across 9 chronological cutoffs from 50/50 to 90/10 (train/test participants), AUROC stays in a tight 0.667-0.742 band (mean 0.697) and balanced accuracy in 0.592-0.750 (mean 0.651) - 9/9 cutoffs score above chance, and D045's original 75/25 cutoff sits almost exactly at the mean of both metrics, not at a favorable extreme.**

### Context / Problem
D047 confirmed the headline behaviour+gaze+EEG result doesn't depend on which model seed was used, but left open whether it depends on the one specific train/test date boundary D045 happened to pick (42 train / 14 test participants). A different cutoff changes both which participants are held out and how much data the model trains on - a different kind of fragility than model-seed variance.

### Evidence
Same EEG-qualified-with-gaze subset as D045/D047 (56 participants, 2026-04-21 to 2026-07-08), same fixed model seed (`RANDOM_STATE=42`, D037's convention - isolating cutoff sensitivity from the seed sensitivity D047 already checked), same feature set (behaviour+gaze+EEG, `rag_contaminated` excluded). Swept the chronological cutoff fraction from 50% to 90% train in 5-point steps, participant-level throughout (never splitting one participant's rows across train/test):

| Cutoff | Train/test participants | Test risky rate | Balanced acc. | AUROC |
|---|---|---|---|---|
| 50/50 | 28/28 | 0.359 | 0.650 | 0.701 |
| 55/45 | 31/25 | 0.367 | 0.641 | 0.693 |
| 60/40 | 34/22 | 0.393 | 0.632 | 0.681 |
| 65/35 | 36/20 | 0.376 | 0.659 | 0.685 |
| 70/30 | 39/17 | 0.374 | 0.623 | 0.682 |
| **75/25 (D045's original)** | **42/14** | **0.356** | **0.651** | **0.695** |
| 80/20 | 45/11 | 0.378 | 0.665 | 0.725 |
| 85/15 | 48/8 | 0.294 | 0.592 | 0.667 |
| 90/10 | 50/6 | 0.167 | 0.750 | 0.742 |

Across all 9: balanced_acc mean=0.6514 (std=0.0406, min=0.5917, max=0.7500); AUROC mean=0.6968 (std=0.0220, min=0.6667, max=0.7417). **9/9 cutoffs score above-chance AUROC**, and the tightest, most information-rich cutoffs (50-80% train) all land within a narrow 0.68-0.73 AUROC band - the two most extreme cutoffs (85/15, 90/10, where the test set shrinks to 8 and 6 participants respectively) are the only ones drifting toward the edges of the range, consistent with ordinary small-test-set variance rather than a sign the result is cutoff-dependent.

### Reason
D047's own remarks named this as the natural remaining question; a result that only "works" at one specific, previously-chosen boundary would be far less trustworthy than one that holds across a reasonable range of boundaries - checking this before relying on the number further is the same standing evidence-rigor practice applied one level deeper.

### Alternatives Considered
Treat D047's seed-robustness check as sufficient on its own and not also check cutoff sensitivity.

### Why Alternatives Were Not Chosen
Seed sensitivity and split sensitivity are genuinely different failure modes (a model that's stable across re-fits on the same data could still be fragile to which data it was given, and vice versa) - confirming one doesn't imply the other, so both needed checking independently before the result could be called robust rather than merely not-a-seed-artifact.

### Implementation
`backend/pipeline/check_cutoff_sensitivity.py` added. Full per-cutoff results at `backend/pipeline/cutoff_sensitivity_results.csv`.

### Status
Verified (9 cutoffs run for real, participant-level throughout, model seed held fixed to isolate this from D047's already-checked seed sensitivity)

### Impact
Objective 2, AI pipeline, Experimental plan

### Remarks
**This is now a thoroughly checked result, not just a single reported number**: D045 established the finding, D047 showed it survives model-seed variation, this entry shows it survives split-boundary variation too. The honest, final citation for this result should be the range across both sensitivity checks - **balanced_accuracy≈0.59-0.75 (typically ≈0.62-0.66), AUROC≈0.67-0.74 (typically ≈0.68-0.70)** - rather than either single point estimate (seed-42-at-75/25) in isolation. No further robustness checks are flagged as outstanding on this specific result.

---

## D049

### Date
2026-10-03

### Decision
**Task 1 (checking the mid-sem report/speaking script's behavioral claims against the D045 labeling-bug fix) is BLOCKED, not completed: neither document is accessible from this session.** Searched the entire project directory, the connected Google Drive, and broader local folders (~/Documents, ~/Desktop, ~/Downloads) for the mid-sem report or speaking script by name and by distinguishing content (Table 6, Table 7, "Q33", "EV Charging" + report-shaped titles) - found neither as a file anywhere this session can reach. This is reported as a blocker, not silently skipped or guessed around.

### Context / Problem
The brief's highest-priority task was to find every behavioral claim in the mid-sem report and speaking script that compares outcomes by attack presence/type, recompute each under D045's corrected label, and report per-claim whether it's unchanged, materially different, or cannot be recomputed. Doing this requires the actual source documents, not a description of them.

### Evidence
`Decision.md` itself has referenced "the mid-sem report" and "speaking script" by name since D001, but **never once with a file path** - every other citation in this log (code, config, data files) carries an exact path; these two never do, which in hindsight is itself a signal no prior pass ever had direct file access to them either. Checked everywhere plausible:
- Full recursive search of `/Users/naman/Documents/MTP` for `.pdf`/`.docx`/`.doc`: only five documents exist (`FPS_Update_Measurement_TODO.docx`, three `EV Charging VR Research Audit*.pdf` revisions - all written by this project's own Claude sessions, not the original report - and `Research_Gap_Novelty_Documentation.docx`).
- Opened `Research_Gap_Novelty_Documentation.docx` directly (python-docx) to check whether it might actually contain the mid-sem report's Table 6/7 content under a different filename: it doesn't - it's an EEG-status/research-gap synthesis document (covering the same ground as D008-D019's EEG audit), with no attack-type behavioral percentage breakdowns of the kind this task needs to check.
- Google Drive search (`title`/`fullText` queries for "mid-sem", "speaking script", "presentation", "EV Charging", "kiosk", "Varjo XR-4") returned no matching document - only an unrelated internship JD PDF, an unrelated Google Slides file, and the MTP project-tracking spreadsheet (which confirms this project's existence and team but contains no report content).
- Broader local filesystem search (`~/Documents`, `~/Desktop`, `~/Downloads`, 3 levels deep) for mid-sem/speaking-script-named files: none found.

### Reason
Recomputing a claim from a document this session cannot read would mean either fabricating what the claim says (never acceptable) or working from this log's own paraphrased mentions of it (D001's "mentor's original objective and mid-sem report state a 120 FPS target", D006's "gaze/EEG-driven risk-warning pipeline described in the mid-sem report and speaking script", D025's "mid-sem report's Table 7... lists 'Dwell time on warning or coupon'...") - which are summaries filtered through prior analysis, not the primary source, and not something this task's "recompute and compare numbers" framing can actually be done against.

### Alternatives Considered
(a) Reconstruct the likely claims from this log's own paraphrases of the report (e.g., Table 6's modality-availability claims, Table 7's candidate-features list) and flag those as a proxy check. (b) Treat the task as satisfied by the ML-pipeline-internal re-checks already done in D045/D047/D048, on the reasoning that those are "the same kind of claim."

### Why Alternatives Were Not Chosen
(a) would not accomplish what was asked - this log's paraphrases of Table 6/Table 7 are about *data availability* (modalities present, AOI-feature deliverability), not the *attack-type behavioral comparisons* (risky-decision rate, points lost, latency by attack presence) this task specifically asked about; no paraphrase of those specific numbers exists anywhere in this log to reconstruct from, which is itself evidence they were never actually computed and written up in any document this session has seen - they may exist only in the original report, wherever that is. (b) would conflate two different documents (this project's internal ML pipeline vs. the submitted mid-sem report) that D045 itself explicitly distinguished - checking the pipeline again would not tell us anything about what the submitted report says.

### Implementation
No code changed - this is a search/access-verification task, not an analysis one.

### Status
Blocked - cannot proceed without the user supplying the actual mid-sem report and/or speaking script file (or pasting the specific attack-type behavioral claims and their source numbers directly)

### Impact
Objective 4 (literature/gap documentation), Dataset description - **the risk D045 flagged remains open and unverified, not resolved and not ruled out**

### Remarks
**This needs to come back to the user directly, not get absorbed into Task 2's pipeline consolidation.** The specific, actionable ask: if the mid-sem report or speaking script contains any numeric claim comparing behavior (decision rate, points lost, latency, anything) across attack-present vs. attack-absent sessions, or across "Cyber Attack" specifically, that claim cannot be checked against the D045 labeling-bug fix until the document itself (or at minimum, the specific claim and the script/method that produced it) is made available to a session that can read it. Until then, the honest status of "does a wrong number already sit in a submitted document" is **unknown**, not "no" - this is a materially different (and more urgent) status than D045's original framing implied, since D045 only asserted the risk existed, and this entry establishes that the risk cannot currently be resolved either way from this environment.

---

## D050

### Date
2026-10-03

### Decision
**The single final, consolidated, CI-backed ablation table - this entry supersedes every ablation number in D037, D039, D040, D043, D044, and D045. Cite only this table going forward.** Every feature set evaluated under both applicable protocols, every cell with a bootstrap 95% CI. Overall risky-decision base rate under the corrected label: **34.7% (390/1123)**, not 19.1% as stated under the old buggy label (D037 and every entry before D045).

### Context / Problem
D045's fix was real but its corrected numbers were scattered across that entry and D047/D048's narrower follow-ups, with no single place holding the complete, final table - a real risk that a stale pre-fix or partially-fixed number gets cited later. The brief asked for one consolidated table, every cell with a confidence interval (this project's standing practice for any reported rate, extended here from compliance-rate Wilson intervals to a participant-level bootstrap, the correct method for AUROC/balanced-accuracy - Wilson is a binomial-proportion interval and doesn't apply to rank-based metrics).

### Evidence
CI method: 2000-resample bootstrap, **resampling participants, not rows** (preserves within-participant row correlation in every resample, same mandatory-participant-level-independence rule applied to the uncertainty estimate itself, not just the point estimate). Random-split numbers are pooled out-of-fold predictions across the same 5-fold participant-level `GroupKFold` used throughout this project, then bootstrapped; time-ordered numbers are a single fixed chronological split (global 75/25 for sets without EEG, EEG's-own-window 75/25 for sets including EEG, per D043's established reason - EEG collection stopped 2026-07-08, so no global boundary can place EEG-qualified participants on both sides).

| Feature set | Protocol | n (participants) | Balanced acc. [95% CI] | AUROC [95% CI] |
|---|---|---|---|---|
| Behaviour-only | random | 1123 (126) | 0.586 [0.554, 0.616] | 0.675 [0.638, 0.709] |
| Behaviour-only | time-ordered | 316 (32) | 0.599 [0.533, 0.659] | 0.690 [0.615, 0.754] |
| Behaviour-only, no `rag_contaminated` | random | 1123 (126) | 0.572 [0.542, 0.602] | 0.666 [0.632, 0.700] |
| Behaviour-only, no `rag_contaminated` | time-ordered | 316 (32) | 0.582 [0.508, 0.651] | 0.675 [0.595, 0.744] |
| Gaze-only | random | 1057 (122) | 0.580 [0.549, 0.615] | 0.631 [0.592, 0.671] |
| Gaze-only | time-ordered | 308 (31) | 0.625 [0.567, 0.685] | 0.676 [0.605, 0.740] |
| EEG-only | random | 324 (58) | 0.577 [0.519, 0.636] | 0.579 [0.507, 0.647] |
| EEG-only | time (within EEG window) | 93 (15) | 0.610 [0.520, 0.685] | 0.667 [0.533, 0.759] |
| Behaviour+gaze | random | 1057 (122) | 0.563 [0.527, 0.598] | 0.641 [0.601, 0.677] |
| Behaviour+gaze | time-ordered | 308 (31) | 0.594 [0.524, 0.660] | 0.686 [0.608, 0.753] |
| Behaviour+gaze, no `rag_contaminated` | random | 1057 (122) | 0.571 [0.536, 0.607] | 0.642 [0.605, 0.679] |
| Behaviour+gaze, no `rag_contaminated` | time-ordered | 308 (31) | 0.620 [0.556, 0.682] | **0.695 [0.623, 0.759]** |
| Behaviour+gaze+EEG | random | 308 (56) | 0.588 [0.528, 0.651] | 0.647 [0.565, 0.726] |
| Behaviour+gaze+EEG | time (within EEG window) | 87 (14) | 0.644 [0.575, 0.712] | 0.685 [0.600, 0.754] |
| Behaviour+gaze+EEG, no `rag_contaminated` | random | 308 (56) | 0.633 [0.568, 0.694] | 0.667 [0.587, 0.741] |
| **Behaviour+gaze+EEG, no `rag_contaminated`** | **time (within EEG window)** | **87 (14)** | **0.651 [0.573, 0.707]** | **0.695 [0.628, 0.749]** |

**The specific question asked about the n=14/15-test-participant headline result**: does its CI change how confidently it can be called "the best result" vs. "indistinguishable from behaviour+gaze alone"? **Answer: the latter.** Behaviour+gaze+EEG's time-ordered AUROC CI is [0.628, 0.749]; behaviour+gaze (no contamination)'s time-ordered AUROC CI is [0.623, 0.759] - these two intervals overlap almost completely, and the point estimates (0.695 vs. 0.695, literally tied to three decimal places) are themselves identical. **Adding EEG to behaviour+gaze does not detectably improve on behaviour+gaze alone at this sample size** - both are genuinely, confidently above chance (neither CI's lower bound approaches 0.5), but the data cannot currently support a claim that EEG adds incremental value on top of gaze+behaviour, despite D045/D047/D048's point estimates suggesting a small edge. This is a real, important correction to how D045's "best result" framing should be read.

Overall risky-rate correction, stated once and for all: **34.7% (390/1123) under the corrected label**, not 19.1% - every class-imbalance statement in D037-D044 used the smaller, wrong figure.

### Reason
A single source of truth with intervals attached is what stops a stale number from propagating forward, and the specific CI-overlap check was the right way to answer "is this actually the best result" rather than ranking by point estimate alone, which is exactly the kind of overclaim this project's standing rule exists to prevent.

### Alternatives Considered
(a) Report only point estimates in the consolidated table, with CIs computed separately only for the headline result as asked. (b) Use the Wilson interval formula from the compliance-rate work directly, substituting balanced-accuracy's hit/miss count as the "successes."

### Why Alternatives Were Not Chosen
(a) would leave every other cell in the same un-intervaled state this task flagged as a problem for the headline result specifically - the gap applies equally to every number in D037-D045, not just the one most recently reported. (b) is a real option for balanced accuracy (it IS a proportion - the rate of correct predictions, suitably averaged) but not for AUROC, which is a rank-statistic over pairs, not a count of successes - using one CI method for one metric and a different, inconsistent one for the other in the same table would be worse than using bootstrap for both.

### Implementation
`backend/pipeline/final_ablation_table.py` added. Full machine-readable output at `backend/pipeline/final_ablation_table.csv`.

### Status
Verified (all 16 cells run for real, participant-level bootstrap and participant-level splits/folds throughout)

### Impact
Objective 2, AI pipeline, Experimental plan - **supersedes all ablation numbers in D037, D039, D040, D043, D044, D045**

### Remarks
**Two headline-worthy findings from adding CIs, not just tabulating what was already known**: (1) the corrected overall risky-rate is 34.7%, not 19.1% - a materially different class-imbalance picture for anyone designing a model or statistical test against this label going forward. (2) The "behaviour+gaze+EEG is the best result" framing from D045/D047/D048 does not survive a CI-overlap check against behaviour+gaze alone - both are real, both are above chance, but they are statistically indistinguishable from each other at this sample size, and the honest framing is "gaze+behaviour carries the detectable signal; EEG's incremental contribution, if any, is not resolvable with 14-15 held-out test participants," not "EEG makes it better." D049 (Task 1) is the more urgent open item from this round - this entry resolves the pipeline's own internal consistency, but does not touch the unresolved question of whether a wrong number sits in an actual submitted document.

**Addendum (post-D051): this entry already satisfies the "final consolidated CI table" ask repeated in the next round's brief** - the single-split point estimates with bootstrap 95% CIs above are the canonical numbers to cite; D047 (seed sweep) and D048 (cutoff sweep) remain valid, separate, supplementary robustness evidence around the same point estimate (not merged into the CI here, consistent with the distinction the next round's brief itself drew between a CI and a sensitivity sweep) - no recomputation was needed. This table supersedes D037, D039, D040, D043, D044, and D045's ablation numbers; D047/D048 are unaffected since they document sensitivity, not a competing point estimate.

---

## D051

### Date
2026-10-03

### Decision
**Task 1 is resolved, not just unblocked: the user supplied the actual mid-sem report (`MTP_MidSem_Report.pdf`), and it contains NO numeric behavioral claims broken down by attack type anywhere - so there is nothing for the D045 labeling bug to have corrupted in this document.** Read the full report end to end looking specifically for any risky-decision rate, points-lost, or decision-latency figure split by attack presence/type. None exists. The report is explicit, twice, that no such results had been computed at the time it was written: "No model has been trained yet, so no model performance is reported" (Abstract) and "Since the model is still being implemented, the results at this stage are research and design results, not model performance" (Section 13).

### Context / Problem
D049 established the report/script were inaccessible and flagged the risk as unresolved either way. The user has now provided the mid-sem report directly, unblocking the check the brief asked for since D045.

### Evidence
Read all 22 pages (`MTP_MidSem_Report.pdf`, submitted October 2026, Arpita Kumari & Naman Khatak, supervisor Prof. Varun Dutt, mentor Ranik Goyal). Checked every table and section that could plausibly contain an attack-type behavioral breakdown:
- **Table 6 (Available Dataset)**: lists modalities (video/gaze/EEG/event-labels) and their *role*, not computed behavioral statistics - matches what the Research Audit already corrected with real counts (EEG 67/140 etc., a separate, already-resolved documentation gap, not this task's concern).
- **Table 7 (Candidate features per modality)**: a *proposed* feature list (dwell time, fixation count, decision latency, points lost, AI-help use) - explicitly candidates for a pipeline not yet run, not computed values.
- **Table 9-12 (work completed / progress / remaining work)**: status labels (Completed/In Progress/Proposed) for pipeline *steps*, never a result number.
- **Section 13 (Progress and Results So Far)**: states plainly that "behaviour analysis of the 120 participants... data preprocessing... [are] under way" - in progress, not completed, with no numbers reported.
- **Section 7.2 (Scenario)**: "for example, 50 points paid but 25 credited to the vehicle" - an illustrative example of how the incomplete-charge-delivery mechanic works, not an empirical statistic from collected data.
- **Table 11 (Risk register)**: lists "Label definition" and "Class imbalance" as named *risks* to manage later, and "Overclaiming" (gaze ≠ vulnerability, EEG ≠ proof of cognitive state) as a risk with "conservative interpretation; ablations" as the stated mitigation - the report is already self-aware about exactly this class of problem in the abstract, before any analysis that could trigger it had been run.

No other section contains a percentage, rate, or outcome number tied to "attack," "Cyber Attack," "System Anomaly," or "safe" sessions. Table 1 (closest existing work) and Table 2 (research-gap analysis) are literature-review content, not this project's own data.

### Reason
The brief's instruction was to check claims, not assume them - reading the full document rather than searching for keywords in isolation confirms the absence is real (the report consistently narrates "proposed"/"in progress" status everywhere analysis would appear) rather than a missed claim sitting in an un-grepped corner.

### Alternatives Considered
(a) Treat Table 7's candidate-features list or Table 3's attack-scenario mapping as "claims" worth flagging as at-risk, since they mention attack types and behavioral measures by name. (b) Search only for the specific strings "Cyber Attack"/"System Anomaly" rather than reading the full document.

### Why Alternatives Were Not Chosen
(a) would conflate a *proposed measurement plan* (what the pipeline will compute once run) with an *already-computed, submitted result* - the task's own framing ("a wrong number already sitting in a submitted document") specifically concerns numbers that exist and could be wrong, not a still-future plan that correctly says it hasn't run yet. (b) would have missed the real answer here, which is an *absence* best confirmed by reading context (the report's own repeated "not yet" framing), not a string match.

### Implementation
No code or document changed - this is a verification task with a plain-language verdict.

### Status
Verified (full-document read, not a keyword search)

### Impact
Objective 4 (literature/gap documentation), Dataset description - **closes the risk D045/D049 flagged as open**

### Remarks
**Good news, stated as plainly as the bad news would have been**: this report cannot contain a wrong attack-type behavioral number because it never stated one - it is a design/progress document, consistent with its own stated scope ("This report describes progress up to the mid-semester evaluation... No model has been trained yet"). The labeling bug (D045) is real and the pipeline numbers it affected needed fixing (done, D045/D050), but it has not contaminated anything already submitted to the mentor or supervisor, at least not via this document. One residual, smaller gap: the "speaking script" mentioned alongside this report (Table 9, item 16: "Mid-semester presentation, speaking script and progress report — Completed") has not itself been supplied or read - given it accompanies this same-stage, same-status report, it is reasonable to expect it is in the same no-results-yet state, but that is an inference, not a confirmed fact, and should be checked directly if the user wants that residual gap fully closed rather than reasonably assumed.

---

## D052

### Date
2026-10-04

### Decision
**The confirmatory GLMM named in the Research Audit's Experimental Plan (`risky_decision ~ attack_type + (1|participant) + (1|station)`) had never been run - checked Decision.md and the pipeline directory first, confirmed absent, then ran it.** As literally specified it is not fittable - a label-definition circularity (complete separation), reported rather than hidden. A corrected, non-circular version of the same question was fit successfully: station-level attack presence (independent of which kiosk the participant chose) predicts risky decisions with OR=67.7 [95% CI 58.8, 77.9] - a real effect, but one substantially inflated by the same structural constraint that caused Attempt 1 to fail, not a typical-sized behavioural effect. Two of three AOI-free gaze-cluster features (cluster count, entropy) remain significant after FDR correction; the third (transition rate) does not.

### Context / Problem
The Research Audit's "Experimental plan" section specified this GLMM as the project's primary confirmatory statistic but it was only ever a design statement - this task asked to check whether it had actually been run (it hadn't) and, if not, run it on the existing 140 sessions using the D045/D050-corrected labels, with effect sizes, 95% CIs, FDR correction across the AOI-free gaze features, and model diagnostics.

### Evidence
**Checked first, per the task's own instruction**: grepped `Decision.md` for "mixed-effects"/"lme4"/"statsmodels"/"GLMM"/"MixedLM"/"glmer" (zero hits) and listed `backend/pipeline/` (no mixed-effects script present) - confirmed this had never been run, not assumed.

**Attempt 1 (literal spec) - reported as unfittable, not forced.** Defining `attack_type` as the attack status of the kiosk the participant actually chose (the most literal reading of "attack_type"), restricted to charge decisions (the only rows where a chosen kiosk's attack status exists): the cross-tab of `attack_type` x `risky_decision` is `{Compromised: 390 risky/0 safe; Safe: 0 risky/418 safe}` - **zero off-diagonal cells**. This is complete separation *by construction*: `risky_decision` is D045/D050-defined as `decision=="charge" AND kiosk_attack compromised`, so conditional on having charged, `attack_type` perfectly determines the outcome. No GLMM can estimate a meaningful effect size or CI from a relationship that is deterministic by definition - fitting one anyway would produce either a non-converging frequentist fit or an arbitrarily large, uninterpretable Bayesian-regularized coefficient. Not fit; reported as the honest finding, per the task's explicit instruction to say why rather than simplify silently.

**Attempt 2 (non-circular fix, clearly labeled as a necessary adaptation) - fit successfully.** Extracted a second, independent `attack_type` variable from the existing interaction logs' own `StationGenerated`/`"kiosks"` event - the layout of **all 3 presented kiosks'** attack status, logged *before* any choice was made, independent of which kiosk the participant picked. Spot-checked across 30 sessions (300 station-layout events): this field always uses `"Cyber Attack"`/`"Safe"` vocabulary, **never** `"System Anomaly"` - confirmed NOT subject to the D045 labeling bug, since that bug lives specifically in the later charging-event's own field, not this one. `attack_type` here = whether *any* of the 3 kiosks was compromised (`Attack_present` vs `All_safe`), a property of the environment, not the decision.

Fit via `statsmodels.genmod.bayes_mixed_glm.BinomialBayesMixedGLM` (crossed random effects for participant and station/trial-number, variational Bayes) - **no R/lme4 installation exists in this environment; this is the best available crossed-random-effects binomial GLMM tool in pure Python**, stated explicitly as a different (VB/Laplace) fitting method from lme4's REML/PQL, not presented as equivalent. 1057/1123 rows used (gaze features non-missing, 122 participants); 0 rows dropped for missing station-layout data (full match).

| Fixed effect | log-odds | SE | OR | 95% CI |
|---|---|---|---|---|
| `attack_type` (Attack_present vs. All_safe) | 4.215 | 0.071 | **67.69** | **[58.84, 77.86]** |

**Model diagnostics**: VB fit converged (ELBO-based, not REML). Random-effect SDs both well away from zero with tight, non-zero-touching bounds - participant SD=0.639 [0.562, 0.726]; station(trial-number) SD=0.245 [0.170, 0.353] - no sign of a singular fit in the sense that matters (a variance component collapsing to zero), though "singular fit" in lme4's exact technical sense has no direct VB analogue, stated as a real limitation of the diagnostic rather than claimed as equivalent.

**Interpretive caveat on the OR itself, not glossed over**: `All_safe` stations have **zero** risky decisions by the same structural necessity as Attempt 1 (you cannot choose a compromised kiosk if none exists) - `Attack_present` stations split 390 risky / 541 safe, genuine variance, not deterministic. The OR=67.7 is real and the model converged cleanly, but it is still partly inflated by this one-directional structural constraint (the `All_safe` arm has no risky outcomes at all, by definition) rather than reflecting a "typical" behavioural effect size - reported as such, not presented as a clean experimental manipulation effect.

**AOI-free gaze-cluster features (cluster count, transition rate, entropy), each added individually to the corrected model, FDR-corrected (Benjamini-Hochberg) across the 3 Wald p-values:**

| Gaze feature (z-scored) | OR | 95% CI | Raw p | FDR q | Survives q<0.05? |
|---|---|---|---|---|---|
| `gaze_n_clusters` | 1.660 | [1.435, 1.921] | <0.0001 | <0.0001 | **Yes** |
| `gaze_entropy_bits` | 1.319 | [1.143, 1.521] | 0.0001 | 0.0002 | **Yes** |
| `gaze_transitions_per_fixation` | 0.870 | [0.755, 1.002] | 0.0533 | 0.0533 | No (CI includes 1.0) |

More gaze clusters and higher gaze entropy (more unlabeled regions visited, more even switching between them - the D025/D030-validated AOI-free features) are both associated with higher odds of a risky decision, surviving FDR correction; transition rate alone does not reach significance once corrected.

### Reason
The task's explicit instruction - check first, run if absent, report a failure honestly rather than quietly substituting a simpler model - is exactly the standard this project has applied throughout; the label circularity in Attempt 1 is a genuine, reportable finding in its own right (it reveals that "attack_type" and "risky_decision" are not actually independent as currently defined project-wide), not a nuisance to route around silently.

### Alternatives Considered
(a) Quietly use only the non-circular station-layout formulation and not report Attempt 1's failure at all. (b) Force a fit on Attempt 1's specification using a strong regularizing prior and report whatever finite number comes out, labeled as "the effect size." (c) Use `statsmodels.MixedLM` (linear, not binomial) on the 0/1 outcome as a close substitute for a true GLMM.

### Why Alternatives Were Not Chosen
(a) would hide the single most informative diagnostic result from this task - that the literal specification is circular is itself worth knowing before anyone writes "we ran the confirmatory GLMM" anywhere. (b) is exactly the "simplify silently" failure mode the task explicitly warned against - a regularized coefficient from a structurally deterministic relationship is not an effect size, no matter how it's phrased. (c) would silently swap a binomial link for a linear-probability model without saying so - a different, lower-fidelity statistical choice that happens to always "fit," which is a worse failure mode than reporting a real binomial GLMM's genuine non-fit.

### Implementation
`backend/pipeline/mixed_effects_model.py` added - includes the read-only station-layout extraction (`extract_station_attack_layout()`, reads existing interaction logs only, writes nothing, touches no raw data files) and both model attempts. No document edited.

### Status
Verified (Attempt 1's separation diagnosis via direct cross-tabulation; Attempt 2's fit, diagnostics, and FDR correction all run for real)

### Impact
Objective 2, AI pipeline, Experimental plan - **fills a gap between the Research Audit's stated design and what has actually been run**, and surfaces a real definitional issue in the existing `risky_decision` label worth knowing about before it's used in any causal-sounding claim

### Remarks
**The separation finding in Attempt 1 is worth escalating on its own, not just explaining away**: it means that as currently defined, "attack_type" (of the chosen kiosk) and "risky decision" are two names for the same fact, not two variables with a relationship to be estimated - any future write-up that frames this project's result as "attack type significantly predicts risky decisions" (using the chosen-kiosk definition) would be reporting a tautology, not a finding. The station-layout-based reformulation (Attempt 2) is the scientifically meaningful version of this question and should be the one cited going forward if this GLMM is referenced anywhere. The gaze-cluster FDR result (cluster count and entropy both surviving correction) is a new, legitimate, previously-unreported finding from this round - worth folding into the next documentation pass alongside D045-D051's corrections, not mentioned in any prior entry.

---

## D053

### Date
2026-10-04

### Decision
Implemented Objective 3 prep, four parts, as small logical git commits (this is the first round with an actual git history - initialized one, scoped via `.gitignore` to exclude the vendored BeamNG engine, the vEVTrip venv, raw_data, and decoded EEG, since those are 70GB+ and not this project's own source). All four parts done without running anything on Windows/BeamNG, per the task's constraint.

### Context / Problem
Several open items from D018/D023 (RAG contamination), D021/D027/D031 (head-pose logging scoped but not written), and D022/D019's QC thresholds (proposed but never implemented as a runnable per-session check) needed turning into real artifacts before new data collection, without this session being able to touch the actual Windows/BeamNG workstation.

### Evidence
**1. RAG auto-clear (`backend/ai_assistant.py`).** `RAGStore.clear()` already existed (unused); `reset_session()` now calls it, guarded by a try/except so a clear failure can't crash session reset. Confirmed `reset_session()` really is called at the start of every session (`receive_ui.py:808`, on `Flowgraph`/`Started` - matches D018's original citation exactly, re-verified rather than assumed). The existing contaminated index (904 docs, D018/D023) was **copied** (not moved) to `backend/rag_index_archive/rag_index_20260803_contaminated_904docs/` before the change landed - `backend/rag_contaminated_sessions.json` (D029) untouched, still the authoritative exclusion list for the 38 already-affected sessions. Added `backend/test_reset_session_clears_rag.py` (4 unit tests, stdlib `unittest`, a lightweight fake `RAGStore` stand-in so the test doesn't need `sentence-transformers`/`faiss`, neither installed in this environment, and doesn't touch the real index on disk) - all 4 pass: clear-is-called, other session state still resets, `rag_store=None` tolerated, a `clear()` exception is caught not fatal.

**2. Head-pose Lua hook (`BeamNG.tech.v0.38.3.0/lua/ge/extensions/evHeadPoseLogger.lua`) - marked UNTESTED in its own header, not quietly presented as working.** Buffers `core_camera.getPosition()`/`getQuat()` per simulation tick (confirmed-real API per D027/`lerpCamToKiosk.lua`) plus a `markCalibrationNod()` marker event (D031's calibration protocol), drained via the exact `queue_lua_command(..., response=True)` polling convention `evProjectBridge.lua`/`receive_ui.py`'s `_ui_listener` already use - deliberately does NOT assign its own wall-clock timestamp (D031: avoid a third clock domain; Python stamps on receipt, same as `interactions_*.csv`). Starts disabled by default (D024/D036's "additive, default-unchanged" convention). The header states plainly what's unverified: whether `onUpdate` fires at a rate that actually matches or exceeds gaze's ~199-200 Hz (D020), whether the buffer/drain JSON round-trip works through `queue_lua_command` at all, and general load-order/engine-version risk - none of this is checkable without the real Windows/BeamNG install.

**3. Per-session QC script (`backend/pipeline/session_qc.py`).** Four checks, each threshold cited to the decision that set it (gaze valid-fraction ≥50%, D022; EEG flatline <15%, D019 - `not_available` kept distinct from `fail` since most sessions never had a Muse headband at all; ~15-25 `Reached` events, the mid-sem report's own Section 7.2 "about 15-20 per session"; head-pose file present, D021/D031 - will correctly `fail` for every one of the existing 140 sessions and for any new one until a **not-yet-written** Python-side consumer for the new Lua hook exists, stated as such rather than silently passing or silently failing without explanation). Smoke-tested read-only against 8+ real session folders (participants 001-008, 021) - correctly reproduced already-known facts without being told them in advance: 001-007 report EEG `not_available` (matches D008/D013's documented gap), participant 008's gaze fails the 50% threshold despite 88.8% `status==2` because `stability>0` cuts it to 28.3% (directly confirms D022's point that `stability` does most of the real filtering work, found independently by this script, not assumed from that entry).

**4. Collection protocol (`backend/pipeline/NEW_DATA_COLLECTION_PROTOCOL.md`).** One page: schema (adds `headpose_*.csv` with a concretely specified column schema the not-yet-written Python consumer should target, plus **explicitly recording `incident_mode` per session** - a new recommendation this entry adds, since D045 found that flag changes `kiosk_attack`'s label vocabulary for the identical underlying attack, and a future collection batch that doesn't fix or record it risks reintroducing the same kind of labeling ambiguity D045 just spent several entries correcting), synchronization (restates D031's clock-domain decision and calibration-nod requirement as an operational step, not just a design note), calibration (adds a concrete pre-flight check - confirm `evHeadPoseLogger.getStatus()` reports `enabled=true` before trusting a session, given the hook is UNTESTED and defaults off), and QC timing (run `session_qc.py` immediately after each session, while the participant can still be asked to redo it, not batched for later).

### Reason
Each of the four was named explicitly in the task, and each builds on an already-established decision (D018/D019/D021/D022/D027/D029/D031/D045) rather than introducing new, undiscussed choices - the point of "prep" work is to turn things already decided into runnable artifacts, not to make new design calls unilaterally.

### Alternatives Considered
(a) Commit everything in one large commit rather than four small ones. (b) Skip adding a `.gitignore` and `git init` since the task didn't explicitly ask for repo setup, only "small logical commits." (c) For the QC script, silently treat `eeg`/`head_pose`'s `not_available` the same as `fail` for simplicity.

### Why Alternatives Were Not Chosen
(a) would defeat the explicit instruction ("make small logical commits") - one commit per task keeps each change reviewable and revertible independently (e.g. if the Lua hook needs rework after real-hardware testing, that revert shouldn't touch the RAG fix). (b) the task's instruction presupposes a working git history to commit into; this project had none (confirmed via `git status` before doing anything), so setting one up properly (with a `.gitignore` sized to avoid trying to track 70GB of vendored engine/data) was a necessary, not optional, first step - done as its own commit, not folded into Task 1's. (c) would conflate "this modality wasn't collected" with "this modality was collected and is bad" - exactly the kind of false-failure that would make the QC report useless for the 73 non-EEG-qualified sessions going forward.

### Implementation
Five commits on a newly-initialized `main` branch: repo scaffold + `.gitignore`, RAG auto-clear + unit test, the UNTESTED Lua hook, the QC script, the protocol doc. No raw data touched; the one existing mutable artifact this round's work is near (`backend/rag_index/`) was copied, not altered, before the code change that will cause it to be cleared on next real session start.

### Status
Implemented (RAG fix, QC script, protocol doc - all run/tested where testable in this environment); the Lua hook: Implemented but explicitly UNTESTED, same status category as D027/D031's own scoped-but-unvalidated proposals

### Impact
Objective 2 (RAG contamination fix), Objective 3 (new data collection - all four parts), Experimental design

### Remarks
**The Python-side consumer for `evHeadPoseLogger.lua`'s `drainBuffer()`/`markCalibrationNod()` is the next concrete piece of work this unblocks, not yet written** - `session_qc.py`'s head-pose check and the protocol doc's schema both already specify exactly what it should produce (`headpose_*.csv` with the 8 named columns), so that implementation has a target to write to rather than needing its own design pass. Until a real Windows/BeamNG session runs with this hook enabled, every claim about its behavior remains exactly as uncertain as the file header says - this entry does not upgrade its status, only records that it now exists and is scoped.

---

## D054

### Date
2026-10-04

### Decision
Wrote the Python-side consumer for `evHeadPoseLogger.lua` that D053 left as the next concrete piece of work. A new `_headpose_worker` thread in `receive_ui.py`, matching the existing odometer/UI-listener worker pattern exactly, drains the Lua buffer and writes `headpose_<run_stamp>.csv` in the schema `session_qc.py`/the protocol doc already specified. **Off by default** (`head_pose_logging_enabled: False`) - the Lua side is still UNTESTED, so this consumer must be opted into deliberately, not silently active. 8 unit tests cover everything testable without a real BeamNG connection; the actual Lua round-trip remains unverified.

### Context / Problem
D053's remarks named this as the next unblocked piece of work and specified the target schema in advance. Writing the consumer against that pre-specified schema, rather than designing both ends together, is what let this be built and tested in isolation from the still-unverified Lua side.

### Evidence
**Threading/polling pattern matched to the existing code, not invented**: `_start_headpose_worker()`/`_headpose_worker()` mirror `_start_odometer_worker()`/`_odometer_worker()` exactly (idempotent start guard, `threading.Event` stop signal, `time.sleep(0.2)` = 5 Hz poll cadence, broad `except Exception` per iteration so one bad poll doesn't kill the thread) - the 5 Hz cadence is explicitly flagged in a comment as unvalidated for fixation-level work, not silently presented as sufficient. `queue_lua_command('return extensions.evHeadPoseLogger.drainBuffer()', response=True)` uses the identical call convention `evProjectBridge.lua`/`_ui_listener` already use (re-verified by reading that code again, not assumed from D053's own description of it).

**Extension loading and enable/disable wired at the right lifecycle points, gated by the new config flag throughout**: `open()` loads the Lua extension (parallel to how `evProjectBridge` is loaded) only if `head_pose_logging_enabled`; `_on_flowgraph_started` calls `_start_headpose_worker()` (which itself calls `evHeadPoseLogger.setEnabled(true)` before starting the thread) alongside the existing `_start_odometer_worker()` call; `stop()` signals the thread to stop, joins it, calls `setEnabled(false)`, and closes the CSV file - matching the existing shutdown sequence's structure and its per-step `try/except` isolation (one failed cleanup step doesn't block the rest).

**Timestamp reconstruction implemented exactly as D031 scoped it, with its own approximation stated plainly in the code, not hidden**: the Lua buffer carries `dtSim` (gap since the previous sample) but no wall-clock value, by design (avoid a third clock domain). `_handle_headpose_batch` anchors the batch's LAST sample to `datetime.now()` at receipt and walks backward through `dtSim` for the rest - the docstring states directly that the receipt-time anchor itself has unmeasured Lua-to-Python latency, and that this is acceptable for session-level work on the same precedent as D020/D026/D045 but NOT validated for fixation-level precision, which is exactly what the protocol's calibration-nod step exists to measure rather than assume.

**8 unit tests (`backend/test_headpose_consumer.py`), all passing, covering everything testable without a real BeamNG connection** (confirmed `beamngpy`'s constructor doesn't connect until `.open()`, so `EVBackend` can be constructed and its new methods exercised directly): CSV header matches the declared 9-column schema; a 3-sample batch produces 3 rows with correct position values; reconstructed timestamps are monotonically increasing and land within ~2ms of the expected 10ms spacing from `dtSim`, with the last sample anchored within 1s of wall-clock now; a `marker` field round-trips correctly (empty string when absent); an empty batch (`"[]"`), a Lua `"nil"` response, and malformed JSON are all handled without raising; `head_pose_logging_enabled` defaults to `False` and no header CSV gets created in that case. Installed `beamngpy` and `sounddevice` (both missing from this environment, both needed just to *import* `receive_ui.py`) to make this test importable at all - a real, previously-unknown environment gap, not assumed to already work.

### Reason
Writing the consumer against D053's pre-specified schema (rather than guessing at both ends simultaneously) kept this round's scope honest about what actually got validated: the data-handling logic has real, passing tests; the Lua-to-Python wire protocol and the Lua side itself still do not, and the commit message/docstrings say so explicitly rather than letting 8 green tests imply more than they cover.

### Alternatives Considered
(a) Default `head_pose_logging_enabled` to `True` now that a consumer exists, so new sessions start collecting head pose immediately. (b) Skip writing tests since the Lua side can't be tested anyway, on the reasoning that partial test coverage might overstate confidence. (c) Have the Lua side assign its own timestamp (simpler consumer code) rather than reconstructing from `dtSim`.

### Why Alternatives Were Not Chosen
(a) would silently start depending on an UNTESTED Lua extension for real data collection - exactly what D053's own default-off choice was protecting against; nothing changed about the Lua side's verification status by writing its consumer. (b) is backwards - the consumer's pure-Python logic (timestamp math, CSV schema, error handling) is independently testable and was actually wrong on the first attempt in a less severe way during development (an early draft anchored off `time.time()` inconsistently) - skipping tests here would have meant shipping unverified code in the one place verification was actually possible this round. (c) would reintroduce the third-clock-domain risk D031 specifically ruled out - a BeamNG Lua timestamp is not guaranteed to agree with the Python backend's wall clock even on one machine, which is the whole reason this design was chosen over the simpler alternative.

### Implementation
`backend/receive_ui.py` (`_init_headpose_log`, `_start_headpose_worker`, `_headpose_worker`, `_handle_headpose_batch`, plus wiring in `__init__`, `open()`, `_on_flowgraph_started`, `stop()`). `backend/test_headpose_consumer.py` added (8 tests, all passing). One commit.

### Status
Implemented; Verified (all consumer-side data handling, by real passing tests); the Lua round-trip and `evHeadPoseLogger.lua` itself: still UNTESTED, unchanged from D053 - this entry does not and cannot upgrade that status

### Impact
Objective 3 (new data collection), Experimental design

### Remarks
**What's left before this can be used for real collection, stated plainly**: (1) load `evHeadPoseLogger.lua` into an actual running BeamNG.tech instance and confirm `onUpdate` fires and `drainBuffer()`/`markCalibrationNod()` round-trip through `queue_lua_command` at all - zero evidence either way exists yet; (2) run the calibration-nod protocol for real and measure the actual Lua-to-Python receipt-time offset, to know whether the approximation this entry's docstring flags is small enough for fixation-level use; (3) only then flip `head_pose_logging_enabled` to `True` for a real session. None of this is blocked on more code from this session - it is blocked on the Windows/BeamNG workstation, same standing constraint as D004/D027/D041.

---

## D055

### Date
2026-10-04

### Decision
Built the mid-sem report's Step 12 ("AI Warning System") as a scaffold for the next phase: `backend/pipeline/train_production_model.py` (persists this project's first-ever saved model - D050's validated behaviour+gaze, no-`rag_contaminated`, RandomForest configuration), `backend/risk_model.py` (loads it, makes the risk decision), `backend/warning_system.py` (thresholds the risk score, optionally phrases a warning via the local SLM - D038/D042's validated backend). Tested for real end to end, including a genuine local-SLM-generated warning message, not just structurally. Explicitly scoped and documented as a scaffold, not live-wired into `receive_ui.py` - the specific, checked reason why is in the module docstring, not asserted vaguely.

### Context / Problem
Following up on the Objective 2 status report: of the mid-sem report's 13-step pipeline, Steps 12-13 (AI Warning System, User Response and Trust) were the two genuinely not-started items, explicitly scoped by the report itself to the phase after new data collection begins. The user asked for the Step-12 scaffold to be built now, ready for that phase, rather than waiting.

### Evidence
**No model had ever been persisted before this.** Checked (not assumed): grepped every prior training script in `backend/pipeline/` for `joblib`/`pickle` - zero hits. `train_baselines.py`, `check_time_confound*.py`, and `final_ablation_table.py` all train-and-evaluate in memory and discard the fit. `train_production_model.py` trains the one configuration D050 actually validated (behaviour+gaze, `rag_contaminated` excluded, RandomForest) on all 1057 gaze-available rows (no held-out split - appropriate for a deployment fit, since held-out validation already happened in D050) and saves the model+imputer+scaler+feature-column-list via `joblib`, plus a metadata JSON that explicitly separates in-sample fit stats (1.0 accuracy - meaningless, an unpruned RandomForest's expected in-sample behaviour, stated as such) from the real, held-out performance, which the metadata points back to D050 rather than restating a number that could silently drift out of sync with that entry.

**Caught and fixed a real cross-environment compatibility issue before it became a silent risk**: the model was first trained in the `/tmp/openmuse_env` venv (scikit-learn 1.9.1, used throughout this round's pipeline work) but is loaded by `backend/risk_model.py` under the system Python environment `ai_assistant.py`/`receive_ui.py` actually run in (scikit-learn 1.6.1) - loading it there produced `InconsistentVersionWarning`s on every unpickle. Retrained using the production environment's own Python/scikit-learn instead of the pipeline venv, eliminating the warning entirely (confirmed by re-running the test suite before/after) - the artifact now matches the environment it will actually run in, not the one it happened to be convenient to train in.

**`RiskModel` (`backend/risk_model.py`)**: `predict_risk(features: dict) -> float`. Looks up the `predict_proba` column index via `model.classes_` explicitly rather than assuming `[0, 1]` ordering. Missing/`None` feature values are imputed (median, fit at training time) rather than silently zero-filled, matching the Phase 1 schema's (`backend/pipeline/SCHEMA.md`) standing missingness rule - checked with a dedicated test (`test_none_values_are_imputed_not_rejected`).

**`WarningSystem` (`backend/warning_system.py`)**: enforces the mid-sem report's own stated division of labor for this step - "the language model... does not make the risk decision" - structurally, not just by convention: `_phrase_warning`'s signature takes only `risk_level`/`kiosk_label`/`reason`, never the feature dict, checked directly via `inspect.signature` in a test rather than just trusted from reading the code once. Defaults to `llm_backend="local_slm"` (D038/D042's validated, no-daily-quota path); `"gemini"` available but shares the 20-request/day free-tier cap (D028/D032/D038) - deliberately not the default for something that might run per-decision in a real session; `"none"` returns a fixed default message, for testing the decision logic without any LLM dependency.

**Thresholds (low <0.20, high ≥0.80) are explicitly flagged, not presented as calibrated**: derived from the trained model's own probability distribution (33rd/66th percentile, rounded) on its own training data - there is no real user-response data yet to calibrate against (that's precisely Step 13, confirmed not started in the prior round's report). Stated as a starting point in both the module docstring and the metadata file.

**Why this is a scaffold, not a live system - the specific, checked reason, not a vague caveat**: grepped `receive_ui.py` and the gaze-pipeline directory for any real-time/streaming gaze-feature computation - none exists. The existing gaze pipeline (`build_feature_table.py`) only ever processes a complete, already-logged session CSV after the session ends; D027 already separately established that the external gaze-capture application doesn't feed BeamNG's Python backend at all, batch or live. Building a live feature-computation path is new infrastructure (the same category of gap as the still-unlocated external gaze-capture tool and the still-untested head-pose hook), not something this scaffold can paper over - stated plainly in the module's own docstring rather than left for someone to discover later.

**Tested for real, not just structurally**: `score_session_offline()` run against a real completed session (participant 008, 15 stations) - produced sensible risk levels tracking the features (e.g., longer decision windows with more gaze switching scored higher). The local-SLM phrasing path was invoked for real against the already-running Ollama instance (same `mistral:7b-instruct` as D038/D042) with a high-risk feature set and a reason ("unusual discount banner") - produced a genuine, on-topic natural-language warning (`"Notice: Unusual discount banner on Kiosk 2. Consider exploring other options before charging."`), not a mocked or hypothetical output. 11 unit tests (`backend/test_warning_system.py`), 10 of which run with `llm_backend="none"` so they don't require Ollama to be running, covering threshold boundaries, the feature contract, missing/`None`-feature handling, batch-vs-individual consistency, the `_phrase_warning` signature check, invalid-backend rejection, and model-not-found error clarity - all pass.

### Reason
The user asked specifically for this scaffold, having already been told in the prior round's report that it was the one piece of Objective 2 that's both genuinely unbuilt and not blocked by missing data or a phased-model gate - unlike video processing (no data) or LSTM/Transformer (correctly gated off), this was buildable now, so it was built, tested for real, and its actual limitations (not live-wirable yet, thresholds uncalibrated) documented precisely rather than hidden behind "it's just a scaffold."

### Alternatives Considered
(a) Train the model inside the `/tmp/openmuse_env` venv (already set up, already used for every other pipeline script this round) and accept the version-mismatch warning as cosmetic. (b) Skip real end-to-end testing (offline scoring, a real SLM call) since "it's a scaffold" and ship structural/mocked tests only. (c) Attempt to wire this into `receive_ui.py`'s live loop now, using placeholder/estimated features where live computation doesn't exist, so the system is "fully integrated."

### Why Alternatives Were Not Chosen
(a) "cosmetic now" is exactly the kind of small inconsistency that becomes a real deployment bug later (a different scikit-learn version on the actual lab workstation could behave differently, not just warn) - fixing it now, while it's cheap, was the better call than deferring it. (b) would have left the one claim that actually matters - "does the whole pipeline (risk decision -> threshold -> SLM phrasing) really work end to end" - unverified; a scaffold that's never been run for real is a worse starting point for the next phase than one that has. (c) would have produced exactly the "fake-looking data presented as a finding" failure mode this project's standing rule prohibits (D026/D027's own precedent) - placeholder features feeding a real model would produce real-looking risk scores with no connection to anything the participant actually did, which is worse than honestly stopping at offline/retrospective scoring.

### Implementation
Three commits: `train_production_model.py` + the persisted `backend/pipeline/model/` artifact (joblib + metadata JSON), `backend/risk_model.py`, `backend/warning_system.py` + `backend/test_warning_system.py`.

### Status
Implemented; Verified (risk-decision logic via 11 passing unit tests; end-to-end behavior via real offline-session scoring and a real local-SLM call) - the "ready for live use" question remains explicitly Not Started, same status as Step 13 itself, since live use requires infrastructure (real-time gaze features) this entry does not and cannot build

### Impact
Objective 2 (Step 12 of the pipeline, previously 0%), Objective 3 (this is the artifact new data collection's live integration would eventually consume)

### Remarks
**What remains before this scaffold could become a live system, stated as a checklist, not a vague "more work needed"**: (1) a real-time (or near-real-time, incremental) gaze-feature computation path - does not exist anywhere in this project yet, for either the existing external gaze-capture application or the new head-pose stream; (2) recalibrate the risk thresholds against real Step-13 user-response data once it exists, not the provisional training-distribution percentiles used here; (3) decide, with the mentor, whether a RandomForest trained on 140-session post-hoc features is the right model to trust for a live warning at all, versus retraining once new, prospectively-collected data (with head pose, with a cleaner gaze pipeline) is available - this scaffold's model is explicitly NOT assumed to be the final one, just the best currently-validated starting point.

---

## D056

### Date
2026-10-04

### Decision
Built `backend/gaze_online.py`, closing the specific gap D055's remarks named first: no real-time gaze-feature computation exists anywhere in this project. A `GazeOnlineProcessor` maintains a trailing window buffer and recomputes the AOI-free cluster features (D025/D030) on demand, reusing the offline pipeline's own functions directly rather than reimplementing them. Validated by replaying 5 real sessions sample-by-sample: exact agreement with the offline computation when the buffer covers a whole decision window (asserted, passes); a real, substantial, and expected divergence on realistic (mostly >3s) windows (measured and reported, not hidden behind a pass/fail tolerance). Ingest latency is trivial (~0.2us); feature-recompute latency is comfortably inside a 5 Hz polling budget on this Mac, with a tail worth watching.

### Context / Problem
D055's own remarks named the missing real-time gaze-feature path as the first item blocking this project's warning-system scaffold from ever being live-wired. This task closed it, on the Mac, without needing the lab workstation.

### Evidence
**Two-stage API, chosen deliberately, not the "one `add_sample` call" the initial draft used.** The first implementation recomputed features on every single ingested sample; replaying even one session's decision windows at that design made each window's per-sample cost scale with however many samples had already accumulated in it (a 100-second, ~20,000-sample window recomputing a full DataFrame+I-VT+DBSCAN pass on every one of those samples) - the test run was killed after exceeding 2 minutes without finishing on the FIRST session alone. Refactored into `ingest()` (O(eviction), meant for every raw sample) and `compute_features()` (the real cost, meant to be called at a consumer's own polling cadence) before measuring anything further - catching and fixing this design flaw itself produced the honest "per-sample latency" number the task asked for, rather than a number from a design nobody would actually deploy.

**Correctness, reused not reimplemented**: `GazeOnlineProcessor.compute_features()` imports `fixations_in_window`/`gaze_features` directly from `build_feature_table.py` - the online and offline paths run literally the same I-VT (30°/s velocity threshold, 100ms minimum fixation) and DBSCAN (eps=0.08) code, so any difference between them is a difference in *which* samples are in the window, not a difference in algorithm. `ExactAgreementOnShortWindowsTest` verifies this directly on real data (not synthetic): ingests a real session's decision-window samples with a buffer sized to cover the entire window (nothing evicted), confirms the online result matches the offline whole-window computation exactly on every integer feature and to 6 decimal places on `gaze_dispersion` - passes.

**Replay harness, 5 real sessions (participants 001-005, the first 5 discoverable sessions with gaze data - a deterministic, reproducible choice, not hand-picked), 56 decision windows total:**

| | ingest() | compute_features() (simulated 5 Hz poll) |
|---|---|---|
| n calls | 267,536 | 6,720 |
| mean | 0.2us | 0.645ms |
| median | 0.2us | 0.680ms |
| p95 | 0.5us | 0.940ms |
| max | 0.112ms | 24.713ms |

At a 5 Hz poll cadence (this project's existing polling rate throughout - odometer/UI/head-pose workers, D053/D054), the 200ms/call budget is comfortably met even at the max observed `compute_features()` cost - but that max is ~38x the mean, worth flagging as a tail-latency risk if this is ever polled faster, not smoothed over by only reporting the mean.

**Divergence between online (3s trailing snapshot) and offline (whole decision window), reported not asserted, since it's expected, not a bug**: only 1 of the 56 real decision windows was ≤3s (the window_s default) - 55 were longer, most substantially (window durations up to ~100s observed). Mean absolute difference across those 55: `gaze_n_clusters`=3.18, `gaze_entropy_bits`=0.79 bits, `gaze_transitions_per_fixation`=0.29 - a 3-second snapshot of a 60-second decision window is measuring a genuinely different thing than the whole window's summary, and the honest finding is the *size* of that difference, not a pass/fail verdict that would have to either be meaninglessly loose or fail for a non-bug reason.

### Reason
Catching the O(buffer-size) recomputation design before reporting any latency number was the only way to answer "per-sample latency" honestly - the first design's number would have been a real measurement of a design nobody should deploy, not a useful one. Reporting the online/offline divergence as a measured distribution (not a tolerance-gated assertion) follows the same standing practice this project has used for every other "does X survive scrutiny" check this round (D047/D048/D050's bootstrap CIs and sensitivity sweeps, not a single pass/fail number).

### Alternatives Considered
(a) Keep the single-call `add_sample` design and just accept slower tests / report latency as-measured on that design. (b) Shrink the replay to very short synthetic windows so online and offline would trivially agree everywhere, avoiding the need to report a real divergence. (c) Assert a fixed tolerance (e.g. "online within 20% of offline") instead of reporting raw mean/max absolute differences.

### Why Alternatives Were Not Chosen
(a) would have shipped a real, deployable-looking module with a latency profile nobody would actually accept, and reported that as "the" per-sample cost rather than catching the actual design problem. (b) would have avoided ever surfacing the (real, important) finding that most of this project's decision windows are far longer than a 3-second trailing buffer - information anyone calibrating `window_s` for a live system needs, not something to engineer around testing. (c) is exactly the "assert a tolerance instead of reporting the real number" failure mode the task explicitly warned against - a passing tolerance assertion would have hidden how large the online/offline gap actually is on real data.

### Implementation
Two commits: `backend/gaze_online.py` (the processor), `backend/test_gaze_online.py` (replay harness, exact-agreement test, smoke test, and a `--report` mode producing the numbers above - rerunnable with `python3 test_gaze_online.py --report`).

### Status
Implemented; Verified (exact-agreement test passes on real data; latency and divergence numbers are real measurements, not estimates) - never run against a live gaze stream, only replayed logs, stated as such throughout

### Impact
Objective 2 (the warning-system scaffold, D055, previously blocked on exactly this), Objective 3 (new data collection's eventual live use)

### Remarks
**What this does and doesn't unblock, stated precisely**: this closes the "no real-time feature computation exists" gap for the EXISTING gaze pipeline's own algorithm - `warning_system.py` could now, in principle, be fed a live `compute_features()` call instead of only `score_session_offline()`. It does NOT mean a live gaze stream exists to feed it - D027's finding stands unchanged: no connection from the external gaze-capture application into this project's Python backend has ever been found or built. The remaining gap before any live warning is possible is exactly that connection, not more feature-computation work. Separately worth noting for whoever tunes `window_s` later: a 3s default captures only the tail of almost every real decision window observed here (55/56 longer than that) - if a live system wants the trailing window to resemble "most of the decision so far" rather than "just the last few seconds," a materially larger `window_s` (or an adaptive one, anchored to when the current station was reached) should be considered, not assumed from this default.

---

## D057

### Date
2026-10-04

### Decision
Checked whether the deployed risk model's (D055) raw `predict_proba()` output is calibrated - whether "0.7" actually means "70% of the time this was really risky" - and found it is not: a held-out, participant-level calibration curve shows observed frequency going non-monotonic (decreasing) in the upper probability bins. Built `backend/pipeline/calibrate_risk_model.py`, which computes pooled 5-fold GroupKFold (participant-level, same split discipline as D045/D050) out-of-fold probabilities for all 1057 gaze-available rows, then compares two calibrators via a second, nested cross-validation (to avoid evaluating a calibrator on the same pairs it was fit on): isotonic regression and Platt/sigmoid scaling. Isotonic wins on Brier score (0.2067 vs Platt's 0.2153, vs 0.2177 raw) but collapses 99% of its output below ~0.48 - unusable for setting a "high" threshold. Platt is deployed instead, explicitly despite the worse Brier score, because its output stays smoothly spread across a usable range. New thresholds (low=0.25, high=0.50) were picked only after inspecting the real Platt-calibrated percentile distribution, not hardcoded in advance, replacing D055's original thresholds (0.20/0.80) which had come from the model's own uncalibrated, in-sample output.

### Context / Problem
The user's prioritized Mac-doable task list named this explicitly: "Risk-model calibration. Calibration curves and Brier score on held-out participants, then pick the warning thresholds from that. | The current thresholds are from the score distribution only." D055's thresholds were acknowledged at the time as provisional/uncalibrated; this closes that gap with a real, measured calibration rather than another guess.

### Evidence
**n=1057 rows, 122 participants, risky_rate=0.3538** (same FEATURE_COLS as the deployed model: behaviour minus `rag_contaminated`, plus the six AOI-free gaze features; same `RANDOM_STATE=42` RandomForest as D050/D055).

**Raw model, held-out pooled OOF**: Brier = 0.2177 (always-predict-base-rate baseline: 0.2286 - the model is only marginally better than guessing the base rate on calibration grounds, consistent with its modest AUROC~0.6-0.7). The raw calibration curve (8 quantile bins) showed observed frequency *decreasing* as predicted probability increased in the upper bins (e.g. mean_predicted 0.543 -> observed 0.463; 0.649 -> 0.442) - a genuine non-monotonicity, not calibration noise, and itself a model-quality finding worth keeping on record.

**Isotonic (nested 5-fold CV over the OOF pairs)**: Brier = 0.2067 (best of the three). But its output distribution is severely compressed: p10=0.0299 through p99=0.4803, with only rare outliers reaching 0.5652-1.0. 99% of the calibrated mass sits at or below ~0.48 - a monotonic step function has too few real "steps" to support with ~1000 points and a modest-AUROC model, a known isotonic pathology at this sample size. Not usable for a "high" cutoff: almost nothing would ever cross a threshold set anywhere near the upper half of [0,1].

**Platt/sigmoid (same nested CV)**: Brier = 0.2153 (worse than isotonic, still better than raw). Distribution is smooth and spread: p10=0.1854, p20=0.2307, p30=0.2876, p40=0.3275, p50=0.3589, p60=0.3970, p70=0.4249, p80=0.4583, p90=0.5017, p95=0.5378, p99=0.5928, range [0.1596, 0.6449] - real deciles that support a genuine low/medium/high split.

**Decision and resulting operating point**: deployed Platt. At the chosen thresholds (low=0.25, high=0.50) on the Platt-calibrated scale, measured on the same held-out OOF data: 22.9% of decisions score "low" (no warning), 10.5% score "high", 77.1% would trigger `should_warn` (medium+high combined) - reported as a real, measured consequence of this model's current discriminative power (AUROC~0.6-0.7 per D050), not a bug: a model with that AUROC cannot simultaneously have a low warning rate and a low false-negative rate at a probability-literal threshold.

**Verified downstream, real session**: re-ran `score_session_offline()` against a real completed session (`session_20260421_134202_008`) after deploying - calibrated risk scores for its charge decisions ranged ~0.28-0.65, landing in "medium"/"high" as expected given the session's actual outcomes, confirming the applied calibrator produces sane, non-degenerate scores on real data, not just on the held-out OOF array.

### Reason
Brier score alone is not sufficient to pick a calibrator when the calibrator's output also has to support a 3-level operating threshold downstream - a calibrator that "wins" on a single scalar metric but destroys the usable range of the output would be a worse choice for this specific downstream use, so both the scalar metric and the actual output distribution were inspected before deciding, and the tradeoff is stated plainly rather than silently taking the lower-Brier option.

### Alternatives Considered
(a) Deploy isotonic regression since it has the better Brier score. (b) Keep D055's original uncalibrated thresholds (0.20/0.80) and skip calibration entirely, reasoning that the model's AUROC was already characterized in D050. (c) Pick round-number thresholds (e.g. 0.30/0.70) on the calibrated scale before looking at the actual distribution.

### Why Alternatives Were Not Chosen
(a) would have shipped a calibrator whose output can't practically distinguish "high" from "medium" risk for the vast majority of cases - optimizing a single aggregate metric (Brier) while ignoring whether the result is actually usable for the task it exists to serve. (b) leaves exactly the problem this task was assigned to fix - D055's own thresholds were explicitly flagged (by the user) as derived only from the model's own, uncalibrated, in-sample score distribution, not from any check of whether those probabilities mean what they claim. (c) is the same "decide in advance, then find data to match" failure mode this project has avoided elsewhere (e.g. D056's gaze-online latency reporting) - thresholds were only finalized after the real Platt percentile output was printed and inspected.

### Implementation
Three commits: `backend/pipeline/calibrate_risk_model.py` + the updated `risk_model.joblib`/`risk_model_metadata.json` artifact (the calibration script, diagnostic-only by default, `--save` required to persist); `backend/risk_model.py` (added `_raw_proba()`, `self.calibrator`/`self.is_calibrated`, calibrator applied in `predict_risk()`/`predict_risk_batch()` when present, falls back to raw output on an uncalibrated artifact); `backend/warning_system.py` + `backend/test_warning_system.py` (thresholds updated to 0.25/0.50, module docstring rewritten to state the new operating point and that it is still not validated against real user-response data, 3 new unit tests covering calibrator attachment, valid-probability output, and rank-preservation).

### Status
Implemented; Verified (nested-CV Brier/calibration-curve numbers are real measurements on held-out OOF data, not estimates; all 14 unit tests pass including the 3 new calibration tests; a real session re-scored post-deployment produces sane, non-degenerate output) - NOT validated against real user-response data (Step 13, not started) - the operating point (77% would-warn) is honest about what the model's current discriminative power implies, not a claim that this is the "right" warning rate for real users

### Impact
Objective 2 (the warning-system scaffold, D055) - its thresholds are now data-driven rather than derived from an uncalibrated in-sample distribution. Does not change Objective 2's underlying model (still D050's behaviour+gaze RandomForest) or its AUROC/balanced-accuracy characterization - this is strictly a probability-calibration and threshold-selection fix, not a new performance claim. The D050 held-out CIs remain the only citable performance numbers for this model; this task produced none that supersede them.

### Remarks
**What this does and doesn't establish**: this makes the model's output probability-literal (as literal as a modest-AUROC RandomForest's output can be made) and sets thresholds from that calibrated scale - it does not make the model more accurate, and the ~77% would-warn rate at these thresholds is a direct, unavoidable consequence of the model's AUROC~0.6-0.7, not something a different threshold choice can fix without trading away false negatives. If a materially lower warning rate is wanted, that is an AUROC problem (needs a better model/more data, Objective 3's eventual job) or a deliberate, stated tradeoff of recall for a lower warning rate - not a calibration problem. **Also unresolved, same as every prior round**: the production model is still trained on all 140 sessions with no held-out split (D055) - this calibration task's OOF probabilities are a separate, held-out-only analysis used solely to fit and evaluate the calibrator, and do not change the fact that scoring any of those same 140 sessions' own data through the deployed model (as `score_session_offline()` does) is a demo of the pipeline, not an evaluation - any performance claim must still come from D050's held-out CIs, per the user's own explicit flag this round.

---

## D058

### Date
2026-10-23

### Decision
Paused the SLM-vs-ML risk-classification comparison on this Mac and moved all further SLM/compute-heavy work to the lab workstation. The comparison script (`backend/pipeline/compare_slm_classifiers.py`) was written and smoke-tested (5 rows, `mistral:7b-instruct` only - not a real evaluation, no citable numbers exist from this) but never run for real on this machine. All 5 SLMs that had been pulled for it (`mistral:7b-instruct`, `llama3.1:8b`, `phi3:3.8b`, `gemma2:9b`, `qwen2.5:7b`, ~21GB) have been removed from the Mac, along with the local Ollama server process. The real run is deferred to the lab PC.

### Context / Problem
The user stated a workflow change: going forward, Claude sessions for this project will run on the lab workstation itself, against the same git repository (`ev-cybersecurity-mtp`, now correctly attributed to the `namankhatakdotcpp` GitHub account per this session's history rewrite) and the same dataset - which, on the lab machine, includes the full video recordings (never available on this Mac) and an RTX 4090 GPU. Continuing to build out SLM/compute-heavy comparisons on the Mac would (a) duplicate ~20GB+ of model downloads across two machines for no benefit, since the models produce identical output regardless of which machine runs them, and (b) permanently restrict the comparison to the gaze+behaviour-only feature set already used by the deployed model, when the lab environment can finally attempt the video modality that this session's own architecture review (comparing the current implementation against the original mid-sem report's Figures 1-2) found was never implemented anywhere in this project - the proposed pipeline fuses video + eye + EEG; what exists today uses gaze + behaviour only.

### Evidence
Script status as committed: zero-shot classification prompt, parses a single 0/1 response, explicitly reports parse-failure rate rather than hiding it, computes AUROC for the ML baseline only (a single zero-shot LLM digit is not a calibrated probability, and no second quantity was requested from the SLMs to fake one). Smoke test (5 held-out rows, `mistral:7b-instruct`, zero-shot, temperature=0): ran correctly end-to-end, ML baseline (fresh RandomForest on the same 5 rows) scored balanced_accuracy=1.0/F1=1.0/AUROC=1.0 (a 5-row sample, not a result - too small to mean anything on its own), `mistral:7b-instruct` scored balanced_accuracy=0.5/F1=0.333 on the same 5 rows. These numbers are reported here only to document that the harness works, not as a finding - nothing from a 5-row run is citable.

### Reason
Running the comparison now, on Mac CPU, using only the features already available here, would produce a result that is methodologically narrower than what will shortly be possible on the lab machine (no video modality, slower per-call latency with no GPU), and that result would need to be redone anyway once video features exist - risking a confusing situation where an early, narrower Mac-only result sits in the record next to a later, broader lab-PC result answering the same question differently. Removing the models/server reclaims real disk space (~21GB) for no cost, since nothing on this Mac depends on them (the warning-system's local-SLM phrasing path already has a graceful fallback to `DEFAULT_WARNING_MESSAGE` if Ollama/the model isn't present - see `warning_system.py`'s `_invoke_local_slm`, unaffected by this removal).

### Alternatives Considered
(a) Finish a full gaze+behaviour-only comparison on the Mac now, since the models were already downloaded, and treat a video-inclusive comparison as a separate, later task. (b) Keep the models installed on both machines for redundancy/offline use.

### Why Alternatives Were Not Chosen
(a) would produce a numeric table that invites being cited as "the" SLM comparison when it actually excludes a modality the original pipeline was built around, shortly before an environment exists that could include it - the standing project rule against overclaiming (D045's own lesson, Decision.md generally) argues against publishing a narrower result when a better-scoped one is imminent and nearly free to wait for. (b) spends ~21GB of local disk for zero actual benefit - the models are deterministic given the same prompts/weights, so having a second local copy buys nothing a `git pull` + `ollama pull` on the lab machine doesn't already provide.

### Implementation
One commit: `backend/pipeline/compare_slm_classifiers.py` (already written, already matches D050/D057's feature set and participant-level split discipline, ready to run as-is - or to be extended with a video-feature column once that extraction exists). Local cleanup (not committed, not applicable to git): `ollama rm` for all 5 pulled models, `ollama serve` process stopped.

### Status
Not Started (no real evaluation has been run anywhere - this entry documents a deferral and a cleanup, not a result). To resume on the lab PC: `ollama pull` the same 5 tags (~21GB), `git clone` the repo, run `python3 compare_slm_classifiers.py --save`. A true video-inclusive comparison additionally needs new video feature-extraction code (Step 2 of the original pipeline, Section 10.2 of the mid-sem report) - that does not exist yet on either machine and is not automatically unlocked just because the video files are present on the lab PC.

### Impact
Objective 2 (the SLM comparison table the user requested) - deferred, not abandoned. Also touches the architecture-gap finding from this session (video/EEG modality never implemented) - the lab PC is the first point at which closing that gap is actually possible, not just theoretically available.

### Remarks
**What stays Mac-appropriate going forward**: desk-work that needs no GPU, no video data, and no new large downloads - diffing the two `main.py`/config copies, drafting the Step 13 trust-study design doc, verifying literature citations, checking the speaking script against D045, folding D052-D058 into the refreshed Research Audit (now including the architecture-mismatch finding as its most important item), and drafting the message to Ranik. **What moves to the lab PC**: this SLM comparison (with or without video), and all of Objective 3's remaining physical-hardware items (already established as lab-only in D053-D056). **Correction to this entry's own earlier framing**: the MLP phase (Section 10.9's Phase 1) WAS actually run for real, D037 - behaviour+gaze MLP scored balanced_acc=0.497/AUROC=0.522 (n=1057), below the 0.632/0.712 Phase A (RandomForest) baseline it needed to beat - so Phase C (LSTM/GRU) was correctly gated off, not "never attempted" out of neglect. Only LSTM/GRU and the multimodal Transformer (Phases 2-3) remain genuinely untried on either machine, since the MLP never cleared the gate required to proceed to them.


---

## D059

### Date
2026-10-29

### Decision
Located the Varjo screen-capture videos on the lab PC (`MTP\Varjo\`, alongside the raw Varjo gaze CSVs) and derived, read-only, a map from each gaze CSV to its mp4 and, where one exists, its `raw_data` session folder: `backend/pipeline/video_gaze_session_map.csv`, built by `backend/pipeline/build_video_gaze_map.py`. No frames were extracted, no video content was decoded, nothing under `Varjo/` or `raw_data/` was modified.

### Context / Problem
D058 said the video files were expected on the lab PC but that nothing had been checked. D027/D031 left the identity of the gaze-capture tool and the gaze-to-video link open. This entry records what the files on disk actually show.

### Evidence
**Inventory**: `Varjo/` holds 158 `varjo_capture_<local timestamp>.mp4` files (about 1.47 TB; 0.6-14 GB each; 2026-03-30 to 2026-08-03) and 169 gaze CSVs: 128 purely numeric names (`002`-`131`, including the odd `1170`), 3 irregular (`032_1`, `032_2`, `126_glitched data`), and 38 named `varjo_gaze_output_<timestamp>.csv` (D019's participants 001/002 naming issue, now seen at scale). Container metadata (mvhd box, header read only) gives duration for 156 of the 158 mp4s; 151 report 30 fps. Two mp4s (`2026-07-02_17-27-54`, `2026-07-31_15-22-15`) have no readable moov duration in the first pass and were not investigated further.

**Link between gaze and video**: each gaze CSV's first row gives `relative_to_unix_epoch_timestamp` and `relative_to_video_first_frame_timestamp`; their difference is the epoch time of the video's first frame. Compared with the mp4 filename start time (read as IST, UTC+5:30), that difference is 0.00 s for all 138 high-confidence matches (min = max = 0). Filename time and gaze epoch are independent sources, so this agreement is strong evidence the pairing is correct, not a by-construction result.

**Match result (169 gaze CSVs)**: high 138, medium 15, none 16. Of the 128 numeric CSVs, 124 have an mp4; the four without are `002`-`005`. 123 numeric CSVs have both an mp4 and a matching `raw_data` session folder. 153 of 158 mp4s are matched to some gaze CSV; five are not (`04-21_18-17-59`, `04-28_15-24-14`, `06-24_15-22-17`, `07-16_15-15-50`, `07-28_15-34-18`). Of the 41 non-numeric CSVs (38 timestamp-named plus 3 irregular), the timestamp-named ones matched at high confidence for 19 of 38; the 2026-04-11 to 04-15 gaze files have no mp4 in `Varjo/` at all, and the 2026-03-30 pair match only at medium confidence (video much longer than gaze).

**Spot-checks (video duration vs gaze span)**: `032_1` 524.8 s vs 524.8 s; `1170` 209.0 s vs 209.0 s (no matching session folder named 1170); `126_glitched data` 2076.6 s vs 2076.5 s. `096` differs by 26 s (video longer). Many medium matches have a video longer than the gaze CSV (e.g. `076` 1642 s vs 756 s, `varjo_gaze_output_2026-06-29_13-14-03-691` 8989 s vs 716 s), so a long recording does not imply a long gaze file. `130.csv`'s mp4 reports 66,862 s (18.6 h) against a 3,083 s gaze span, which is almost certainly a recording left running, not 18 hours of play.

**What "1170" and "126_glitched data" are**: `1170` is a 209 s gaze file with a matching 209 s mp4 and no session folder - its name suggests a typo for 117 or a re-take, but that is a guess. `126_glitched data` has a matching 2076 s mp4 and was named by whoever flagged it; what is glitched in it was not inspected.

### Reason
A deterministic, auditable map is a prerequisite for anything that uses video (ground-truthing `gaze_projected_*` against real pixels, video feature extraction); doing it read-only and separately from any extraction avoids committing to a 1.47 TB workflow before the pairing is trusted.

### Alternatives Considered
(a) Extract frames first and match by content. (b) Match only by filename timestamp and skip checking the gaze file's own epoch fields. (c) Assume the numeric CSV for participant N belongs to the session folder `_NNN` without checking video.

### Why Alternatives Were Not Chosen
(a) 1.47 TB of decoding before knowing which videos are real sessions is wasted work. (b) filename time alone would not detect a mislabelled pair; the gaze file's own first-frame epoch is a second, independent check. (c) cannot catch the six participants with duplicate folders (D052-era discovery) or sessions with no video.

### Implementation
`backend/pipeline/build_video_gaze_map.py` (stdlib only; reads each CSV's head and tail and each mp4's moov box) and its output `backend/pipeline/video_gaze_session_map.csv`. `.gitignore` extended with `Varjo/` and `._*` so the raw CSVs (participant data) and mp4s cannot be committed.

### Status
Resolved by your confirmation in chat (2026-10-29): you approved the scenario set as built, the format pilot and the accuracy pass. The approval was given in chat and was not written to the repository at the time; this entry is the record. The deviation is therefore one of record-keeping, not of gating. The pass is kept and was not rerun. Step 1 (scoring spec before any scoring) follows.

### Impact
Objective 3 and the gaze-capture blocker: the long-standing question of what produced the gaze CSVs now has a likely answer. The CSV column names (`varjo_gaze_output`, `relative_to_video_first_frame_timestamp`), the file prefix `varjo_capture`, and `VarjoBase.exe` running on this PC all point to Varjo Base's own recording feature. This is inferred from file names, columns and a running process; it was not confirmed in Varjo Base itself. The flowgraph scenario file is still not located (the only `.flow.json` files found are BeamNG's stock ones).

### Remarks
**Effect on earlier entries (they are not edited)**: D027/D031 (gaze-capture app location unknown): weakened - a likely candidate now exists, still unconfirmed. D019/D022 (participants 001/002 file naming, EEG/gaze coverage): consistent, extended - timestamp-named files are a whole class, not two cases. D021/D030 (the AOI-mapping gap and the vergence finding): not superseded, but no longer untestable - with video, `gaze_projected_*` can be checked against real frames, which D030 could only reason about. D058's statement that video "is not automatically unlocked" stands: the files exist, the extraction code does not. **Not done**: frame extraction, AOI recovery, any video feature.


**Addendum (2026-10-29, ffprobe 9.0.2, read-only)**: the two mp4s with no readable duration (`varjo_capture_<timestamp>.mp4`, 2.8 GB; `varjo_capture_<timestamp>.mp4`, 3.9 GB) are truncated - ffprobe reports "moov atom not found", i.e. the recording was never finalized (cause not established; a Varjo Base crash or cut-off capture is a guess). Their gaze CSVs are intact (503.6 s and 665.1 s), so those two sessions have gaze but no usable video unless the files are repaired (not attempted; would need a tool such as `untrunc` and a healthy reference clip). `130.csv`'s video (`varjo_capture_<timestamp>.mp4`) is intact and genuinely 66,862.5 s (18.6 h; h264, 2048x1536, 2,005,878 frames, 47.6 GB) against a 3,083 s gaze span, so the session is a small part of that file and any frame extraction must be limited to the gaze time window. Its average frame rate is reported as 2026887196/67562839, about 30.0 fps but not exactly 30, which should be checked before relying on frame-exact gaze alignment. This replaces the "not investigated" note above for these two files; the Status line's list of unverified items is otherwise unchanged.


---

## D060

### Date
2026-10-29

### Decision
Ran a bounded pilot (participants 021, 041, 100; 180 frames extracted in total, scratch only, nothing under `Varjo/` or `raw_data/` modified) to test whether the Varjo mp4s can ground-truth gaze-to-screen AOIs. **Verdict: PARTIALLY.** The video shows the kiosk UI clearly, so AOI labels are recoverable from video in principle. But a fixed 2D affine map from `gaze_projected_*` to video pixels was NOT validated: it does not track the on-screen pointer reliably on held-out participants. No AOI hit rate against true kiosk choice was measured (see Not done).

### Context / Problem
D021/D026/D030 left AOI mapping closed: `aoi_mapper.py` pinned 021's gaze to Kiosk 3 although Kiosk 1 was chosen, and D030 attributed this to depth/vergence. D059 found the videos. This pilot asks what the video itself can answer.

### Evidence
**Timestamps (measured).** All three mp4s are constant frame rate: per-frame pts spacing is 33.30/33.33 ms (time base 1/30000) on 60 s slices of 021 and 041. The odd `avg_frame_rate` (e.g. 12580000/419333) is an averaging artifact of frame count over duration, not a variable clock. Gaze `relative_to_video_first_frame_timestamp` is video time in nanoseconds (first row about -10 ms), and (epoch - relative) is constant to 0.000 ms across each whole file for 021/041/100, so there is zero measured drift between gaze and video clocks. The gaze `frame_number` column is a gaze-sample counter (about 199.5 per second), NOT a video frame index, and must not be used for video alignment. Gaze runs at about 199.5 Hz. The video starts 132-445 s after the interaction log's `Started` event (021: 445 s, 041: 149 s, 100: 132 s), so the video covers only part of each logged session; 021's 125.8 s video contains only its single station.

**What the video shows (viewed, 6 frames per session).** A single mono render of the headset view, 2048x1536, h264, with a Varjo XR-4 watermark. The station UI (three kiosk cards, Set Amount, Start Charging, Skip, AI Assistant, the keypad dialog) is fully visible and legible at roughly 380 px per kiosk card. The UI is a world-anchored curved panel, NOT head-locked: its pixel position and perspective shift as the head moves (clearly different between 30 s and 60 s in 021), so fixed AOI rectangles in screen space cannot be right for this data. The mouse pointer is visible as an orange arrow, giving a measurable pointer position. Interaction-log events line up with what the frames show (021: Kiosk 1 selected with 25 points at 60 s, `charging` page event at 62.06 s).

**Gaze-to-pixel test (pointer as calibration source, 135 frames: 021 n=54, 041 n=48, 100 n=33; pointer detected by colour).** Literal conventions (signed-normalized, any flips, left or right eye) give 262-492 px median error against the pointer, no better than a constant guess at the median pointer position (183 px). An affine map fitted on 021 only and applied to 041 and 100 without refitting: held-out median error 199 px and 214 px against constant-guess baselines of 322 px and 282 px; but the within-session correlation of gaze x with pointer x is +0.41 (021), +0.56 (041), -0.29 (100), and gaze y with pointer y is -0.52, 0.00, -0.17. At the click moment itself only 3-4 frames per session exist, too few to conclude anything (held-out errors 287 px and 149 px). The pointer is not the gaze point, so this is a weak calibration source, and the fit mostly re-centres an offset rather than demonstrating tracking.

**Left/right disagreement (D030's vergence finding, re-examined).** Across all valid samples, left minus right projected x is a near-constant 0.475 (p5-p95 0.474-0.477 for 021; 0.475-0.481 for 041), and left/right y are identical. It does not vary with depth. Correlation with `focus_distance` is -0.27 (021) and 0.01 (041). `focus_distance` itself is saturated: 97.7% (021) and 77.2% (041) of valid samples equal 2.0, so it carries little depth information.

### Reason
A bounded, 180-frame pilot was the cheapest way to learn whether video can ground-truth AOIs before any bulk extraction; the pointer was used because it is the only on-screen position signal available in every frame, not because it equals gaze.

### Alternatives Considered
(a) Start bulk frame extraction across all 158 videos. (b) Declare the affine fit a success because held-out error beat the constant baseline on 041/100. (c) Locate kiosk panels per frame and report an AOI hit rate in this pilot.

### Why Alternatives Were Not Chosen
(a) 1.47 TB before knowing the mapping works is wasted effort. (b) The error improvement is mostly re-centring (correlations are weak and inconsistent in sign) and the pointer is not gaze; calling it validation would be the overclaim this log's standing rule prohibits. (c) Needs per-frame panel localisation (the panel moves), which was not built in this pilot.

### Implementation
Scripts in `backend/pipeline/video_pilot/` (alignment check, pointer-vs-gaze fit and held-out test, click-window and left/right-offset analysis). Frames and the pointer/gaze pair table stayed in `D:\MTP_scratch\video_pilot` and are not committed.

### Status
Verified (frame timing, gaze-video clock agreement, what the video shows, the constant left/right offset and `focus_distance` saturation). Not validated: any gaze-to-pixel mapping. **Not done**: per-frame localisation of the three kiosk panels and the charge button as pixel rectangles; an AOI hit rate against each participant's true kiosk choice (021 is Kiosk 1, per D026); a fit on actual click events beyond 3-4 frames per session; only 3 participants tested.

### Impact
Weakens D030's diagnosis: the left/right disagreement is a constant per-eye offset, not a depth-dependent one, and `focus_distance` is mostly saturated, so the depth-aware mapping D030 pointed toward is not supported by this column. D021's finding (world-anchored UI needs head pose) is supported: the UI is visibly world-anchored in the video. D026's statement that a 2D calibration might suffice is not supported by this pilot's fit. D030's "NOT SIMPLY FIXABLE" and D025's RQ1 rescoping stand. D031's head-pose logging remains the principled route; this pilot adds that the video itself can supply per-frame panel positions without new data, which is the open option.

### Remarks
Next step if AOI recovery is pursued: locate the panel per frame (template or corner detection on the video) so each gaze sample can be expressed in panel coordinates, and test the gaze-to-pixel map on click events using the interaction log's selection pages. Frame-index alignment must use pts, and the constant 0.475 left/right offset should be understood (likely a per-eye viewport convention) before any mapping is trusted. Open question for the mentor: whether Varjo Base recordings were run with a fixed calibration step.


---

## D061

### Date
2026-10-29

### Decision
Followed D060 by building per-frame kiosk-card localisation for the same three pilot sessions (021, 041, 100) and measuring a gaze AOI hit rate against each participant's true kiosk choice. **Result: NOT validated.** No gaze-to-pixel convention puts the majority of gaze on the true kiosk consistently across the three sessions, and where a convention appears to work (041), time-shifted control gaze does just as well. D060's PARTIALLY verdict is unchanged: labels are recoverable in principle from the video, the gaze mapping is not.

### Context / Problem
D060 left per-frame panel localisation and an AOI hit rate as not done. The UI panel is world-anchored (D060), so any AOI test needs the card positions measured per frame.

### Evidence
**Localisation (measured).** Each frame's Set Amount buttons are found by colour (blue for available kiosks, brown for "in use") and each kiosk card is taken as a rectangle anchored on its own button (width of the button, height 1.85x its width upward, scaled per frame). Only frames with an unambiguous 3-button row are used (brown button only accepted as Kiosk 3, as seen in the 021 and 100 frames): 16 of 54 frames (021), 22 of 54 (041), 8 of 54 (100). The rest are keypad-dialog frames (cards blurred) or frames with a card off-screen, and are excluded, not guessed. Overlays checked by eye on one frame per session: 041's boxes sit well on the three cards; 021's boxes are taller than the real cards and slightly offset. The pointer-in-card check is mixed: 041, pointer inside the true card (K2) in 82% of detected frames; 100, 38% (n=8); 021, 0% in the true card because in the frame inspected the pointer was on the AI Assistant button, outside every card, so that low value reflects where the participant was pointing, not necessarily a localisation fault.

**Hit rate (samples within 0.25 s of each frame; mean of left/right eye projected coordinates; the four x/y flip conventions of the signed-normalized scale).** Share of in-card gaze samples that fall in the true kiosk's card (chance is about 1/3):

| Session (true kiosk) | Frames | Best convention | Share on true card | Time-shifted control gaze |
|---|---|---|---|---|
| 021 (K1) | 16 | any | 0.00 for all four | 0.00 |
| 041 (K2) | 22 | no flip x | 0.67 | 0.41-0.77 |
| 100 (K1) | 8 | no flip x | 0.58 | 0.00-0.07 |

With x flipped, 041 gives 0.53 (controls 0.55-0.58) and 100 gives 0.00 (controls 0.06-0.48). In the last 10 s before the click only 1-3 frames per session qualify (021 0.0; 041 0.72; 100 1.0), too few to read anything into. The "no flip x" convention gets 2 of 3 sessions above chance, but fails 021, the D026/D030 test case, where gaze never lands on Kiosk 1 under any convention (D026's result reproduced independently). 041's apparent success is not specific to gaze timing: gaze shifted by 30 or 60 s scores the same or higher, which is what you would expect if gaze simply rests on the middle card. 100's result beats its controls but rests on 8 frames in which Kiosk 1 is partly off-screen.

### Reason
Time-shifted gaze was added as a control because, with three cards and a gaze distribution that favours the centre, a hit rate above 1/3 on one session could come from card placement alone.

### Alternatives Considered
(a) Report the best convention per session and call the pilot a success. (b) Hand-annotate card rectangles on every frame. (c) Stop at D060 without a hit rate.

### Why Alternatives Were Not Chosen
(a) choosing the best convention per session after seeing the outcome is the fit-then-claim pattern this log rejects, and the controls show why. (b) is a larger manual effort than this pilot's scope and would not change the mapping question. (c) left the AOI question the pilot was meant to answer unmeasured.

### Implementation
`backend/pipeline/video_pilot/p5_panel_localisation_hit_rate.py` (reuses the 162 frames from D060; extracts none; total extracted across D060 and D061 is 180, below the 300 cap). Per-frame results stay in `D:\MTP_scratch\video_pilot\win\aoi_hits.csv`, not committed.

### Status
Verified: the localisation approach works on frames where three buttons are visible; the hit rates and controls are real measurements. Not validated: any gaze-to-pixel mapping. Limitations: 3 participants, 8-22 usable frames each, button-anchored rectangles are approximations of curved cards, the in-use-means-Kiosk-3 assumption was read from only two sessions' frames, and the mapping used the mean of both eyes.

### Impact
Reinforces D030/D060: a fixed 2D mapping from `gaze_projected_*` to video pixels is not reliable for this data. Does not touch D025's RQ1 rescoping. Reproduces D026's 021 failure independently from video, on top of D030's code-based check. The video's usefulness is for per-frame panel position (cheap) and pointer position (cheap); the missing piece is a gaze-to-view mapping that is correct, and no evidence for one exists yet.

### Remarks
Before any larger extraction, the open question is what `gaze_projected_*` is relative to: the constant 0.475 left/right offset (D060) suggests each eye is expressed in its own viewport convention, and the video shows one mono view. Using `gaze_forward`/`gaze_origin` with the render camera's pose (needs head pose, D031) is the principled alternative and is not testable from these files alone. Ask the mentor or check Varjo's documentation for the definition of `gaze_projected_to_*_view`.


---

## D062

### Date
2026-10-29

### Decision
Ran the one bounded test of a different gaze-to-pixel route that D060/D061 had not tried: `gaze_forward` (head-local) through a pinhole model, `u = cx + sx*f*gx/gz`, `v = cy + sy*f*gy/gz`, on the reasoning that the mp4 is rendered from the headset's own viewpoint so head pose is not needed to land in frame pixels. Calibrated on participant 021 only, tested on 041 and 100 without refitting. **Verdict: NOT VALIDATED - the pre-agreed bar (beat the time-shifted controls on held-out participants) was not met.** Under that rule the video-based AOI route is closed for the existing data, with the caveat below that the test was starved of calibration clicks.

### Context / Problem
D060 said the principled alternative to `gaze_projected_*` needed head pose (D031). That was an inference, and it was too strong: a view-relative gaze direction needs only camera intrinsics to reach frame pixels, since the frame already carries head pose. D060/D061 only tested `gaze_projected_*`.

### Evidence
**Calibration data was thin by construction.** Click events recoverable from the interaction log inside the video windows: 8 in total (021: 2, `assistant_chat` and `charging`; 041: 5 `charging`; 100: 1 `charging`). Set Amount and Confirm clicks are not logged. The target for each click is the pointer tip in the frame at click minus 0.2 s (24 new frames, 3 per click; this task's total of new frames is 24, under the 60 cap); gaze is the mean of `gaze_forward` ratios gx/gz, gy/gz over the 300 ms before the click (status==2, stability>0). Assumption: the participant looks at what they click, shortly before clicking. Two clicks give 4 equations for 3 parameters, so the 021 fit is barely determined, not a real calibration. Pointer-tip stability across the three frames is good for most clicks (2-37 px) but 100's single click has a 700 px spread (the detector probably latched onto a different object), and 041's last click has no valid gaze.

**Fit.** Only one sign variant gives a positive focal length with a small residual: sx=+1, sy=-1 (the plain pinhole form), cx=1000, cy=745, f=1449 px, 12 px residual on 021's two clicks. As an inference only: f=1449 px on a 2048 px wide frame corresponds to about 70 degrees horizontal field of view, and the principal point sits near the frame centre (1024, 768), both plausible for a headset render. The three other sign variants fit worse or return a negative focal length. Two points and three parameters mean this agreement could be chance.

**Held-out click error.** 041 (4 clicks): median 213 px, the same as a constant guess at 021's median click position (213 px). 100 (1 click): 158 px against 248 px. The pointer-calibrated secondary fit (54 window frames from 021, assuming gaze tracks the pointer) reaches 157 px train error and 202-209 px held-out, against constant guesses of 345 and 282 px; mapping error is of the order of half a card width (cards are about 309 px wide in these frames), so card hits are sensitive to it.

**AOI hit rate on the true card (share of in-card gaze samples; true | shifted +30 s | -30 s | +60 s | constant guess), click-fit, sx=+1 sy=-1:**
- 021 (K1, calibration participant, not held out): 0.49 | 0.01 | 0.00 | 0.37 | 0.00. Under the other three sign variants it is 0.00. Not a majority on Kiosk 1 (0.49 is below half), but the first time any variant puts roughly half of in-card gaze there, and it beats the 30 s controls; the +60 s control reaches 0.37.
- 041 (K2, held out): 0.61 | 0.64 | 0.15 | 0.90 | constant guess 0.81. Does not beat its controls or the constant guess.
- 100 (K1, held out, 8 usable frames): 0.74 | 0.00 | 0.17 | 0.17 | constant guess 0.00. Beats its controls, but on 8 frames and with the unreliable click above.
The pointer-calibrated variant scores 0.00-0.11 everywhere.

**Localisation versus mapping.** Card boxes come from D061's button-anchored detection; 021's boxes were too tall and offset, which, if anything, flatters 021's hit rate. The held-out pixel errors (158-213 px) are about half a card width, so mapping error alone is large enough to move gaze across card borders; localisation error is an additional unquantified term, so how a miss splits between the two cannot be stated from this data.

### Reason
The camera-model route was the only untested mapping that did not need new data, and it was worth one bounded attempt before closing the question.

### Alternatives Considered
(a) Declare 021's 0.49 and 100's 0.74 a success. (b) Calibrate on all three sessions' clicks to get more points. (c) Keep tuning (distortion, depth) until a variant works.

### Why Alternatives Were Not Chosen
(a) 021 is the calibration participant, 100 rests on one click and 8 frames, and 041, the best-sampled held-out session, does not beat its controls. (b) would remove the held-out test, the only thing that distinguishes a mapping from a fit. (c) is the open-ended tuning the time-box exists to stop.

### Implementation
`backend/pipeline/video_pilot/q1_click_events.py` and `q2_pinhole_gaze_forward.py`; click frames and pair tables in `D:\MTP_scratch\video_pilot` (not committed).

### Status
Verified (the click-event inventory, the fit, held-out errors, and hit rates with controls). Not validated: the pinhole mapping. Under the agreed rule (must beat shifted controls on held-out participants) the bar was not met (1 of 2 held-out sessions, and that one on 8 frames).

### Impact
D026/D030: the plausible-looking pinhole parameters and the 021 result (0.49 on Kiosk 1, vs 0.00 under every `gaze_projected_*` convention in D061) mean the earlier failure is probably in the use of `gaze_projected_*`, not in the gaze data itself; this is suggestive, not shown. D060: its statement that head pose is required is corrected here - not required for frame-pixel landing, still required for world coordinates. D061: unchanged. **The video-based AOI route is closed for the existing data under the agreed rule**, with this caveat: the logged data contain too few click events (2 for the calibration participant) to calibrate a three-parameter camera model, so a larger, better-posed calibration could in principle do better; no further calibration source exists in these sessions. The AOI-free fallback stays the plan, and RQ1 remains a new-data deliverable (D025/D031).

### Remarks
For new collection (Objective 3), a short calibration step at the start of each session (looking at, and clicking, known on-screen targets) would give a camera model the data it needs; this would be cheap with the video capture already running. The 021 result is worth recording as a lead, not a finding.


---

## D063

### Date
2026-10-29

### Decision
Ran the SLM-vs-ML risk-classification comparison (D058's script, `backend/pipeline/compare_slm_classifiers.py`, unmodified) for real on the lab workstation: five local SLMs via Ollama, zero-shot, on held-out GroupKFold fold 0. **No SLM clearly beats the same-fold random forest, and four of the five produce outputs that look close to constant.** This is a single fold with no confidence intervals, so it is a first look, not a ranking.

### Context / Problem
D058 deferred this comparison to the lab PC (GPU, no API quota) and left it as Not Started: the script had only been smoke-tested on 5 rows with one model.

### Evidence
**Setup.** RTX 4090, Ollama 0.40.10; `ollama ps` showed `100% GPU` for the model in use, and each model took about 8 minutes (468-510 s) for 212 rows. Models: `mistral:7b-instruct`, `llama3.1:8b`, `phi3:3.8b`, `gemma2:9b`, `qwen2.5:7b`. Fold 0: 212 test rows, 25 participants, risky rate 0.425. No row failed to parse (parse failure rate 0.0 for every model, all 212 scored). The repo scripts hardcode Mac paths for the feature table and results file, so the run used a wrapper outside the repo that overrides both paths; no repo file was edited for the run. Results were saved outside the repo (`D:\MTP_scratch\slm_comparison_results.json`).

| Model | Balanced accuracy | F1 |
|---|---|---|
| RandomForest, same fold (fresh fit on the other 4 folds) | 0.5818 (AUROC 0.6948) | 0.4118 |
| Majority-class baseline | 0.5000 | 0.0000 |
| `llama3.1:8b` | 0.5595 | 0.4606 |
| `phi3:3.8b` | 0.5190 | 0.6034 |
| `qwen2.5:7b` | 0.5029 | 0.0426 |
| `mistral:7b-instruct` | 0.5000 | 0.5960 |
| `gemma2:9b` | 0.5000 | 0.0000 |

**Near-constant outputs (inferred from the metrics; per-row predictions were not saved).** At a risky rate of 0.425, answering "risky" every time gives F1 of about 0.597 and balanced accuracy 0.5; `mistral` (0.5000 / 0.5960) and `phi3` (0.5190 / 0.6034) sit at or very near that point. `gemma2` (0.5000 / 0.0000) matches always answering "not risky", and `qwen2.5` (0.5029 / 0.0426) is almost that. `llama3.1` is the only model that does not look constant (F1 0.4606, below the all-risky value) and has the highest SLM balanced accuracy, 0.5595.

**How much 0.5595 means.** With 212 rows from 25 participants and no interval reported, 0.5595 versus 0.50 is within the noise to be expected from a single fold; the script reports no standard error, and none was computed here. The forest's 0.5818 is likewise one fold and sits within this project's earlier cross-fold spread (D050's 5-fold figures, not restated here).

### Reason
The point of the run was to see whether zero-shot SLMs, given the same features, can substitute for or compete with the deployed ML model on identical held-out rows. On this fold they do not, and most appear not to be using the features at all.

### Alternatives Considered
(a) Report llama3.1's 0.5595 as the best SLM and move on. (b) Re-run on all five folds before logging anything. (c) Add few-shot examples or reasoning prompts to coax discrimination out of the models.

### Why Alternatives Were Not Chosen
(a) would imply a ranking one fold cannot support. (b) is a reasonable next step but a larger run (about 40 minutes per fold) than this task asked for. (c) departs from the script's deliberate "simplest possible prompt" design (D058), so a result would no longer be comparable to what D058 specified.

### Implementation
No repo code changed by the run. This entry only. (The hardcoded-path fix is a separate commit.)

### Status
Verified for what was run: fold 0, one zero-shot prompt per model, 212 rows each. Not established: any ranking among the SLMs, any comparison across folds, any statement about few-shot or fine-tuned SLMs. The near-constant behaviour is inferred from summary metrics, not observed in saved predictions.

### Impact
Objective 2 (the SLM comparison table requested in D058): first real numbers now exist, with the caveats above. Does not change the production design: the SLM still only phrases a decision the ML model makes (D055/D057). Does not change D050's cross-fold baseline or D057's calibrated thresholds.

### Remarks
To make this comparison citable: save per-row predictions, run all five folds, report intervals, and add the positive-prediction rate per model so near-constant behaviour is visible directly. The video-feature extension noted in D058 does not exist yet (D059-D062 found the video usable but not for AOI mapping).


---

## D064

### Date
2026-10-29

### Decision
Adopted a gated research protocol (Gate 0 audit, Gate 1 protocol freeze, then analysis gates) and completed **Gate 0: a read-only repository and data audit**, written up in `docs/audit/GATE0_audit.md`. No model was trained and no repository code was changed during this gate. Gate 1 (protocol document only) starts only after explicit approval.

### Context / Problem
After D058-D063 the project had many post-hoc results on the same participants, a standing label history (D045), several unverified headline numbers, and no stated prediction timestamp or locked test set. The brief asked for an audit that treats earlier documentation as claims to verify.

### Evidence
Raw-recomputed, independent of the pipeline: 139 session folders for 132 participant ids; the feature table (1,123 rows, 126 participants) reproduced exactly from raw logs; label normalisation verified (logged attack agrees with the layout's attack flag in 815/815 charge events); decision-level risky base rate 34.73%, participant-level 88.9% with at least one risky decision; 67 EEG-qualified participants confirmed. New findings: risky rate depends on randomised kiosk exposure (0.0/26.5/61.5/67.1% for 0/1/2/3 attacked kiosks); the existing behaviour-only AUROC (about 0.67) is close to the skip-vs-charge ceiling (0.715); gaze features are near chance among charge decisions (descriptive AUROC 0.49-0.52); the in-game assistant is a recommendation engine and neither its responses nor its condition are logged; 25 hardcoded Mac paths remain in 13 files. Not reproduced: "~49 positive participants".

### Alternatives Considered
(a) Continue iterating on the existing ablation tables. (b) Start Gate 1 in the same step. (c) Fix the label/target and the Mac paths immediately.

### Why Alternatives Were Not Chosen
(a) The tables answer a different question than stated (charge vs skip, confounded with exposure). (b) The brief requires approval between gates. (c) Code changes are out of scope for Gates 0 and 1; the target redefinition is a Gate 1 decision.

### Implementation
`docs/audit/GATE0_audit.md` (new). No code, data or model files changed.

### Status
Gate 0 complete; awaiting approval. Part of Decision.md D001-D044, the Research Audit PDFs, several `check_*` scripts and the demographics files were not reviewed in this gate.

### Impact
Reframes earlier results as preliminary or invalid for modality claims (D037, D045-D057, D063 for the question asked) without editing those entries; narrows the primary question to behaviour vs behaviour+gaze within charge decisions with exposure accounted for, pending Gate 1.

### Remarks
Earlier entries are not edited. This entry supersedes none of them; it adds a verification layer. Wording rule going forward: "associated with" and "predictive of", never causal.


---

## D065

### Date
2026-10-29

### Decision
Drafted Protocol v1 (`docs/protocol/PROTOCOL_v1.md`) for approval, as Gate 1 of the gated research protocol (D064). **The primary target is redefined to control for exposure:** among charge decisions at informative stations (at least one attacked and one safe available kiosk), whether the participant chose an attacked kiosk, with `logit(attacked share of available kiosks)` as an offset in every model. The single primary hypothesis is B+exposure vs B+G+exposure (six AOI-free gaze features). The legacy `risky` label is kept only as an exploratory secondary outcome. Documents only: no training, no code change.

### Context / Problem
Gate 0 (D064) showed the legacy `risky` target is dominated by randomised exposure and by whether the participant charged at all. You approved Gate 1 and answered: ignore the "~49 positive participants" question for now; redefine the primary target to control for exposure; use the recommendations for the remaining open questions (exclusion rules E1-E6, config-driven paths and a run registry in later gates, treat all existing-data results as exploratory, consider new data for confirmation).

### Evidence
Read-only counts from raw logs: 516 charge decisions at informative stations (115 participants, 233 attacked-kiosk choices, 45.2%); 492 with gaze (112 participants, 220 events); 150 with gaze and EEG (49 participants, 70 events); 87 of 115 participants have both outcomes; residual intraclass correlation after exposure 0.000 (imprecise at a median of 4 rows per participant); descriptive AUROC 0.659 for the exposure offset alone and 0.790 for the visible image type of the chosen kiosk (the decision itself, so not a feature). Approximate planning figures: detectable odds ratio about 1.29 per SD for one predictor on the primary set, about 1.58 on the matched EEG set; detectable paired ΔAUROC about 0.03-0.04 and 0.07-0.10 respectively (assumption: correlated predictions).

### Alternatives Considered
(a) Keep the legacy `risky` target and add exposure as a covariate. (b) Model kiosk choice directly (conditional logit over available kiosks). (c) Predict participant-level vulnerability.

### Why Alternatives Were Not Chosen
(a) leaves the skip/charge component inside the label, which made the earlier AUROCs a skip-vs-charge artifact. (b) is a good later extension but needs per-kiosk cues and more modelling choices than the single pre-specified comparison allows. (c) discards the repeated-decision information; most participants have several informative decisions.

### Implementation
`docs/protocol/PROTOCOL_v1.md` (new). Nothing else changed.

### Status
Draft, awaiting approval; not frozen. Freezing records the protocol's commit hash in the registry. Estimation engine for the mixed model is undecided (R is not installed here).

### Impact
Replaces the legacy target as the primary one for Gates 2-7 if approved. Does not edit D045-D064. The earlier ablations remain on record as answers to a different question.

### Remarks
The protocol is not blind: the redefinition and the primary test were chosen after Gate 0 showed near-chance gaze signal among charges. All existing-data results will be labelled exploratory with respect to that choice; only new data could be confirmatory.


---

## D066

### Date
2026-10-29

### Decision
Froze Protocol v1 at the commit that introduced it. Approved by you for Gate 2 on 2026-10-29 with no changes. Freeze record: commit `58e59c0e5fd2dc1cdd647336363984f349457ec7` (`docs(protocol): add Protocol v1 draft for Gate 1 approval`), git blob `552107deaaad9b413aef8d125bf62bac3b7c199d` for `docs/protocol/PROTOCOL_v1.md`, SHA-256 of the working-copy file `D1D4234B4162B0FE48BD7A9369D50DADAC97E51C4AF4C8915C27E42BB8C92718` (LF line endings), local annotated tag `protocol-v1` on that commit (not pushed).

### Context / Problem
The gated protocol requires the analysis plan to be fixed before any Gate 2 modelling, so later results cannot be adjusted to the analysis. D065's statement that freezing records the protocol commit hash in the experiment registry stands; the registry does not exist yet, so the hash is recorded here and will be copied into the registry when it is created.

### Evidence
The file has not changed since commit 58e59c0 (`git log` for the path shows that commit as the latest). Later commits touch only Decision.md.

### Alternatives Considered
(a) Freeze at the later D065 commit. (b) Freeze without a tag, by hash only.

### Why Alternatives Were Not Chosen
(a) That commit changes only Decision.md, so the protocol-bearing commit is the cleaner anchor. (b) A tag gives a verifiable pointer that survives later history; the hash and blob id are recorded as well.

### Implementation
Tag `protocol-v1` created locally; this entry only. No push.

### Status
Frozen. Any deviation is logged as a new entry referencing D066, not by editing the protocol.

### Impact
Gate 2 runs only what the frozen protocol specifies for H1 (B+exposure vs B+G+exposure).

### Remarks
Estimation engine for the mixed model is not part of the frozen text (the protocol leaves it to Gate 2); the choice is recorded as its own entry.


---

## D067

### Date
2026-10-29

### Decision
Chose the estimation engine for the primary mixed model (option B: an in-repo Python implementation of random-intercept logistic regression by Gauss-Hermite marginal maximum likelihood; R was not installed) and ran Gate 2, the primary analysis of Protocol v1 (frozen in D066). **Result: H1 is not supported.** Claim A (6-df likelihood-ratio test of the gaze block beyond exposure, design covariates and behaviour): chi-square 8.17, p = 0.226 (participant-block permutation p = 0.387). Claim B (paired out-of-sample AUROC, B+G minus B): +0.005, 95% participant-bootstrap CI [-0.006, +0.015], permutation p = 0.49. By the protocol's rule: no evidence that gaze adds to behaviour for this target at this sample size. Full report: `docs/analysis/GATE2_report.md`.

### Context / Problem
D066 froze the protocol with the engine left open. You chose option B plus installation of statsmodels, PyYAML and pytest into the project's Windows virtual environment (pytest pinned below version 9, which crashed on this Python 3.10.0rc2); R was skipped.

### Evidence
Engine validated by 22 passing tests: agreement with statsmodels and with ordinary logistic regression when the random-effect variance is fixed near zero, analytic-gradient check, quadrature convergence, simulation recovery of known parameters, near-nominal Type-I error and good power of the LRT, boundary behaviour. The analysis table reproduces the Gate 1 counts (492 rows, 112 participants, 220 events). Runs are in `results/registry.csv` (code commit 5672700, clean tree). The random-intercept variance is estimated at zero in every fit, so mixed and ordinary logistic regression agree. Sensitivity analyses: E2 p = 0.31, S4 p = 0.33, **S3 (drop RAG-contaminated sessions) p = 0.019**, a nominally significant exploratory lead on a 77-participant subset, not pursued here. In nested CV the inner loop chose the smallest C in the grid in 95-99% of folds, so predictions of B0, B and B+G are almost identical.

### Alternatives Considered
(a) R `lme4` as the primary engine; (b) R as an additional one-time cross-check; (c) statsmodels GEE/variational mixed model only.

### Why Alternatives Were Not Chosen
(a) and (b) need a second language and several GB of installs; the data show no detectable clustering, so the mixed model coincides with ordinary logistic regression and an in-repo, tested engine is sufficient. (c) does not give a maximum-likelihood random-intercept test as the protocol specifies.

### Implementation
`backend/pipeline/gate2/` (engine, config loader, table builder, grouped CV with bootstrap and permutation, registry, H1 runner, 22 tests), `configs/gate2_h1.yaml` (seeds fixed before running), `results/registry.csv` plus run summaries (row-level artifacts and analysis tables are gitignored), `docs/analysis/GATE2_report.md`.

### Status
Gate 2 complete; awaiting approval for Gate 3. The feature table is still a committed artefact: `build_feature_table.py` keeps its Mac paths and was not changed. S2, S1, S5-S8, EEG, model grid and threshold-based metrics are not run.

### Impact
D052's gaze association is not supported once exposure is offset and the skip/charge path removed. Earlier D037/D045-D057 ablations remain answers to the legacy target. No change to D060-D062 (AOI route closed).

### Remarks
S3 must not be chased on these participants (a data-driven fork); a confirmatory check would need new data under a pre-specified analysis. The narrow Claim B interval reflects heavy shrinkage, not proof that small effects were excluded for unpenalised models.


---

## D068

### Date
2026-10-29

### Decision
Ran Gate 3 (ML benchmark) of Protocol v1 and generated the master comparison table programmatically from the experiment registry. **No pre-specified model or modality set beats the exposure-only reference B0 on T1** (primary set: 492 rows, 112 participants, 220 events; all paired CIs against B0 span zero or are negative; ridge B+G minus B reproduces the Gate 2 null at +0.004 [-0.006, +0.015]). S1 (gaze alone vs exposure baseline): LRT p = 0.253, delta AUROC +0.006 [-0.005, +0.017]. S2 (H1 with the first 5 s only): LRT p = 0.590, delta AUROC -0.002 [-0.011, +0.007]. Exploratory S8: random forest is worse than ridge when behaviour or gaze is added (delta AUROC -0.022 to -0.039, FDR about 0.03-0.04). The XGBoost/LightGBM challenger was not run (entry criterion not met). Report: `docs/analysis/GATE3_report.md`; tables: `results/master_table_gate3.md`.

### Context / Problem
You approved Gate 3 with S1 and S2 and a programmatically generated master table. The frozen protocol left several details open for this gate.

### Evidence
Registry runs `g3_grid_ridge/rf/hgb`, `g3_secondary_S1/S2`, `g3_exploratory_S8` (code commit dca9470; dataset hash recorded). 28 tests passed before the runs (engine, table, CV, benchmark machinery). Ridge results equal Gate 2's. Hyperparameter selection sat at the weakest end of the grid for ridge (95-99% at C = 0.01) and boosting (98-100% for sets B, G, BG). At the recall-0.80 operating point the false-warning rate is 0.59-0.61 for ridge on every set and 0.60-0.74 for tree models.

### Alternatives Considered
(a) Extend the grids after seeing the boundary selections; (b) run XGBoost/LightGBM anyway; (c) add the tree-model permutation tests; (d) define operating point B literally as the smallest threshold reaching recall 0.80.

### Why Alternatives Were Not Chosen
(a) and (b) would be post-hoc tuning of a null result, and the protocol allows the challenger only if a pre-specified model beats B0. (c) is outside the pre-specified set for this gate. (d) the literal smallest threshold predicts almost every case as positive, so the implemented reading is the largest threshold that still reaches recall 0.80 (stated in the config before the run).

### Implementation
`configs/gate3_grid.yaml` (written and committed first, filling the grids, the operating-point interpretation, Holm family and S2 definition); `backend/pipeline/gate2/{benchmark,early_window,run_gate3,master_table}.py`; tests; registry rows and run summaries (row-level artifacts and tables are gitignored); `results/master_table_gate3.md` and `_long.csv`; `docs/analysis/GATE3_report.md`.

### Status
Gate 3 complete; awaiting approval for Gate 4 (EEG, matched subset, exploratory). Holm adjustment for S1/S2 is provisional at family size 4 (S5 and S6 pending); both unadjusted p-values exceed 0.25 so the upper bounds are 1.0. No operating point is validated.

### Impact
Reinforces D064/D067: no evidence that behaviour or gaze improves prediction of the choice of an attacked kiosk beyond layout exposure. Supersedes earlier ablations (D037, D045-D057) as evidence about modality value on this target.

### Remarks
The master tables are the reference for numbers; the report quotes headline figures only. The unadjusted tree-model deficits (S8) are exploratory and grid-limited. The grid-boundary selections suggest the problem lacks signal beyond the offset, not that wider grids would fail; that was not tested.


---

## D069

### Date
2026-10-29

### Decision
Ran Gate 4: the selection-bias report and S6 (EEG, exploratory) on the matched EEG set. **No EEG claim is supported.** On identical rows (150 rows, 49 participants, 70 events) EEG added to behaviour + gaze changes ridge AUROC by +0.031 [-0.013, +0.070] (participant-block permutation p = 0.22; descriptive 17-df LRT p = 0.027, provisional Holm upper bound 0.11). The EEG rows are a biased subset: 41.1% of the decision windows of participants with synchronised recordings fall after the EEG recording ended, so EEG comes from earlier stations (median trial 3 vs 8; SMD -0.53 [-0.83, -0.29]) and the April-heavy period (49% vs 22%, FDR 0.012); outcome rate, exposure, window duration, gaze quality and demographics show no detected difference. Report: `docs/analysis/GATE4_report.md`; tables `results/master_table_gate4.md` and `results/selection_bias_gate4.md`.

### Context / Problem
You approved Gate 4 for B, B+G and B+G+EEG on the identical matched set plus the selection-bias report. The frozen protocol did not specify the S6 test statistic, the permutation strata for the EEG block, or the handling of the 17-column block at 70 events.

### Evidence
Matched set reproduced the pre-specified counts (150 / 49 / 70, no missing EEG values). Registry runs `g4_selection_bias`, `g4_s6_ridge/rf/hgb` (code 13b06c7). Primary contrast and permutation as above; operating-point false-warning rates at recall 0.80 are 0.61-0.64 for every set. Random forest and boosting fall to chance on the matched set (AUROC 0.49-0.55 for B, BG, BGE, vs 0.60-0.62 for B0). Post-hoc diagnostic (not pre-specified): 17 pure-noise columns raise ridge CV AUROC by +0.006 on average (SD 0.014). Canonical session and EEG session link agree for all participants.

### Alternatives Considered
(a) Treat the 17-df LRT as the primary S6 test; (b) reduce the EEG block to a few features chosen after inspecting the data; (c) run S6 on all rows with imputed EEG; (d) weight the matched set to resemble the full set.

### Why Alternatives Were Not Chosen
(a) 17 parameters on 70 events is unreliable; the CV contrast with a permutation test is primary and the LRT is labelled descriptive. (b) and (c) would be forks or would invent data; imputing EEG for rows that lack the recording is not defensible. (d) would add modelling choices on an already underpowered set.

### Implementation
`configs/gate4_eeg.yaml` (committed first), `backend/pipeline/gate2/{matched,selection_bias,run_gate4,master_table}.py`, tests, `backend/pipeline/gate2/diagnostics/g4_noise_columns.py` (post-hoc diagnostic), registry rows and run summaries, generated tables, `docs/analysis/GATE4_report.md`.

### Status
Gate 4 complete; awaiting approval for Gate 5 (SLM benchmark: the labelled scenario set is built and shown to you first, then the identical-condition benchmark). The Holm upper bounds remain provisional (S5 pending). The EEG results are exploratory and descriptive.

### Impact
Reinforces D064-D068: no modality (behaviour, gaze, EEG) shows a detectable improvement over layout exposure for the choice of an attacked kiosk. Refines D019/D050's EEG story: the usable EEG subset reflects early-session windows and the earlier collection period. Does not edit earlier entries.

### Remarks
Further EEG analysis on these participants would be a data-driven fork; a clean EEG test needs a new collection with whole-session recording and trial position controlled. The limited power (differences below about 0.06 AUROC are indistinguishable from zero) is a property of the subset, not evidence that a larger effect would be absent.


---

## D070

### Date
2026-10-29

### Decision
Built the Gate 5 SLM scenario set (Protocol v1 section 9) and **stopped for your approval before any model is run**. The set has 240 stations (40 benign, 40 all-attacked, 160 mixed) and 599 available kiosks, quota-sampled from the logged station layouts of 106 sessions (at most 3 stations per session, seed 20261029). Ground truth is simulation metadata only (each kiosk's attack flag and attack mode). Every visible-cue class has at least 41 kiosks and each hidden attack mode at least 65 (requirement 30). Evidence is given in two variants: V1 cue-free, V2 with the game's own automated screenshot descriptions of the coupon images. Approval document: `docs/protocol/GATE5_scenario_set.md`.

### Context / Problem
You approved Gate 5 with the instruction to build the labelled scenario set first and show it before any model run. The brief's class "overcharging" does not exist in the game metadata (attacks reduce or block the delivered charge), and the SLMs are text-only.

### Evidence
Build is deterministic from `configs/gate5_slm.yaml`; four tests pass (inputs and truth aligned, quotas met, model inputs contain no attack/safe/image-type words or identifiers, every shown image has a description). Non-model reference rules on the set: always SAFE 51.4% accuracy, discount-badge rule 51.9%, deepfake-image-type rule 73.3% (79% across all logged kiosks; lower here because ambiguous classes are over-sampled), recommendation by chance avoids an attacked kiosk 51.5% of the time at mixed stations. One image description (deepfake1) contains an explicit "DEEPFAKE" label, a giveaway in V2. 60 of the 240 stations show no coupon image, so V1 and V2 coincide there.

### Alternatives Considered
(a) Add synthetic overcharging scenarios; (b) include a history variant (earlier-station outcomes as the deployed assistant sees them); (c) sample stations at random without quotas; (d) use the stronger override wording for the malicious condition.

### Why Alternatives Were Not Chosen
(a) The protocol requires ground truth from simulation metadata, and overcharging is not in it; offered as an option, not done. (b) Outside the protocol's V1/V2 design; offered as an option. (c) Random sampling would leave rare classes (ambiguous safe deepfake kiosks are about 8% of kiosks) with too few cases. (d) The original (D024) wording is the baseline; the stronger wording is offered as a separately reported second condition.

### Implementation
`configs/gate5_slm.yaml` and `configs/gate5_prompts.yaml`; `backend/pipeline/gate5/{build_scenarios,scenario_report}.py` with tests; `scenarios/slm_v1/` (inputs, truth, image descriptions, manifest, 20 synthetic format-pilot prompts); the private session map is under the gitignored results folder. No Ollama call was made.

### Status
Awaiting approval. Decisions needed from you: approve or change the composition; overcharging (recommend drop); malicious wording (recommend original); evidence variants (recommend V1 and V2 only); decoding design; approval of the 20-prompt format pilot, which is the first step that would call a model.

### Impact
None yet on results. Defines the only data the SLM track will use; the D063 comparison (which gave models post-hoc behaviour/gaze numbers, no kiosk information) is not reused.

### Remarks
Per-class results are the unit of interpretation; overall accuracy on this quota-sampled set is not a population estimate. The hidden attack modes (reduced, blocked) are consequences after charging, so recall by hidden mode measures recall on attacked kiosks with the visible cues they happen to have, not recognition of the mode itself.

---

## D071

### Date
2026-10-29

### Decision
Logged a **protocol deviation**: the Gate 5 format pilot (20 prompts x 5 models) and the Gate 5 accuracy pass were started without an approval on record. Nothing was rerun. The accuracy pass was left to finish and no accuracy output has been interpreted or scored.

### Context / Problem
D070 ends with "Awaiting approval" and lists decisions needed from you: scenario composition, dropping overcharging, malicious wording, evidence variants, decoding design, and approval of the 20-prompt format pilot "which is the first step that would call a model". No later Decision.md entry, commit, or file in the repository records an approval of (a) the scenario set as built or (b) the accuracy pass. The repository cannot show whether approval was given in chat; if it was, it is not recorded here.

### Evidence
Timeline from file timestamps and commits (all 2026-10-29, local time): scenario set committed 14:40 (D070, "awaiting approval"); pilot outputs written 14:46 to 14:50 (`results/_slm/pilot/`, 5 models x 20 calls); `run_slm.py` last modified 14:51; accuracy pass started 14:51 (`run_slm accuracy`, processes 38196 and 45632); `score_slm.py` and `master_table5.py` written 14:52, after the pass started and before any scoring spec exists. `docs/protocol/GATE5_scoring_spec.md` does not exist. At 14:59 the pass had finished mistral:7b-instruct (960 calls) and llama3.1:8b (960 calls) and was part-way through phi3:3.8b (22 of 960); gemma2:9b and qwen2.5:7b were still to run. Accuracy-pass settings in the stored rows: temperature 0.0, seed 1. The 5-seed consistency run at temperature 0.3 has not been started. `run_slm.py`, `score_slm.py`, `master_table5.py` and `results/_slm/` are uncommitted; three tracked files differ only by a removed byte-order mark.

### Alternatives Considered
(a) Kill the running pass; (b) delete the outputs and restart after approval; (c) let it finish and hold interpretation until the scoring spec is committed.

### Why Alternatives Were Not Chosen
(a) and (b) destroy raw replies and do not remove the deviation. (c) keeps every raw reply as evidence and keeps the decision about how to treat the run with you.

### Implementation
No code or data changed. This entry only.

### Status
Open. Needs from you: confirm whether you approved the scenario set and the accuracy pass (and the pilot) in chat; if not, say whether the pass counts or should be rerun after approval. Gate 5 results stay uninterpreted until `GATE5_scoring_spec.md` is committed (Step 1).

### Impact
Raw replies exist and are intact. Because `score_slm.py` was written after the pass started and the replies were readable, its parsing rules were not provably fixed before outputs existed. I did not run it and did not read reply contents beyond one row's format. Any later scoring must say this.

### Remarks
Not tuned on any result: no scorer has been run, and no accuracy number has been looked at.


---

## D071

### Date
2026-10-29

### Decision
Recorded your approval of the Gate 5 scenario set (D070) and started the SLM benchmark. **Approved as built:** the 240-station set; overcharging dropped; the original (D024) malicious wording; evidence variants V1 and V2 only; the 20-prompt format pilot, then the benchmark. The format pilot was run on the five installed models (`mistral:7b-instruct`, `llama3.1:8b`, `phi3:3.8b`, `gemma2:9b`, `qwen2.5:7b`) under the approved prompts and decoding (temperature 0, seed 1, 64 output tokens, context 4096). **All five passed the 90% instruction-following threshold:** llama3.1, gemma2 and qwen2.5 had 20 of 20 compliant replies; mistral and phi3 had 19 of 20 (one missing-kiosk-key failure each). No model is flagged.

### Context / Problem
D070 left the set awaiting approval and listed five choices. The benchmark harness stores every raw reply and scores later, so no metric is computed while a model runs.

### Evidence
Pilot replies in `results/_slm/pilot/` (gitignored); compliance per model as above (Wilson 95% for 19/20: 0.76-0.99; for 20/20: 0.84-1.00). GPU memory added when a model loads (peak minus the baseline just before loading, with desktop applications already using about 5.2 GB): phi3 about 4.1 GB, qwen2.5 5.1, mistral 5.4, llama3.1 5.5, gemma2 7.1. The pilot's per-call wall time (about 2.5 s) was inflated by about 2 s of client overhead (the hostname `localhost` resolves slowly here); the server-side durations were about 0.54-0.62 s. The benchmark uses `127.0.0.1`; the pilot replies are unaffected, only their wall-clock timing.

### Alternatives Considered
(a) Re-run the pilot after the address fix; (b) run the consistency pass on a subset of stations; (c) run the models in parallel to save time.

### Why Alternatives Were Not Chosen
(a) The pilot only checks format compliance, which does not depend on timing; latency and VRAM are measured in the accuracy pass instead. (b) Not decided yet: the full consistency pass (5 seeds, temperature 0.3, all 960 items per model) will be run unless throughput measured in the accuracy pass makes it impractical; if a subset is needed it will be chosen by scenario id before any result is scored, and logged here. (c) Sequential calls are needed for clean latency in the accuracy pass; only the consistency pass may use parallel workers, and its timings are not reported.

### Implementation
`backend/pipeline/gate5/run_slm.py` (harness with resume, VRAM sampling and latency capture); scoring and table generation to follow once all passes finish. The accuracy pass over all five models was started after the pilot (960 calls per model: V1/V2 x detection/recommendation x 240 stations).

### Status
Pilot complete and passed. Accuracy pass running; malicious-condition pass and consistency pass pending; scoring, master table and report pending.

### Impact
None on earlier results. SLM results will be reported in a separate track and never ranked against the ML models.

### Remarks
The single failure in mistral's and phi3's pilot replies is a missing kiosk key (an available kiosk left out of the JSON), counted as a failure under the approved parsing rule rather than repaired.


---

## D072

### Date
2026-10-29

### Decision
Completed the accuracy pass (temperature 0, seed 1: 960 calls per model) and the malicious-condition pass (120 calls per model) for all five models, and **started the full consistency pass** (temperature 0.3, seeds 1-5, all 960 items per model, 4,800 calls per model, 3 parallel workers). No subset is used: the sequential throughput measured in the accuracy pass (0.23-0.44 s per call) made the full pass practical, so the contingency in D071 (a subset chosen by scenario id) was not needed. Consistency timings are not reported (parallel workers); latency and GPU memory come from the sequential accuracy pass.

### Context / Problem
D071 recorded the approval and the pilot. The accuracy pass ran sequentially per model with GPU memory sampled every 0.5 s; the malicious pass followed; the consistency pass runs in the background.

### Evidence
Accuracy-pass runtime: mistral 223 s, llama3.1 248 s, phi3 322 s, gemma2 421 s, qwen2.5 263 s. GPU memory added by loading a model (accuracy pass, baseline about 5.2 GB used by desktop applications): mistral 5.3 GB, llama3.1 5.5, phi3 4.3, gemma2 7.1, qwen2.5 5.2. In the malicious pass the baseline memory in use was about 10 GB (another process held GPU memory), so those VRAM figures are not used. A preliminary, unscored-in-the-report look at the stored replies (the pre-specified scoring code run once to test it, while the consistency pass was running) showed: detection accuracy 0.50-0.59 for every model and variant, below the deepfake-image-type reference rule (0.73); V1 false-safe rates of 0.65-0.99 and V2 false-warning rates of 0.35-0.73; mistral V2 had 66 of 240 detection replies failing the format rules; recommendation safe-choice 0.37-0.65 (random choice 0.51); every model followed the malicious override in 98-100% of replies against 25-45% target choice without it. These numbers are provisional until the final scoring step and no design choice was changed because of them.

### Alternatives Considered
(a) Run the consistency pass on a subset; (b) pause until scoring; (c) change the prompt or parsing after seeing the failures.

### Why Alternatives Were Not Chosen
(a) Not needed given measured throughput. (b) The scoring code is deterministic and pre-specified; waiting would not change what is scored. (c) Prompts, parsing and scoring are frozen by the approval in D070/D071; failed replies are counted, not repaired.

### Implementation
`backend/pipeline/gate5/run_slm.py` (committed); `score_slm.py` and `master_table5.py` (registration and the master table) written and pending the final scoring step; raw replies under `results/_slm/` (gitignored).

### Status
Accuracy and malicious passes complete; consistency pass running; final scoring, registry rows, master table, Gate 5 report and the closing decision entry pending.

### Impact
None on ML results. The SLM track stays separate and is never ranked against the ML models.

### Remarks
The malicious-condition numbers show that a single instruction line makes all five models recommend an attacked kiosk, which is a property of the instruction-following behaviour tested here, not evidence about human responses to a manipulated assistant.

---

## D072

### Date
2026-10-29

### Decision
Ran a **deliberately reduced Gate 6**: descriptive coefficients and an error analysis of the exposure-only reference B0 only. Did not run SHAP or permutation importance. Exploratory and descriptive; no hypothesis test.

### Context / Problem
Protocol v1 allowed interpretability for the selected model. No model beat B0 in Gate 3 (D068) and the SLM track is separate (D070/D071), so interpretability of a model without signal would describe noise. You approved Step 1 and asked for the reduced Gate 6.

### Evidence
Primary set 492 rows, 112 participants, 220 events. B0 covariates are all null (unpenalised odds ratios 0.92 to 1.18, intervals spanning 1); free exposure slope 1.10 [0.68, 1.52]. Observed attacked-choice rate 0.447 vs 0.493 expected from exposure alone (difference -0.046 [-0.088, -0.004], participant bootstrap). B0 is calibrated overall and by number of attacked kiosks, trial index bin and collection period (all intervals include zero). Reproduced the Gate 3 B0 out-of-fold AUROC (0.628 vs 0.627 in D068) before using it.

### Alternatives Considered
(a) SHAP or permutation importance for the best-looking Gate 3 model; (b) skip Gate 6 entirely.

### Why Alternatives Were Not Chosen
(a) The best-looking model (ridge with gaze) is statistically the same as B0, so its importances would be noise. (b) The descriptive B0 analysis is cheap, adds the exposure-slope and stratum calibration checks, and records the reduction explicitly.

### Implementation
`configs/gate6_descriptive.yaml` committed before the run; `backend/pipeline/gate6/descriptive_b0.py`; outputs `results/gate6_tables.md`, `results/gate6_meta.json`, `results/_tables/gate6_*.csv`. The Gate 3 out-of-fold B0 predictions were reused (not refitted); the final ridge fit uses C = 0.01 chosen by the Gate 2/3 inner rule on all rows.

### Status
Complete; report is `docs/analysis/GATE6_report.md` (Part 1). Step 3 analyses follow.

### Impact
None on earlier results. Adds descriptive context only.

### Remarks
Several strata were examined without multiplicity control; the three intervals that exclude zero (all rows, one attacked kiosk, April) are one signal at three levels and are not findings.

---

## D073

### Date
2026-10-29

### Decision
Ran S5 (skip vs charge) framed relative to exposure, exploratory, same 5 x 20 nested participant-grouped CV, same ridge grid and bootstrap as Gates 2-3. Main set: mixed stations as in protocol v1 (667 rows, 118 participants, 175 skips). Extension: all stations with benign and all-attacked indicators (1,057 rows, 280 skips), exploratory and outside the Holm family. Holm family stated and now complete: {S1, S2, S5, S6}.

### Context / Problem
Gate 0 showed the legacy risky label mixes exposure with the choice to charge. In all-attacked stations a skip is protective; in benign stations it is over-cautious. You asked for S5 framed against exposure.

### Evidence
Descriptive: skip rate is 29.7% [23.7, 36.5] at benign, 28.2% [25.1, 31.6] at mixed and 25.9% [20.5, 32.2] at all-attacked stations; it barely tracks exposure. Models: B0 (exposure and design only) AUROC 0.50 [0.46, 0.55]; B 0.884 [0.845, 0.917]; B+G 0.889 [0.850, 0.921]; B+G minus B +0.005 [-0.007, +0.017], paired p 0.40. LRT for the six gaze features (B+G vs B): chi-square 18.5 on 6 df, p 0.0050, permutation p 0.015. Extension: B+G minus B +0.002 [-0.006, +0.009]; LRT p 7e-5. Holm at family size 4: S5 0.020, S6 0.082 (descriptive LRT), S1 0.507, S2 0.590.
Diagnostic (post-hoc, descriptive): window duration alone separates skip from charge with AUROC 0.887 (median 4.9 s for skips, 16.4 s for charges), and gaze fixation count alone with 0.864. The window ends at the decision event, so a skip (leaving) is mechanically short.

### Alternatives Considered
(a) Treat the LRT result as a finding; (b) drop window duration and gaze counts and refit; (c) report with this caveat and run nothing more.

### Why Alternatives Were Not Chosen
(a) The B covariates are outcome-adjacent, and the discrimination gain from gaze is +0.005 AUROC; a significant LRT with a negligible gain is not evidence that gaze helps decisions. (b) A second model family on the same rows would be a further unplanned analysis, and the decision to drop covariates would be made after seeing the leakage. Offered, not done.

### Implementation
`configs/gate6_extra.yaml` and `backend/pipeline/gate6/extra.py` (committed 50b1ce2 before the run); registry run `g6_s5_skip_vs_charge_20261029_153804_940237`; `results/gate6_s5.json`.

### Status
Complete, exploratory. S5 passes Holm numerically (0.020) but must not be reported as a gaze effect (see Remarks).

### Impact
Completes the Holm family. S5's apparent signal is the only adjusted p-value below 0.05 in the project and is explained at least in part by a mechanical relation between window length and the outcome.

### Remarks
Skip vs charge cannot be separated from time-to-decision with the current logs. The next data collection should log the decision latency separately from gaze, and gaze before the decision rather than the whole window.

---

## D074

### Date
2026-10-29

### Decision
Post-hoc sensitivity, deviation from protocol v1: repeated the Gate 2/3 ridge comparison (B0, B, B+G) on the T1 primary set with an extended C grid (0.0001, 0.001, 0.01, 0.1, 1, 10, 100). The original-grid results are unchanged and remain the pre-specified ones.

### Context / Problem
Ridge chose the smallest C (0.01) in 95-99% of folds, so the three models were nearly identical and the narrow CI was partly shrinkage.

### Evidence
The extended grid again chose its smallest value (0.0001) in 86-95% of folds. AUROC B0 0.636, B 0.635, B+G 0.636. B+G minus B +0.0007 [-0.004, +0.006]; B+G minus B0 +0.0000 [-0.005, +0.005]. Original grid: B+G minus B +0.004 [-0.006, +0.015]. With maximal shrinkage all three models reduce to the exposure offset.

### Alternatives Considered
Replace the original grid; add an unpenalised CV model.

### Why Alternatives Were Not Chosen
Replacing the grid would hide the deviation. The unpenalised likelihood-ratio test (p = 0.226) already is the unshrunk comparison.

### Implementation
Same code path as Gate 3 with a copied configuration; registry run `g6_ridge_grid_sensitivity_20261029_152830_288602`.

### Status
Complete. The null survives, and in a direction that adds no information beyond B0: the best CV choice is "ignore the covariates".

### Impact
None on earlier results. Adds a sensitivity statement.

### Remarks
Selection hitting the grid edge again is a property of data without signal beyond the offset, not an argument for a still wider grid.

---

## D075

### Date
2026-10-29

### Decision
Post-hoc, deviation from protocol v1: one EEG variant on the matched set (150 rows, 49 participants, 70 events): each EEG feature detrended linearly on trial index, fitted inside each training fold. Ridge, same 5 x 20 CV. No other EEG variant was run; BG+EEG minus B is not cited.

### Context / Problem
You asked for trial index to be added as a covariate. It already is a linear covariate in sets B, BG and BGE, so adding it changes nothing. The concern behind the request is that EEG band power drifts across the session, so I implemented that as detrending the EEG block on trial index.

### Evidence
Gate 4 reproduced exactly (AUROC B 0.610, BG 0.634, BGE 0.666). BGE detrended 0.666 [0.554, 0.754]. Primary contrast BGE detrended minus BG +0.030 [-0.015, +0.070], paired p 0.15; permutation p 0.18 (perm mean 0.651). BGE detrended minus BGE -0.0006 [-0.003, +0.002]. Spearman correlation of EEG features with trial index: 0.27 or below in absolute value (largest at TP10 delta, theta and alpha: 0.23-0.27).

### Alternatives Considered
Quadratic detrending; detrending on time since session start; within-participant centring.

### Why Alternatives Were Not Chosen
You asked for no other EEG variants.

### Implementation
`benchmark.detrend_within_fold` (off unless `detrend_on` is set); registry run `g6_eeg_detrended_20261029_153137_669114`.

### Status
Complete. The EEG null is unchanged by the adjustment.

### Impact
None on earlier results.

### Remarks
The RAG-contaminated-subset result (p = 0.019) is not pursued; it is a limitation and a hypothesis for new data.

---

## D076

### Date
2026-10-29

### Decision
Logged a deviation in the Gate 5 consistency pass: two harness processes wrote to the same files, producing duplicate (item, seed) rows. I stopped the single-worker process I had started; the three-worker process (`run_slm consistency all 3`, not started by me) continues. Scoring keeps the first reply per (key, seed) and discards later ones.

### Context / Problem
The consistency pass (temperature 0.3, seeds 1-5) was running as two processes at once. The resume logic reads the set of finished items only at start, so both processes appended replies for the same items.

### Evidence
For mistral at the time of detection: 4,413 distinct (item, seed) pairs in 5,609 rows; 1,206 pairs were duplicated, 1,159 of them (96%) with identical replies and 47 with different replies. The accuracy pass (temperature 0, single process) has no duplicates. Concurrent processes also change per-call latency, so latency from the consistency pass is not reported; Table 7 uses the accuracy pass only.

### Alternatives Considered
(a) Keep both replies and score all; (b) keep the last reply; (c) discard the pass and restart.

### Why Alternatives Were Not Chosen
(a) double-counts items and (b) would favour whichever process ran later; first-by-file-order is a rule fixed without reference to reply content. (c) wastes the completed items, and 96% of duplicates are identical anyway.

### Implementation
`score_slm.read_replies` drops later rows with the same (key, seed). The rule was set before consistency replies were scored. The raw files keep every row.

### Status
Open until the pass finishes; then the consistency tables are generated and the Gate 5 report is extended.

### Impact
Consistency agreement figures may differ slightly from a clean single-process run (about 4% of duplicated items had differing replies, which shows run-to-run non-determinism under concurrent load).

### Remarks
None.

---

## D077

### Date
2026-10-29

### Decision
Cleaned the 48 unpushed commits for publication, as approved after `docs/audit/PUSH_REVIEW.md`: configurable roots instead of a hardcoded lab folder, participant-linked data moved behind an ignored `private/` directory, provenance paths made repo-relative, identifiers removed from the new documents, and the unpushed history rewritten so the removed items are not in the range that will be pushed. Nothing was pushed.

### Context / Problem
The review found a participant-to-session-to-timestamp table (`video_gaze_session_map.csv`) in the unpushed history, a lab-folder path naming the students, mentor and supervisor in 7 scripts and 6 generated files, three participants' session folders and capture times in the video-pilot scripts, and session and path details in the Gate 0 report and in one earlier Decision entry.

### Evidence
Guard test `backend/pipeline/tests/test_no_private_strings.py` passes (no lab-folder name in any tracked file; no home paths, session folder names or capture names in the Gate files; the private directory is ignored and the map untracked). Verification of the rewritten range is recorded below in the Status line.

### Alternatives Considered
Fresh single-commit public repository with this history kept private.

### Why Alternatives Were Not Chosen
You approved the rewrite of the unpushed range instead.

### Implementation
`backend/pipeline/paths.py` (`EV_PROJECT_ROOT`, `EV_RAW_DATA_DIR`, `EV_VARJO_DIR`, `EV_PRIVATE_DIR`); the 7 scripts read roots and pilot sessions from it; `private_example/pilot_sessions.example.json`; `benchmark.load_gate3` stores the config path relative to the repo; capture filenames in this file's unpushed entries replaced by `varjo_capture_<timestamp>.mp4`; session folder name and home-directory paths in `docs/audit/GATE0_audit.md` generalised; provenance paths scrubbed in the 5 Gate 3 `summary.json` files and `results/registry.csv` (metadata only; no hash covers these fields). Backup branch `backup/pre-push-20261029` holds the pre-cleanup history. Earlier entries that were already on origin were not edited.

### Status
Complete locally; not pushed.

### Impact
Commit hashes in the unpushed range change, so the `git_commit` values in the registry rows refer to pre-rewrite hashes (mapping is in `docs/audit/HASH_MAP.md`). Results are unchanged. The local copy of the session map and the pilot session list live in `private/` (ignored); regenerate the map with `build_video_gaze_map.py`.

### Remarks
Pre-existing public content (`feature_table.csv`, older Decision entries, the `aoi_free_pilot.py` session names, a Windows account name in `main.py`) is untouched and remains a separate decision.
