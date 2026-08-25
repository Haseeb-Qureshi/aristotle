# Capped-student audit — recall of facts that were never presented

**Date:** 2026-08-25. **Trigger:** the learner hit this failure repeatedly in the live AI-economics course, most recently session 15 ("You didn't tell me these facts so how was I supposed to guess this?"). **Question:** does a tutor running the unmodified Aristotle skill probe facts it never presented, and how does it grade the resulting miss?

**Verdict: reproduced on the first run, three times, with two unfair `fail` grades recorded.** The defect is structural, not a model quirk: nothing in the course state records which facts a teaching session actually presented, so nothing can stop a later session from quizzing the gap.

## Method

Five sessions of the real AI-economics course, replayed from a virgin copy (state reset to pre-session-1; engine, SKILL, assets all unmodified — see `make_virgin.py`).

- **Teacher:** codex `gpt-5.6-sol` (high effort), fresh thread per session, exactly as a stateless production tutor: its only continuity is the course directory.
- **Student:** codex `gpt-5.6-luna` (low effort), one-shot per turn. Its only continuity is the accumulated visible transcript (`ledger.md`), and it is **hard-capped to that transcript**: any probe of a fact not present must be answered "you never taught me that" — never bluffed from world knowledge. It also asks 1–2 tangential side-quest questions per session, to put the same time pressure on the teacher that a curious human does.

The audit signal is the divergence between the two continuities: the course state says `taught`; the transcript knows what was actually said. `driver.py` orchestrates; raw event logs and per-session transcripts were kept.

Cost: ~67k output tokens (sol) + ~2k (luna) for all five sessions.

## Findings

### F1 — Untaught-fact recall, graded as failure (the target defect; 2 occurrences, 1 near-miss)

**Session 3, `cache-economics.q2`.** Session 2 taught cache economics through Anthropic's write/read pricing and session reuse — and never mentioned ProjectDiscovery. Session 3 then opened cold retrieval with the bank item whose entire answer key is the ProjectDiscovery case fact (cache-hit rate 7%→84%). The student: "I don't think you've taught me what ProjectDiscovery changed, so I can't say. It sounds like the lesson is that inference architecture or workload design can matter more than switching models…" — the concept, recovered correctly. The tutor **acknowledged this** ("You recovered the economic lesson correctly but didn't know the case evidence") **and recorded `fail` anyway**: `note: inferred that architecture matters but did not know the ProjectDiscovery cache-hit mechanism`. The interval stepped down for a miss that was authored, not committed.

**Session 4, METR item (unit 6 bank).** The question supplied the trend claim; the key demanded the study's methodology facts (~170 coding-heavy tasks, sparse long tail, 50% bar) — presented in no session, belonging to a unit ~40 sessions away. The student gave a conceptually excellent answer ("supports that the trend has been increasing… extrapolating assumes the trend continues, ignores plateaus, benchmark limits, whether the chart reflects real workflows"). Tutor: "Good direction… The missing diligence detail is that the chart rests on only about 170 mostly coding tasks… **That missing specificity makes this one a miss today.**" Recorded `fail`.

This is an exact reproduction of live-course session 15 (`interconnect-topology.q2`, the InfiniBand/Ethernet market facts), where the learner had to object before the tutor retracted. Here the tutor was never challenged, and both fails stood.

**The near-miss that proves the fair pattern exists:** session 5 spent two more stored items but *phrased them fairly* — "a benchmark created by the model vendor — nearly double last year's best" and "Lab A reports 80%, Lab B 39%" — supplying every case fact inside the question and grading the inference. Both passed, both were honest evidence. The same tutor does it right when the question happens to carry its own facts; nothing but chance decides which way it goes.

### F2 — Cross-unit bank leakage

Sessions 4 and 5 spent **unit-6 bank items** (METR, the six-question checklist) to feed retrieval on `eval-diligence`, a concept that was never taught — only placement-seeded. Bank items are single-use per course: unit 6 will arrive with its bank partially dead, and the ledger will forbid the best items exactly when the unit finally teaches the material. Root: `begin` queues any active due concept, but the only stored questions for a far-future concept live in a far-future unit's file, and nothing marks that file off-limits.

