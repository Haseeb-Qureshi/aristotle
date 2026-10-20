# Missed concepts, lost grades, and predictable reviews — diagnosis and proposal

2026-10-20. Prompted by the learner noticing, mid-session 33, that a whole concept (`neocloud-model`) was never taught although unit 4 is marked `taught`, that "PPA" was used in a question without ever being defined, and that reviews feel aggressive and identical every session. Evidence is from `~/projects/ai-economics` (git history, logs, `coverage-omissions-audit.md`) and the gateway transcript of 2026-10-20.

## Part A — Diagnosis

### A1. A whole concept was skipped (`neocloud-model`, unit 4)

**Trigger (operator error, mine).** On 2026-09-01 a context-scrambled tutor mislabelled its log as session 19 while the course was at 18, so slot 18 (then a review block) was skipped. The repair moved the review below unit 4 and noted "unit 4 absorbs the dead index: 7 planned sessions, 6 that will actually run" — enough, it claimed, for unit 4's remaining 5 concepts. It forgot that a unit's final slot is always the keystone teach-back. Real capacity: slots 20–23 = 4 teaching slots for 5 concepts. One was certain to be dropped; the last in list order (`neocloud-model`) was.

**Why nothing caught it.** The engine has no notion of coverage at unit boundaries:

1. `dispatch` is purely positional. The last slot of a unit is a teach-back unconditionally, even with concepts of that unit still untaught.
2. `cmd_close` writes unit status `taught` when the slot index reaches the unit's end — by calendar, not by content.
3. `check` / `course_warnings` warn when a unit is *padded* (more sessions than concepts+1) but never when it is *starved* (fewer teaching slots than concepts).
4. `begin` lists `untaught here` for the current unit only. A concept stranded in a finished unit is invisible to every later session, forever.

### A2. Grades silently dropped; session tokens reused (an engine bug)

`cmd_recover`'s replay path — "stale lock + a log with grades → replay" — calls `cmd_commit_grades` only. That marks the token committed and applies its grades, but never runs the rest of close: the plan counter does not advance, `sessions-done` is not incremented, unit status is not updated. The next `begin` therefore issues the *same* token. When that re-run session closes, `cmd_commit_grades` sees the token already committed and returns `noop` — its grades are discarded — while `cmd_close` goes on to advance the counter.

Evidence: tokens with more than one log are 21, 25 (three logs), 27 and 33. The closing commits of sessions 21, 25 and 33 changed **zero** rows of `knowledge-state.md`. Session 25's real close (2026-09-26) dropped five review grades. Session 21 was hand-repaired the next day; session 33 was rescued on 2026-10-20 by the runtime agent writing its own `amend-grades` command into the course's copy of `schedule.py` (engine drift — the repo never saw it).

The latent bug predates 2026-09-01, but the draft-log change made on that date (`begin` creates the log, the tutor appends grades as they land, recovery replays any draft holding evidence) turned "abandoned session with grades" from rare into routine. Every abandoned-then-resumed session since has hit it.

Secondary effect: a replayed session's material gets re-run under the same token, so the ledger and the learner see repeats (session 33 reused a case from the abandoned 10-14 draft; the tutor apologised for it).

### A3. Sub-concept omissions accumulate and are never repaid

58 `| without:` clauses across 22 concepts record material a teaching session deliberately left out. Leaving material out is correct — a twelve-minute session cannot carry an asset section of five to ten cases and figures. The defect is that omissions are a write-only record: nothing schedules them back. Retrieval sessions re-probe the concept's core, so the same omission is re-recorded session after session (`cache-economics` logged the same omitted worked example in five sessions; `token-pnl` in seven).

Two aggravating factors:

- **No core/optional distinction.** Assets do not mark which facts are the mechanism and which are dated colour. The tutor cannot tell that "PPA mechanics" (a definition later questions depend on) matters more than "Broadcom guides to >$100B FY27".
- **Terms of art used before definition.** The 2026-10-20 PPA question used a term the original session 22 log explicitly lists as not taught. The fair-retrieval rule checks *answer keys* against the presented record, but not the *vocabulary of the question itself*.

