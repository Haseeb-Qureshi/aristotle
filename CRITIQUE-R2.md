# Critique Round 2 — Same Panel vs SPEC v2.1 (2026-07-20)

Same outlay as round 1 (Fable fresh-eyes + Opus × learning-science /
hostile-executor / churn / state-audit), pointed at v2.1's *new machinery*
with CRITIQUE.md provided so no budget was spent re-verifying round 1.
~40 findings consolidated into clusters, ranked by cross-lens
confirmation × severity, against SPEC.md @ 2ebaec8.

## Verdict

**The architecture and the pedagogical direction held for a second round.
The round-1 amendments did not: three of the five headline fixes are
broken as specified, and the meta-pattern is now unmistakable — the spec
keeps writing "the script handles X" without writing X.** The transition
table §6 calls "stated" is stated nowhere; the grade-line grammar the
whole deterministic core parses is defined nowhere; the recovery gate
destroys the exact sessions it was built to save. Round 2's real
conclusion: this design has reached the limit of what prose specification
can verify. The ambiguities that survived two panels physically cannot
survive an implementation — the next artifact must be `schedule.py`, its
grammars, and its tests.

---

## R2-A — The deterministic core still doesn't exist on paper
[Fable + executor + auditor, all top-ranked]

- §6's "stated transition table" is not in the document. Pass at
  `exposed` vs `retrievable`, `use`-evidence jumps, ceiling behavior,
  repair-pass effects: all undefined.
- The grade-line grammar — the sole channel between agent and state
  machine — has no syntax. A weak model writes freeform; a stdlib parser
  matches nothing; **mastery silently stops moving** (round 1's silent
  no-op reborn at the format layer).
- §5 has the agent *writing* `solid` grade lines — putting mastery
  decisions back in the agent's hands, violating Invariant 4.
- `commit-grades` "atomicity" is asserted with no temp-file+rename, and
  the session-number guard corrupts under torn writes in either ordering
  (guard-last → double-apply; guard-first → grade loss).

**Fix A:** The spec (and script stub) carries the actual transition
table and a label-parsed grade-line grammar
(`- grade: <id> | result: pass|fail | evidence: <ref> | note: ...`).
`solid` is **never a writable grade** — the script derives it from the
(rubric-pass at N, re-probe-pass at N+1) pair in its own state.
`commit-grades` writes via `os.replace` with the committed-session
marker inside the same atomic write, and hard-errors (loud, non-zero) on
unparseable grade lines and unknown ids.

## R2-B — The recovery gate destroys good work
[Fable + executor + auditor; three independent proofs]

- Close order deletes the sentinel *after* commit → a commit failure
  (the round-1 motivating case: missing git identity) presents as
  sentinel+dirty → case 1 → `git reset --hard` **destroys a completed
  session**. Case 2 is unreachable by the intended path.
- `git add -A` commits the sentinel every session; its deletion
  re-dirties the tree, making "case 2" the routine state of every prep.
  No `.gitignore` is specified. `reset --hard` doesn't remove untracked
  files.
- The sentinel is simultaneously crash-marker and writer-lock with no
  pid/timestamp/heartbeat — a concurrent trigger (cron + phone) reads a
  *healthy live session* (sentinel + dirty from queue regen) as a crash
  and resets it. The "lock stops it" parenthetical runs *after* the
  recovery gate.
- "Commit-as-is" blesses non-close dirt (user hand-edit, crashed
  bootstrap) into history before `check` ever runs.

**Fix B:** All recovery moves into a `schedule.py recover` verb — it is
pure structure. Sentinel gains owner + ISO-timestamp + heartbeat; a
*fresh* sentinel means "locked, abort this trigger," never reset.
A stale sentinel is disambiguated by comparing its session number to
`plan.next-session` and checking whether the session's log with grade
lines exists: completed close → validate with `check`, replay the
idempotent close, commit; genuinely mid-flight → reset + clean
untracked. Sentinel is gitignored. Fingerprint mismatch → quarantine
branch, never mainline.

## R2-C — Delayed-`solid` is dead as specified [4/4 applicable lenses]

The most-confirmed finding of the round, from four directions:
never wired into `queue` (learning-science); even if due, it's the
*newest* item so cap-5 oldest-first actively selects against it (Fable,
executor); felt as "it didn't believe me" (churn). Net: `solid` — the
band goal #1 is measured by — is silently unreachable for keystones
whenever a backlog exists.