### F3 — Placement seeding activates far-future concepts into the queue

Placement (session 1) seeded `eval-diligence` (unit 6) as `exposed` and `token-pnl` as `retrievable` from single answers. Reasonable calibration — but `exposed` → active/interval 1 put a unit-6 concept into the retrieval queue of nearly every subsequent session (2, 4, 5), months before its unit, with no legitimately spendable bank (F2) and no presented facts to probe (F1). Seeding conflates "has prior exposure, skip re-teaching later" with "is in active spaced retrieval now."

### F4 — Off-queue quizzing and grading

Session 2's brief said `quiz these (2): margin-debate, eval-diligence`; the tutor also quizzed and graded `token-pnl` (not due until 09-01). Session 3's brief queued only `cache-economics`; the tutor graded three concepts. The elapsed-gap rule contained ladder inflation (token-pnl held at interval 7), but every extra probe burns a single-use ledger entry and re-anchors spacing clocks the scheduler didn't ask to move. Sessions 4–5 were compliant.

### F5 — Machinery leak in openers

Three of five sessions began with a meta line naming the machinery: "I'm using the Aristotle tutoring workflow / skill / instructions…". SKILL §5 bans concept ids, bands, tokens, and script output — but never says "don't name the skill," so the tutor doesn't know not to.

### F6 — Session-1 cosmetics

The bookend line `AI economics · Session 1 —` was emitted twice in one message; harmless to reconciliation but sloppy. Also observed once in session 4's close (two `Next time (…)` lines).

## What held up

- **Close discipline: 5/5.** Every session closed itself, wrote a well-formed log, committed, and advanced the plan — zero operator nudges. (The cleanroom-era failure is gone.)
- **Placement manners:** pre-instruction misses in session 1 were explicitly not scored ("this establishes your starting point rather than counting as a miss").
- **Asked-ledger:** written every session, ids mostly correct, no cross-session question repeats.
- **Elapsed-gap rule:** off-queue passes did not inflate intervals.
- **Knowledge-cap methodology:** the capped student surfaced every violation unprompted and is cheap to re-run (`driver.py` against any course).

## Root cause

A stored bank item is an implicit claim: *"the facts in my answer key were presented to this learner."* Nothing in the system records fact-level presentation — `## taught` is a one-line summary, `status: taught` is per-concept, and grades measure the learner, not the coverage. So the claim is unverifiable at ask time, and two paths falsify it: the teaching session **elided** the case to fit the budget (correct tutor behavior under the 12-minute rule and learner side quests — the elision is not the bug), or the concept became quizzable **without its unit ever running** (placement seeding, F3). Grading then charges the learner for the tutor's edit. You cannot exhort a stateless agent into fairness here; the state it needs — what was actually shown — must exist.

## Proposed fixes (not yet applied)

1. **Presented-facts ledger (state):** the log's `## taught` section becomes a real coverage record — one line per concept touched: what was presented, and explicitly `without:` what the asset file holds that was not shown. `begin` replays the union for each queued concept, next to the asked-ledger.
2. **Fair-retrieval rule (SKILL, consulting #1):** before spending a bank item, check its answer key against the presented record. Facts not presented go **into the question**, and the inference is what's graded — the session-5 pattern, made mandatory. A learner who demonstrates the concept but lacks an unshown case fact can pass or go ungraded, never fail.
3. **Bank fence (engine, deterministic):** `begin` names the spendable asset files — the current unit and units already taught. Items from unreached units are off-limits; seeded-but-untaught concepts get fresh-built cases only.
4. **Seed semantics (engine):** placement seeds on far-future concepts record the evidence but do not activate retrieval until their unit opens (entry interval set from the seed at that point).
5. **§5 additions (SKILL):** never name the skill/workflow/machinery; quiz and grade only what `begin` queued plus today's taught concept.

Fixes 1–2 close the live course's actual incidents (sessions 12 and 15); 3–4 close the class the audit found beyond them; 5 is hygiene.
