# Critique Round 1 — Five Independent Reviewers (2026-07-20)

Panel: one Fable with fresh eyes and foundations attackable, plus four Opus
reviewers with fixed lenses (learning science, hostile cheap-model executor,
adherence/churn, state-corruption audit). Each returned ≤8 ranked findings
against SPEC.md @ fda68ce. This document consolidates ~40 findings into
clusters, ranked by cross-lens confirmation × severity. Full reports live in
the session transcript; nothing of substance was dropped.

## Verdict

**The architecture survived; the mechanization didn't.** No reviewer
attacked map/plan/session, markdown state, no-RAG, sessions-as-currency, or
compression-as-pruning (the churn reviewer explicitly credited the queue
cap as dodging Anki's review-wall). What failed, in one sentence: the spec
*asserts* "structure over prose" but ships its most critical rules — the
concept state machine, atomicity, asset authoring, grading rubrics — as
prose, and its scheduling arithmetic doesn't fit inside its own course
length. Plus an entire missing dimension: the emotional design of being a
user.

---

## Cluster A — The concept state machine does not exist [4/5 lenses]

The single most-confirmed defect. The spec never defines: how far a pass
moves mastery, when a concept enters the queue, where `plateaued` /
`retired` / `dropped` live (the line schema has **no status field**), how
teach-back evidence reaches the script (teach-back is never told to call
`update`), how calibration seeds ~22 concepts (no `seed` verb — `pass`
would schedule everything at interval 1), or how adjudication verdicts
flow back (`set-verify` doesn't exist). Two implementers would build
materially different systems; the anti-inflation guard is enforced by
nothing. The auditor added the killer detail: `update` on a typo'd id
**silently no-ops** — the concept's dates freeze forever with no error.

**Amendment A:** Specify the full per-concept state machine and put it in
`schedule.py`, not prose. Line schema gains `status:
active|plateaued|retired|dropped`. Script verbs become:
`check | queue | seed <id> <mastery> | update <id> pass|fail |
set-verify <id> <mech> | report`. `update` is idempotent (no-op if
`last == today`), errors loudly on unknown ids, owns mastery arithmetic
via a stated transition table, and sets status transitions. `report`
emits decaying/plateaued/progress so checkpoints need zero agent date
math.

## Cluster B — Atomicity is false as written [2 lenses, mechanically proven]

`schedule.py update` mutates knowledge-state.md live during the retrieval
block, hours before the only commit. Crash mid-session → next dispatch
re-delivers the *same numbered session*, but the advanced dates hide the
already-quizzed concepts from the re-run's queue (silent interval
double-advance). Worse, "on doubt, reset" has no defined trigger and
cannot distinguish a half-crashed session (reset is safe) from a
completed-but-uncommitted one — e.g. `git commit` failing on a fresh box
with no git identity — where reset **destroys a finished session**.

**Amendment B:** Grades are recorded in the session log as they happen but
applied to knowledge-state in one batch at close (`schedule.py
commit-grades <session-log>`), immediately before `git commit`. A
`.session-inprogress` sentinel is written at prep and removed only after
commit succeeds; prep runs a `git status` gate and the sentinel tells
recovery which case it's in. README mandates git identity (or the skill
commits with `git -c user.email=…`).

## Cluster C — The scheduling math fails the #1 goal [1 lens, but it's arithmetic]

Graduating the 1/3/7/16/35 ladder requires ~62 days of successful
reviews; a 30-session course at 3/week is ~70 days. **Every concept
introduced after ~session 18 is mathematically stranded** — abandoned at
course end with 1–2 exposures. And "retire permanently after one 35-day
pass" stops reviewing exactly where durable retention begins (spacing
research: final gap should scale with the desired retention horizon —
months, not 35 days). Also: reset-to-1 on failure discards storage
strength, over-reviews, and stacks failure experiences.

**Amendment C:** No permanent retirement mid-course. On the final ladder
pass, the next interval scales to a retention target (90/180 days).
Maintenance mode becomes the *default* terminal state (the celebration
happens first — see F). Failure steps back one interval (16→7), reserving
the 1-day floor for repeated consecutive failures.

