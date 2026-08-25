# Remediation plan — presented-facts coverage, fair retrieval, bank fencing

Implements the five fixes from REPORT.md, the backfill of the live AI-economics course, and the authoring-side rules for the packaged skill. Four workstreams (A engine, B skill docs, C live-course backfill, D bank annotation), independently executable given the grammar pinned here. Nothing in any workstream commits to git; review and commits happen after.

**Deadline context:** the live course's next session fires today (Mon) at 16:00 America/Los_Angeles. All syncs must land consistently before that, or not at all.

## Pinned grammar (all workstreams conform to this exactly)

### Taught-line (in a session log's `## taught` section)

```
- <concept-id>: <what was actually presented, free text> | without: <asset facts deliberately not presented>
```

- One line per concept whose facts the tutor presented this session — first teaching AND substantive feedback (feedback teaches).
- `| without:` clause optional. Omit when nothing notable was withheld. `<concept-id>` matches case-insensitively.
- Legacy free-prose lines under `## taught` (anything not matching `^- \S+: `) stay legal and are ignored by the parser.
- **Conservative principle:** when unsure whether a fact was presented, it goes under `without:`. Over-claiming coverage recreates the bug; under-claiming only makes future questions more generous.

### `begin` output additions (after the existing asked-recently block)

```
presented (grade only against this; anything absent goes INTO the question):
  cache-economics [2]: Anthropic cache pricing; session reuse | without: ProjectDiscovery case
  cache-economics [4]: paid writes vs discounted reads confirmed
  eval-diligence: (nothing recorded as presented — supply all facts in any probe)
banks spendable: assets/unit-01.md — items from unreached units are off-limits
```

- One line per taught-line found in any historical log, for each concept in the printed quiz queue, format `  <id> [<session>]: <presented>` with optional ` | without: <...>`.
- A queued concept with no taught-lines anywhere gets the `(nothing recorded as presented — supply all facts in any probe)` line.
- `banks spendable:` lists asset files of units that are reached (see fence definition below). Always printed when a quiz queue exists.

### `requires:` clause (asset banks, prose-level, tutor-read — the engine never parses banks)

```
- quiz: <stem> | a: <key> | distractor: M1 | requires: <case facts the key demands that the stem does not supply>
```

Runtime rule (SKILL): spend the item only if every `requires:` fact appears in the presented record; otherwise weave those facts into the stem and grade the remaining inference. The asked-ledger entry is still the bank id — the item is spent either way.

## Workstream A — engine + tests (`~/projects/aristotle/scripts/schedule.py`, `~/projects/aristotle/tests/test_schedule.py`)

TDD: write the tests first, watch them fail, implement, then run the full suite (currently 167 tests — all must stay green).