**Fix C:** Rubric pass sets `solid-pending: <id>` (mirroring
`repair-pending`); `queue` force-prepends it *outside* the cap.
Framing: a promotion mechanic — "nail this callback and it locks in as
solid" — with the award visible when earned.

## R2-D — Reprune is freehand surgery on the irreplaceable file
[Fable + executor + auditor + churn]

No verb removes a concept; accepting a reprune means hand-editing
knowledge-state (single-writer violation), plan, and assets
simultaneously; dropped concepts keep `status: active` with future
dates and **haunt the queue**; `check`'s symmetric orphan rule then
bricks the course at every subsequent prep. The trigger ("≥2 weeks
behind cadence") is *uncomputable* — the cadence lives only in platform
cron config (hidden state, unrecoverable at resurrection). And it's
offered at checkpoints the stalled user, by definition, doesn't attend.

**Fix D:** `schedule.py reprune --drop <ids>` mutates all files
coherently and atomically: `status: dropped` (excluded from queue and
from id-agreement — orphan rules become asymmetric), refuses to drop a
prereq of a kept concept, runs `check` before writing. `cadence:` is
recorded in plan.md at bootstrap. The offer also fires at re-entry, and
is framed as renegotiation toward the terminal task ("lock in a finish
on the essentials"), never as a concession; never auto-applied.

## R2-E — `check` validates existence, not quality [executor + auditor]

A lazy teach-back close ships placeholder keys, no rubrics, no
interleaved set — flips `next-assets: authored` — and passes `check`.
From unit 3 on, rubric grading silently becomes improvised judgment
(Cluster G reopened at runtime, exactly Open Question 2's fear). Also:
author-then-flip is prose ordering with a crash window that deadlocks
the gate (assets present, flag pending, no rung resolves it); and prep
never loads unit N+1's *sources* at teach-back, so authoring happens
from the map alone.

**Fix E:** Misconception ids are already machine-form, so `check`
requires per new unit: a rubric block per keystone (≥N required-claim
lines, ≥M misconception lines whose ids exist in the map), distractors
referencing real M-ids, ≥3 interleaved entries, an application prompt
per `use` concept, item counts matching the unit. Asset-write + flag
flip are one atomic operation. The gate is **self-healing**: a rung
between repair and teach-back — if next unit's assets are `pending`,
*this* prep authors them (map + sources are all in-directory; still
tool-free) and proceeds. Teach-back prep loads unit N+1's source notes.

## R2-F — `17r` breaks every integer that touches it
[executor + auditor]

`int("17r")` crashes `commit-grades` (→ abort → sentinel → reset →
**the rescue session is lost**); a digit-stripping parser records "17"
and the idempotency guard then **drops real session 17's grades**.
"Max one repair per boundary" has no counter; a failed repair leaves
the flag set → dispatch fires `17r` forever (stalling the unstallable
plan) and same-day reruns overwrite the log.

**Fix F:** Session-number token grammar: integer + optional `r`-suffix,
guard keyed on the exact string. `repairs-done` counter per boundary; a
*failed* repair clears the flag, marks the concept plateaued, and the
next unit opens with that concept's worked example re-shown (also
resolves the hard-edge vs forward-motion contradiction: prereq edges
are design-time sequencing constraints validated by `check`, never a
runtime gate).

## R2-G — Lifecycle counters are hidden state; two rungs are missing
[Fable + executor + auditor + churn]

- "3 consecutive silent triggers" is uncountable from the directory —
  a silent trigger writes nothing by definition. Resurrection-violating
  hidden state, alongside the cadence (D).
- `dormant` appears in the enum and nowhere else. Maintenance has no
  status and no rung — an exhausted course falls to "standard session"
  with nothing to teach.
- Re-entry has no rung: `resume` re-evaluates the raw ladder and can
  greet a returner with a **repair session** — the opposite of §8's
  promised gentle review, which has no structural carrier.
- Pause flips are out-of-band commits; a paused ping's prep writes a
  sentinel that no close ever deletes → stale-sentinel landmine.
- Churn retuning: 3 triggers ≈ one ordinary busy week at 3/week — far
  too eager; the paused-state ping (a content question about a decayed
  concept) deepens avoidance; the attendance streak is the canonical
  broken-streak shame artifact and collides with pause (zeroed = pause
  destroys the only positive counter; frozen = it lies).

**Fix G:** plan.md gains `cadence:`, `silent-triggers:` (incremented by
the trigger that finds the prior nudge unengaged — a one-line committed
write), and `re-entry-pending:`. Statuses: add `maintenance` with its
own rung; delete `dormant`. Re-entry is a ladder rung: review-only,
first retrieval item is the user's *most-solid* concept (engineered
win), no backlog framing, clears the flag. Pause triggers on **~14
elapsed silent days** (computed from `cadence` + last log date — all in
the directory), not trigger count; the paused ping offers a smaller
door ("5-minute rust-knock, or hold your spot?"). The streak becomes a
**cumulative sessions-done count** — can pause, cannot break.
Lifecycle-only preps clean their own sentinel.

## R2-H — Pedagogy calibration [learning-science + Fable]

- **The feedback amendment broke the session budget:** 5 items + 5
  feedback turns + re-probes + hook ≈ 13 turns before teaching begins.
  Fix: retrieval cap **3** on teaching sessions (5 only on
  teach-back/review-only); feedback on *correct* answers folds into the
  same turn; the dedicated turn is for misses.
- **`solid` after one delayed pass overstates durability** (successive
  relearning: 3–4 spaced successes) — and `verified`/graduation ride on
  it. Fix: `solid` additionally requires the concept to have cleared
  the 35-day interval; until then `retrievable`.
- **Maintenance cadence starves the fast ladder** where ~⅓ of concepts
  still are at graduation. Fix: weekly until the youngest concept
  clears interval 35, then fortnightly.
- **One interleaved problem/session is spacing, not interleaving.**
  Fix: the pre-teach-back session runs the *full* 3–5 mixed set as its
  middle (a natural unit-review session).
- **Fading was specified across unit position, not within a concept**
  (expertise-reversal hazard: late concepts get less scaffolding for
  arriving late). Fix: fade within a concept's own re-encounters —
  worked example at intro, faded at first Apply re-encounter, solo at
  second.
- **Pretesting left on the table:** the hook becomes a committed guess
  ("answer before I explain") — pretesting + hypercorrection for free.
- **Same-session re-probe of a miss is corrective closure only** —
  never grants pass credit; the fail stands for scheduling.
- **Session 1 is outside the ladder** and initial state is undefined
  (`exposed` means *taught*; untaught concepts need a band). Fix:
  `status: untaught` (excluded from queue, flipped at first teach);
  ladder rung 0: `next-session: 1` → placement session. `seed` is an
  idempotent upsert; seed-then-grades ordering defined (seed = baseline,
  probe grades apply forward from it).

## R2-I — Experience fixes to round-1's experience fixes [churn]

- Graduation: specify **no grade lines at capstone** — it is a mirror
  (session-1-you vs now), an output the user keeps, never a measurement.
  "Final cumulative teach-back" as written renders as a long exam.
- Checkpoint report: `report` output is agent-state; the user sees one
  sharp progress sentence + the hook + at most one adjudication ask.
  Never paste the 10 lines.
- Monotony: a small pre-authored rotating menu of encounter formats
  (predict-the-outcome, spot-the-flaw, critique-a-real-claim,
  mash-two-concepts), picked deterministically by session parity —
  variety without touching the spacing machinery.

## R2-J — Simplicity verdict [Fable]

A faithful SKILL.md is realistically 3k+ words. Fix: progressive
disclosure — SKILL.md carries ladder + body + close + pointers;
checkpoint/adjudication/reprune live in `checkpoint.md` (loaded on 7th
sessions); recovery lives entirely in `schedule.py recover`; asset
authoring is a template file read at teach-back closes; lifecycle
messages are templates. Pin the log draft: grade lines live in chat
context until the close writes the file — nothing touches disk
mid-session.

---

## Disposition

Every fix above has a converged solution across lenses; no open user
decisions remain from this round (pause timing, streak design, and
retrieval-cap changes adopt the churn/learning-science
recommendations directly).

**The definitive resolution of both rounds is the same act: build the
deterministic layer.** Two panels have now shown that every surviving
defect lives in an interface that exists only as prose. Writing
`schedule.py` + grammars + tests (Roadmap step 1) is not just the next
step — it is the only medium in which these bugs cannot hide. SPEC
v2.2 should be edited *concurrently with* the implementation, not
before it, so the document records what the code actually does.