## Cluster D — Sessions open on a loss frame; feedback is missing [2 lenses, opposite directions]

The learning scientist and the churn skeptic converged from opposite
sides on the retrieval block: the spec **never requires telling the user
the correct answer** — forfeiting the corrective-feedback amplification
of the testing effect *and* creating the competence-killing experience of
unresolved failure. Meanwhile session 1 is a placement exam as a first
impression (the steepest churn cliff in any learning product), and every
session's fixed front door is cold quizzing before any payoff.

**Amendment D:** (1) A corrective-feedback turn is mandatory after every
retrieval item: correct answer + which named misconception the error
matched; failed items get re-probed later the same session. (2) Session 1
leads with one striking flagship idea from the terminal task *before* the
placement probe, which is reframed as "finding your starting line."
(3) Every session opens with a curiosity hook tied to today's concept;
the retrieval block follows it. Cold retrieval and grading keys are
untouched — only position and framing change.

## Cluster E — Teach-back is doubly broken [3 lenses]

The learning scientist: a learning activity miscast as the exam —
same-day fluent explanation measures retrieval fluency, not durable
storage, and scoring it is exactly the improvised judgment the invariants
forbid. The executor: no rubric exists, so a lazy model grades a
half-right explanation charitably and books 5/5 at the highest-stakes
measurement point. The churn skeptic: thumb-typing multi-paragraph
expositions on a phone every 3–5 sessions is the highest-friction
recurring session, with predictable evasion (and since 5/5 is only
reachable there, evasion silently caps mastery).

**Amendment E:** Asset files carry a discrete teach-back rubric per
concept (N required claims present, M named misconceptions absent →
pass). Teach-back is scoped to the unit's 1–2 keystone concepts, not all
of them. Voice notes and bulleted answers are accepted. Top mastery
requires *delayed* evidence (the rubric passed at the next session's
warm-up re-probe, or an artifact section surviving critique) — not
same-day fluency. Teach-back results flow through `schedule.py update`
like any other evidence.

## Cluster F — The missing lifecycle: pause, reprune, dignified exits [3 lenses]

No pause state, no dormancy, no quit path, no mid-course renegotiation.
Nudges repeat forever at a ghosting user (most likely real outcome: the
user kills the cron by hand, orphaning the course outside its own state —
violating the no-hidden-state principle in spirit). A stalled "17/30" is
a shame monument with two exits: grind or ghost. Compression-as-pruning
exists only at bootstrap, so a slumping user can never renegotiate to a
shorter finish.