### A4. Reviews are predictable

Every teaching session since session 21 has the same shape: an opener, then exactly two retrieval items, then the new concept. `TEACHING_CAP = 2` is reached every session because the early ladder rungs keep the queue full, and SKILL.md places the retrieval block at the start unconditionally. The learner experiences "two review questions at the top" as a fixed ritual — and reports it as aggressive and repetitive.

## Part B — Proposal

### B1. Engine: make replay a real close (fixes A2)

- Factor `cmd_close`'s post-grade work (counter, `sessions-done`, `last-attended`, unit status, queue, commit) into one function used by **both** `cmd_close` and `cmd_recover`'s replay path. A replayed session is a closed session.
- Hard invariant in `begin`: never issue a token already in `committed-sessions`. If it would, raise an actionable `IntegrityError` naming the state ("session N is committed but the counter was not advanced — run `S recover-counter`" or similar), rather than silently producing a duplicate.
- Drop the course-local `amend-grades` patch when the course resyncs from the repo: with the root cause fixed it has no future use, and keeping an engine fork in one course is the drift `install.sh --check` exists to prevent. Session 25's five lost review grades are a month old; replaying them now would stamp September evidence with an October date and distort intervals, so they are recorded as lost rather than re-applied.

### B2. Engine: coverage is a unit-closing condition (fixes A1)

- **Starvation check.** `course_warnings` (and `begin`, once, as a NOTE) flags any unit whose teaching slots (sessions minus the teach-back slot when the unit has keystones) are fewer than its concepts. Every plan edit is then checkable.
- **Debt-first teaching.** A concept is *stranded* when its unit's slot range has ended and it is still `untaught`. Stranded concepts are taught before anything else (see B3). Within a live unit, the teach-back slot becomes a standard teaching slot if any of the unit's own concepts are still untaught; the deferred keystone teach-back is owed and scheduled like any other catch-up item.
- **Unit status by content.** Close writes `taught` only when every concept of the unit is past `untaught`; otherwise the unit stays `in-progress` (and its untaught concepts are stranded once its range ends).

### B3. Engine: catch-up sessions that don't consume the plan (fixes A1, A3; schedules the backlog)

Reuse the shape that already works for repairs: a fractional token that does not move the counter.

- New engine-owned file `catch-up.md` holding an ordered agenda of items:
  - `- [ ] teach: <concept>` — a whole concept owed (stranded concepts are added automatically by `begin`/`close`; nothing needs the operator).
  - `- [ ] teachback: <keystone>` — a deferred teach-back.
  - `- [ ] gap: <concept> | <owed material>` — sub-concept material, added by the course author with a new `S owe <concept> "<material>"` command (validates the concept id; appends; commits).