**A1. Taught-ledger.** A `_taught_history(course)` scan of `log/*.md` `## taught` sections (mirror `_asked_history`'s approach), returning per-concept entries `(session, presented, without)`. `begin` prints the `presented` block per the pinned format for every concept in the quiz queue. Case-insensitive id matching.

**A2. Close validation.** `commit-grades`/`close`: every `result: taught` grade must have a matching `- <id>: ...` line under `## taught` in the same log. Hard error, actionable: `log error: concept 'X' is graded taught but has no '- X: ...' line under '## taught' — record what you presented (and what you skipped) before closing.`

**A3. Bank fence.** A unit is **reached** iff `status != untouched` OR it contains the current session index. `begin` prints `banks spendable:` listing reached units' existing asset files. `close` emits an advisory (never failing) `warn: asked item '<id>.<qn>' belongs to unit <N>, which is unreached — that bank item is now spent for the whole course.` when an `## asked` bank id maps (via plan.md concept lists) to an unreached unit. Free-text asked lines and unknown ids: no warning.

**A4. Seed semantics.** `seed <id> <band>`: if the concept's unit is reached (same definition — at placement, session index 1 makes unit 1 reached), keep current behavior. Otherwise: record `note: placement: <band>`, keep `status: untaught`, `next: -`, `interval: 0` — the concept must NOT enter any quiz queue until its unit opens and it is taught normally (entry interval unchanged at the standard taught value; the note is what lets the tutor compress the teaching). Idempotency preserved.

**Mandated new tests** (names indicative): TestTaughtLedger (parse with/without clause; legacy prose ignored; begin prints records for queued concepts; nothing-recorded line; close hard-errors on taught-grade-without-taught-line; old-format logs never break begin/close), TestBankFence (spendable list tracks unit status; close warns on unreached-unit id; no warn otherwise), TestSeedFence (current-unit seed activates as before; future-unit seed is note-only and never queued; idempotent; later `taught` grade behaves normally).

Do not touch SKILL.md, templates, or any course directory.

## Workstream B — skill documents (`~/projects/aristotle/`: SKILL.md, templates/log.md, bootstrap.md, scheduling.md, references/question-novelty-and-review-spacing.md)

**B1. SKILL.md §1** — update the example `begin` brief to include the new `presented` and `banks spendable:` lines so tutors recognize them.

**B2. SKILL.md §2 (retrieval block)** — after the single-use/ledger paragraph, the fair-retrieval rule: a bank item's answer key lists facts; check them (and any `requires:` clause) against the `presented` record `begin` printed. Facts not in the record go **into the question**, and what is graded is the inference that remains. And the grading floor: a learner who demonstrates the concept but lacks a case fact that was never presented can pass or go ungraded — **never fail**. The fail verdict is reserved for misses on material the record shows was taught. Guard the loophole explicitly: this is not grade inflation — the grade stands on the inference the question actually demanded.

**B3. SKILL.md §5 (Never list)** — add: never name the skill, workflow, instructions, or any machinery to the learner ("I'm using the Aristotle tutoring workflow…" is machinery); never quiz or grade a concept `begin` didn't queue, other than today's newly taught concept — an off-queue probe burns single-use ledger novelty and moves spacing clocks the scheduler didn't ask to move; the open question is a doorway into the session, not a quiz — don't grade the answer to it; one bookend line per session, exactly.

**B4. templates/log.md** — the taught-line grammar (pinned above) with the conservative principle, replacing the `<one line: what was covered>` placeholder; note that `close` requires a taught-line for every `taught` grade; update the example.

**B5. bootstrap.md (the authoring/packaging side)** — three additions where they naturally fit: (1) **concept-probe vs case-probe**: a key graded on reasoning is freely reusable; a key demanding specific case evidence (names, numbers, events) is only fair if the stem supplies the case or the fact was presented — prefer stems that carry their case; where a key still demands outside facts, add the `requires:` clause (grammar above). (2) The design-studio checklist gains: for every case fact in an answer key, decide — stem, `requires:`, or core teaching notes. (3) Placement seeding: seeds on concepts in unreached units record the band as a note only (the engine enforces this); explain why — a placement answer is calibration evidence, not spaced-retrieval evidence, and activating far-future concepts drains far-future banks (REPORT.md F2/F3).

**B6. scheduling.md** — one sentence: when reconstructing a lost log from chat bookends, include taught-lines for what the transcript shows was presented, conservative principle applies.

**B7. references/question-novelty-and-review-spacing.md** — a short paragraph in the item-type taxonomy: case-fact items and the fair-retrieval check.

Keep every document's existing voice and prose conventions (natural paragraph lines, no hard wrap). Do not touch scripts/ or tests/.

## Workstream C — live-course backfill (`~/projects/ai-economics/log/*.md`, 15 files)

Reconstruct per-concept taught-lines for sessions 1–15 and append them under each log's existing `## taught` (keep the prose line), preceded by `<!-- reconstructed 2026-08-25 from gateway transcripts; conservative: uncertain facts under without -->`.

- **Source of truth:** copy `~/.hermes/state.db` to a scratch location first and read only the copy (the live gateway writes to the original). Table `messages` (`role`, `content`, `timestamp` as epoch floats). Locate each session by its bookends: first message matching `AI economics · Session N` through the matching `Next time (AI economics):`. All 15 sessions should be present (the course started 2026-07-26; the DB predates it). Telegram duplicates (identical consecutive user messages) are noise.
- **Which concepts:** exactly those with `- grade:` lines in that session's log.
- **What counts as presented:** only facts the transcript shows the tutor actually stating — including in answer feedback. For `without:`, consult the unit's asset file (`~/projects/ai-economics/assets/unit-0N.md`): case facts in that concept's items/teaching notes that the transcript never states. Conservative principle governs every judgment call.
- Known ground truth to honor: session 13 taught `interconnect-topology` WITHOUT the InfiniBand-tripled / Nvidia-leads-Ethernet market facts (they surfaced only in session 15's unfair probe, then were supplied in the retraction — so by session 15 they ARE presented, by session 13 they are `without:`). Session 12 note records `hbm-cowos.q1` spent as an unfair opener.
- **Never** run `schedule.py begin`/`close` on the live course, never touch knowledge-state.md/plan.md, never write to state.db, and leave everything uncommitted. Appending to logs is within the tutor's write surface; state files are not.
- Deliverable addition: a short summary (in the final report, not a file) of any live-course evidence of the F2 class — bank ids in `## asked` across the 15 logs that belong to unreached units.

## Workstream D — bank annotation (`~/projects/ai-economics/assets/unit-01..08.md`; `~/projects/aristotle/example-course/` asset banks)

Sweep every stored item. For each item whose answer key demands case facts (names, numbers, events, disclosures) that its own stem does not supply, append the `| requires:` clause per the pinned grammar. Leave stems and keys otherwise byte-identical — this is annotation, not rewriting. Items whose keys are pure reasoning get no clause. Report (don't fix) any item that is irredeemably trivia-shaped — a key that is ONLY a case fact, with no inference left once the fact is supplied. Leave everything uncommitted.

## Review phase (after all four land)

1. Diff review of both repos; full test suite; `install.sh` sync + `--check`; copy `scripts/schedule.py` to `example-course/scripts/` and `~/projects/ai-economics/scripts/`; re-sync the course's SKILL.md copy.
2. Dry `begin` on a scratch copy of the live course (today's date): presented records render from the backfill, fence line correct, session 16 brief sane.
3. Empirical re-validation: rebuild the virgin audit course (now carrying the fixed engine + skill) and re-run 3 capped-student sessions; no untaught-fact probe should survive, and any elision must surface as facts-in-the-question.
4. Add the one-line teaching invariant to `~/projects/bombot/AGENTS.md`: never fail a learner on a fact never presented — supply it and grade the inference.
5. Commit and push both repos.