**Amendment F:** plan.md gains `course-status:
active|paused|dormant|closed`. After K consecutive silent triggers,
auto-pause with one low-shame message ("say resume whenever") and drop to
a fortnightly ping at most. Checkpoints offer a **reprune** when the user
is badly behind wall-clock: cut to a shorter finish by re-running the
backward-design pruning rule (drop non-threshold concepts, keep spacing
on what's left) so a stalled user finishes *something*. Graduation
becomes a moment — capstone teach-back or finished artifact as the
closing act, report as trophy — with maintenance as the post-celebration
default (per C).

## Cluster G — The spec violates its own Principle 1 [2 lenses]

The executor's worst hole: **authoring unit N+1's assets appears only in
§3's file description, never in §5's executable procedure** — a literal
executor never does it, and from unit 3 onward "graded against stored
keys" silently degrades into improvised judgment. Related structural
gaps: repair-pending is a dispatch input no file holds; dispatch
conditions are an unordered bullet list (teach-back + checkpoint + repair
collisions undefined); turn-count self-tracking is an exhortation;
`schedule.py check` validates only acyclicity, so a lazy bootstrap
shipping 40 undifferentiated concepts and empty asset files passes; and
§2's claim that sessions need no tools contradicts §5's per-unit refresh
doing web research inside session prep.

**Amendment G:** (1) plan.md gains `next-assets: pending|authored` and
`repair-pending: <concept-id>` (set by script from teach-back grades);
dispatch reads both. (2) Dispatch is an explicit priority ladder: repair
> teach-back > standard; checkpoint composes orthogonally; the retrieval
block and close run in **every** mode (also fixes queue starvation at
unit boundaries). (3) Repair sessions take fractional numbers (`17r`) —
no renumbering, shot clock intact. (4) `check` extends to: concept-count
band, threshold-tag count 5–8, every unit's asset file exists with ≥1
quiz key per `verify: quiz` concept, and **cross-file id integrity**
(map ↔ knowledge-state ↔ plan ↔ assets; no orphans, no duplicates), run
at every prep, not just bootstrap. (5) Unit-boundary prep becomes a
named third mode (`unit-prep`) with research tools; standard sessions'
"no tools" claim becomes true. (6) The close follows a fixed template
with slots (structure) instead of a remembered turn counter.

## Cluster H — File-format fragility [2 lenses]

The irreplaceable file is parse-ambiguous: records shown wrapped across
physical lines with no stated delimiter; notes can contain `|`, breaking
naive splits; positional-vs-label parsing undecided; id uniqueness
unenforced; timezone for "today" unpinned (the pilot user crosses the
dateline routinely); no Python minimum stated for resurrection.

**Amendment H:** One physical line per record, `- ` delimiter, label-based
parsing, `note:` guaranteed-last with right-bounded split, `check`
rejects duplicates and multi-line records. Map header gains `timezone:`;
`schedule.py` computes "today" via `zoneinfo`; README states python3.9+
and git as resurrection preconditions. A lockfile keyed on session number
prevents the cron+user-initiated double-writer.

## Cluster I — Pedagogy upgrades accepted [1 lens each, low conflict]

- **Interleaving lives in Apply:** mixed problems spanning prior units
  where the learner must *identify* the applicable concept before
  applying it (discrimination is the transfer skill the terminal tasks
  need). This also replaces depth-leveled concepts (below).
- **Transfer-appropriate items:** for concepts whose terminal use is
  judgment, quiz items are short case-judgments, not definition recall.
- **Self-explanation prompt** ("why is that true?") after retrievals and
  applications; **worked-example fading** across each unit (example →
  faded → solo).
- **Turn budget calibrated down**; retrieval answers may be one word /
  short phrase (still production — free recall preserved; multiple-choice
  only where the item is inherently discriminative, since recognition is
  weaker than production).
- **Attendance streak** (not correctness streak) as the one positive
  counter, in plan.md.

## Cluster J — Simplifications (Fable's overbuild audit, adopted)

- **Delete depth-leveled concepts** (`x-1`/`x-2`): interleaved Apply (I)
  now does the revisiting work with less machinery.
- **Merge the freshness dials into one** (`refresh: none|per-unit`
  implies the bootstrap-research answer in practice).
- **Copy SKILL.md into the course directory** at bootstrap (like
  schedule.py) — kills the README-as-drifting-duplicate problem and makes
  the resurrection standard consistent (Principle 8 and §9 currently
  state different bars).
- `verify: use` concepts: bootstrap authors 2–3 reusable application
  prompts each, so scheduled re-encounters draw on curated material and
  they flow through the same queue.
- Errata gains a machine-applicable form (`erratum: remove-edge A -> B`)
  merged over the frozen graph by `check`/`queue` — ids stay immutable,
  edges become correctable.

---

## Open decision points for v2.1

1. **Mastery scale:** keep 0–5, or collapse to 3 evidence-anchored bands
   (exposed / retrievable / transfers-cold) as the learning scientist
   argues the evidence supports? Recommendation: **3 bands** — the
   transition table (Amendment A) gets trivially simple, and the 0–5
   precision was never measurable anyway.
2. **Per-unit refresh:** keep as the new `unit-prep` mode, or cut from
   v1 entirely (Fable's alternative)? Recommendation: **keep** — the
   pilot course (AI economics) is the motivating case for it.
3. **Repair sessions:** fractional numbering (`17r`, recommended) vs.
   consuming numbered slots.

## Status

Amendments A–H are correctness fixes and not controversial; I and J are
adopted recommendations. Pending: user sign-off on the three decision
points, then SPEC v2.1.