- `dispatch`: if the agenda has open items, the session is type `catch-up` with token `{idx}c` (`{idx}c2`, …), which close never uses to advance the counter. The brief prints this session's items: one `teach:` or `teachback:` item alone, or up to three `gap:` items (grouped as written in the file, so the author controls themes).
- Close of a `c` token ticks exactly the items the brief assigned, and nothing else. An abandoned catch-up ticks nothing (the items stay open). Close requires at least one `## taught` line for a gap-only session; grades remain optional there (a `pass`/`fail` on a gap's parent concept is allowed when the tutor checked it), because a gap session teaches rather than tests.
- Precedence: repair > catch-up > the plan's next slot. Re-entry and dormancy rules keep precedence over all of these.

### B4. Engine: varied review (fixes A4)

`begin` decides a **review plan** for every teaching session (`standard`, `catch-up`), deterministically from a hash of the course id and the session token — two agents running `begin` for the same session always agree, but the shape varies session to session:

| Plan | Weight | Brief line |
|---|---|---|
| none | 0.15 | `review: none this session — the queue rolls forward` |
| 1 item, at the open | 0.20 | `review: 1 · at the open` |
| 1 item, at the end | 0.25 | `review: 1 · at the end, as an exit ticket` |
| 1 item, woven in | 0.15 | `review: 1 · woven into the lesson where it fits` |
| 2 items, split open/end | 0.15 | `review: 2 · one at the open, one at the end` |
| 2 items, at the open | 0.10 | `review: 2 · at the open` |

Mean load drops from 2.0 to about 1.1 items per teaching session. Guards that override the draw:

- `none` is never chosen twice in a row (the previous session's plan is recomputed from its token).
- `none` is never chosen when any queued item is overdue by more than its own interval (spacing tolerates slip, not neglect), or when the queue holds a recent `fail`.
- `review`, `consolidation`, `repair`, `re-entry` and `teach-back` sessions keep their current dedicated behaviour; the draw applies only to sessions that teach.

Items not reviewed roll forward exactly as overflow does today; the elapsed-gap rule already handles late reviews correctly (a later pass is stronger evidence, not weaker).

### B5. Pedagogy (SKILL.md)

- **Follow the review plan line.** Replace "Then the retrieval block" (fixed position) with: run retrieval where the brief's `review:` line says — at the open, at the end as an exit ticket, or woven in at the moment the lesson touches that concept.
- **Repay one debt per retrieval.** When a queued concept's `presented` record shows a `without:` that is a mechanism or definition (not a dated figure or colour example), the correction after that item presents one such owed piece — one sentence or one number, never a lecture — and logs it as a coverage line. Over a course, every retrieval of a concept closes one gap instead of re-recording it.
- **No undefined terms in questions.** Every term of art in a question you pose must appear in that concept's `presented` record, or be defined inside the question. ("PPA" in session 33 was neither.)
- **Catch-up sessions** (type `catch-up`): teach the listed items with a worked micro-case each, no new plan concept, retrieval per the review line, close as usual. For a `teach:` item, it is an ordinary first teaching of that concept.

### B6. Authoring (bootstrap.md, asset template)

- Mark the irreducible core in each concept's asset section with `- core: <the one mechanism or definition the concept cannot be taught without>` (one or two lines). A teaching session must present the core; everything else is optional colour that may be skipped without debt. `check` warns when a concept has no `core:` line.
- The plan arithmetic rule, stated where plans are written: teaching slots = sessions − 1 when the unit has keystones; teaching slots must be ≥ concepts. (The engine now checks it, but authors should not rely on the check to discover it.)

## Part C — The AI-economics course: catch-up schedule

With B1–B3 in place, the course gets a catch-up agenda (`catch-up.md`) worked through before unit 6 continues. Proposed agenda (themes grouped so each gap session is coherent; ~3 items each):

1. `teach: neocloud-model` — automatic (stranded in unit 4).
2. Serving mechanics gaps: `prefill-vs-decode` — TTFT vs tokens/sec and who feels each, disaggregated serving; `batching-economics` — MFU as the honesty metric with its rules of thumb, the long-context KV-loading crossover; `cache-economics` — the write/read multiples and the worked A-vs-B prompt-architecture bill.
3. Chips, memory, fabric gaps: `workload-shapes` — bytes per parameter to train vs to serve, and failure economics of synchronous clusters; `hbm-cowos` — the 2026 memory-price split (HBM contracts vs DRAM spike); `parallelism-axes` — pipeline bubbles and the MoE three-bills walk.
4. Power, sites, money gaps: `power-markets` — PPA vs virtual PPA, heat-rate call options and deal unbundling; `dc-anatomy-cost` — behind-the-meter as the only fast greenfield path and the announced-vs-operating gap; `margin-debate` — the free-user mix explanation behind the API-vs-blended margin gap; `asic-absorption` — the share-denominator taxonomy.

That is four catch-up sessions (1 + 3), after which session 34 (unit 6, `benchmark-failure-modes`) proceeds. Dated figures and colour examples from the audit (price ladders, vendor guidance, market sizes) are deliberately not on the agenda; the debt-repayment rule (B5) covers them opportunistically if they matter.

## Part D — Test plan

- TDD for every engine change: replay advances the counter and later close applies its grades; `begin` refuses a committed token; starvation warning; teach-back slot yields to an untaught unit concept; unit status stays in-progress with untaught concepts; stranded concepts auto-enter the agenda; catch-up token never advances the counter, ticks only assigned items, survives abandonment; review plan is deterministic per token, respects both guards, and its long-run distribution matches the weights.
- Migrate a scratch copy of the live course and simulate the next ~10 sessions with `ARISTOTLE_TODAY` and scripted closes: confirm four catch-up sessions run first with the right items, then unit 6 resumes at 34, and review shapes vary.
- One live-model run: a capped-student audit (teacher on the production tutor model, student capped to the transcript) over the first two catch-up sessions on a scratch copy, checking that catch-up teaching and the review line are followed.

---

# Part E — Critique (independent reviewer, same model tier) and resolution

The reviewer verified A1, A2 and the engine claims against the code, then corrected and extended them. What changed as a result:

| Finding | Severity | Resolution |
|---|---|---|
| Starvation check is redundant: `cmd_check` already fails `sessions < concepts+1`; unit 4 starved through a dead index the arithmetic can't see | should-fix | Dropped. Replaced by the content condition: an ended unit's untaught concepts become owed. |
| Session 24 also hit the replay bug; six grades lost on token 25, not five | correction | Recorded. Old losses are not replayed (dating September evidence in October would distort intervals). |
| **M1: units 2-4 never got a graded teach-back** | blocker | Engine derives owed teach-backs: any ended unit whose keystone has no `rubric-*` grade in a committed log. |
| **M2: "repetitive" is selection, not shape** — `(interval, next)` sort let fresh items win every slot; 19 of 23 concepts overdue, units 1-3 untouched for six weeks | should-fix | Queue now alternates fresh items with the most-overdue backlog (lateness relative to interval). |
| **Replay-as-close double-advances** after a crash between header write and unlock | blocker | Replay never advances. Close advances only when the counter still points at the token's slot. A replayed slot re-runs under `Nb`, so grades never collide. |
| Replay burns a half-done slot | should-fix | Resolved by the same design: a slot advances only on a real close. |
| Replay NOTE text and empty open question after drafts | should-fix | NOTE rewritten in engine and SKILL; open question falls back to the newest log that has one. |
| Catch-up (new file, `c` token, new type, new command) is over-engineered | drop | Catch-up of whole concepts and teach-backs is *derived* (no state), runs as `r` tokens through existing non-advancing machinery. Sub-concept gaps go to `owed.md`, offered one per concept the session already touches. |
| `none` review is swallowed by an overdue guard; "woven" and end items get dropped by a cheap model near the close trigger | should-fix | No overdue guard; only "never twice in a row". Shapes reduced to none / open / exit ticket / split; the exit ticket is written into the close trigger. `hashlib`, not `hash()`. |
| Off-queue probes are the real session-33 failure | add | `begin` pins `review/quiz/teach/owed` in the draft; `close` warns on grades outside it. |
| `core:` marker duplicates `def:` | drop | Brief prints the target concept's `def:` line. |
| Course-local engine fork invisible to `install.sh --check` | add | `install.sh --check-course DIR`. |
| Evidence-free drafts committed as clutter | nit | `begin` sweeps wholly empty drafts; drafts with posed questions stay (ledger). |
| Gap agenda timing / content | should-fix | Whole-concept and teach-back catch-up first (the learner asked for catch-up sessions now); trivia dropped (HBM price split replaced by the "nothing to reallocate" mechanism); added allocation's financing loop, token-pnl's 5-6x rule, nvidia-generations' multiple-inflation trick; PPA trimmed to heat-rate options and unbundling. |

Found later in simulation, fixed: a regular teach-back brief never named its keystone (a scripted tutor skipped the rubric and the engine flagged the debt), and teach-back sessions still queued five review items — both now follow the brief like other teaching sessions.
