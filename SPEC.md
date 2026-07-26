> **SUPERSEDED — do not execute this document.**
>
> This is the v2.1 design spec, kept for the design history. The system
> was then built, reviewed by a third adversarial panel, and changed in
> ways this file does not reflect: mastery bands, `ceiling`, `reprobe`
> and `solid-pending` were deleted (mastery is derived, not stored);
> dispatch and the close moved into `schedule.py` as `begin` and `close`;
> the unit-review session type was folded into teach-back; consolidation
> sessions were added at the end of the course. Several statements here
> are now simply wrong — most sharply, it has the agent writing a `solid`
> grade line, which no longer exists.
>
> **The executable spec is `SKILL.md`, `bootstrap.md`, `checkpoint.md`,
> `templates/`, `tests/test_schedule.py`, and `example-course/`.**
> See `CRITIQUE-R3.md` for what changed and why.

# Tutor — Consolidated Spec (v2.1)

A chat-based AI tutoring skill that teaches a single user one topic across a
finite, scheduled course of short sessions. All state lives in one
human-readable directory. Exportable: any user, any agent platform, any model.

v2.1 incorporates the five-reviewer critique round (see CRITIQUE.md):
the concept state machine moved into the script, batch-atomic grading,
retention-horizon scheduling, feedback-first pedagogy, rubric-based
teach-back, a course lifecycle, and a simplification pass.

Design goals, in priority order:

1. **Retention** — the user remembers, long-term (past the course, not to
   its end).
2. **Adherence** — the user keeps showing up and finishes.
3. **Simplicity / exportability** — a stranger's agent runs it faithfully.
4. **Coverage** — of the pruned, goal-relevant slice of the domain.

---

## 1. Design principles

1. **Structure over prose.** A skill is executed by an arbitrary LLM under
   context pressure. Any rule that matters is embedded in file formats,
   scripts, or state-driven dispatch — never in exhortations. Scheduling,
   mastery transitions, and status changes live in a script. Grading is
   comparison against stored keys and rubrics. Session type is derived
   from state via an explicit priority ladder.
2. **Forward motion is unconditional; verification is advisory.** The
   course advances session by session. Mastery is a scheduling input,
   never a gate. Weak concepts persist in the (capped) review queue.
3. **Map fixed, plan mutable, session ephemeral.** A one-time design pass
   produces a stable concept graph. A living plan derives from it.
   Sessions are generated from plan + state + pre-authored assets.
4. **Sessions are the currency.** Course size, progress, and the shot
   clock are counted in sessions. Only review scheduling is
   calendar-based. Missing days costs calendar time, never progress.
5. **Compression = pruning** — at bootstrap *and mid-course*. A shorter
   course is a smaller concept list chosen by backward design, never the
   same content covered faster.
6. **Design time is cheap, runtime is fragile.** Grading keys, rubrics,
   worked examples, misconception distractors, interleaved problem sets,
   and source notes are authored at bootstrap or at structurally-gated
   unit boundaries. Runtime adapts curated assets; it never improvises
   evidence standards.
7. **User-minutes are the scarce resource.** Onboarding is ~5 taps; the
   agent spends tokens lavishly and user-time stingily. Cheap onboarding
   is safe because the plan is mutable and checkpoints are the
   correction loop.
8. **Showing up must feel like learning, not being audited.** Every
   session opens with a payoff before any testing; every retrieval ends
   with corrective feedback; failure steps back, never to zero; stalls
   get a dignified renegotiation, never a guilt pile.
9. **The resurrection test.** A fresh agent, any model, any platform,
   handed only the course directory, must correctly run the next session
   with zero explanation. No state exists outside the directory.

---

## 2. System shape

Two skills, one directory, one script.

- **`bootstrap`** — run once per course. Brief interview, research (if
  needed), curriculum design, asset authoring, directory creation,
  schedule setup. The only place with web/research tools.
- **`session`** — runs every scheduled session. Tool-free beyond file
  I/O and the bundled script — true in every mode, always. All external
  ingestion happens at bootstrap.
- **`scripts/schedule.py`** — stdlib-only Python (≥3.9), copied into the
  course directory at bootstrap. Owns all date arithmetic, mastery
  transitions, status changes, queue generation, and integrity checks.
  The agent never computes dates and never decides mastery moves.

Cut from v1/v2: spar; four-way verification classes; per-modality attempt
budgets; standalone teach-back/weekly-review skills; embeddings; the 0–5
mastery scale; depth-leveled concept splits; per-unit source refresh
(bootstrap-only ingestion in v1 — a refresh mode is a v2 extension
hook); turn-count self-tracking.

---

## 3. Course directory layout

```
course/
  README.md            # pointer + course facts + resurrection preconditions
  SKILL.md             # copy of the session skill, made at bootstrap
  domain-map.md        # concept graph; frozen ids, machine-form errata
  plan.md              # units, statuses, counters, lifecycle fields
  knowledge-state.md   # one line per concept (the irreplaceable file)
  review-queue.md      # GENERATED by schedule.py — never hand-edited
  history.md           # rolling digest of old session logs
  log/                 # recent session logs; older ones distilled
  assets/unit-NN.md    # pre-authored teaching assets per unit
  sources/             # distilled source notes + index.md (bootstrap-time)
  artifact/            # optional; the user's work product
  scripts/schedule.py
  .session-inprogress  # transient sentinel; see §7 recovery
```

Copying SKILL.md in (like schedule.py) makes the directory fully
self-contained: README stays a thin pointer plus course-specific facts
(topic, terminal task, timezone, preconditions: python3 ≥3.9, git) and
never drifts from the real procedure.

Every state file opens with a 2–4 line format header describing its own
schema.

### domain-map.md

Header: topic, terminal task (verbatim), `research: yes|no` (was cutoff
knowledge adequate at bootstrap — one dial, recorded for provenance),
`timezone:` (IANA name; all "today" computations use it), session
budget, creation date. Then:

- **Concept blocks** (~0.75 × session count of them):

```
### inference-cost-curves
def: why serving LLMs is a marginal-cost business while training is fixed-cost
prereqs: [scaling-laws]
verify: quiz          # quiz | use | none
ceiling: solid        # solid (default) | retrievable (tacit concepts)
threshold: yes        # one of the 5-8 gateway concepts
misconceptions:
  M1: conflates marginal cost per token with average cost incl. training
  M2: assumes inference cost is static
```

- All prereq edges are hard: an edge means "cannot teach B before
  evidencing A." Soft "helps to know" relations are prose in the def
  line, not edges.
- Controversies / schools of thought (debate-exercise fuel).
- Source list (bound to units in plan.md).
- **Errata** (append-only) in machine-applicable form, merged over the
  frozen graph by every `schedule.py` run; concept ids are immutable:

```
erratum 2026-08-02: remove-edge scaling-laws -> inference-cost-curves
erratum 2026-08-02: note inference-cost-curves "def imprecise: see log/..."
```

### plan.md

```
course-status: active        # active | paused | dormant | closed
next-session: 14/30
attendance-streak: 6         # consecutive scheduled sessions attended
repair-pending: none         # concept-id, set by schedule.py
next-assets: authored        # pending | authored, per upcoming unit
```

Then unit blocks — question-framed, sized in sessions with ranges
*derived* from counts (never stored, so fractional repair sessions never
force renumbering):

```
## Unit 4: Why did the app layer capture so little value — and will it hold?
sessions: 4
concepts: [moat-taxonomy, switching-costs-ai, app-layer-margins]
keystones: [moat-taxonomy]         # 1-2 concepts; teach-back covers these
artifact-milestone: draft the "defensibility" memo section
sources: [unit-04-a, unit-04-b]
status: untouched                  # untouched | in-progress | taught | verified
```

The agent may reorder or split units with a logged reason; units are
never re-entered (interleaved application, §6, does the revisiting).
Every unit's final session is a teach-back.

### knowledge-state.md

Exactly one physical line per concept, `- ` delimited, label-parsed
(never positional), `note:` guaranteed last and right-bound parsed;
`|` is forbidden outside delimiters (the script strips it from notes):

```
- id: inference-cost-curves | verify: quiz | ceiling: solid | mastery: retrievable | status: active | last: 2026-07-18 | next: 2026-07-21 | interval: 3 | fails: 0 | note: hit M1 once
```

The agent writes *grade lines into the session log* (§5); only
`schedule.py` writes this file. Duplicate ids, multi-line records, and
unknown ids are hard errors surfaced by `check`.

### assets/unit-NN.md

Per concept: 2–4 quiz items (question + expected answer + distractors
drawn from the misconceptions; for concepts whose terminal use is
judgment, items are short case-judgments, not definition recall), a
worked example with a faded variant, a self-explanation prompt, and —
for `verify: use` concepts — 2–3 reusable application prompts. Per
keystone concept: a **teach-back rubric**: N required claims that must
appear, M named misconceptions that must not. Per unit: an
**interleaved problem set** — 3–5 problems spanning *earlier* units
where the learner must first identify which concept applies.

Assets for units 1–2 are authored at bootstrap. Authoring unit N+1's
assets is a mandatory step of unit N's final-session close (§5), gated
by plan.md's `next-assets` field: dispatch refuses to start a unit whose
assets are `pending`.

### sources/

Distilled notes only, created at bootstrap — **raw scraped content never
enters the course directory or any session context**. Each note: ≤800
words of key claims, numbers, quotable lines, plus URL and retrieval
date. Distillation is simultaneously compression, prompt-injection
quarantine, and provenance. Binding to units happens at curation time;
runtime retrieval is by name, never by search.

---

## 4. Bootstrap skill

Onboarding, ~5 user-taps:

1. **"What do you want to learn?"** → topic.
2. **Terminal-task guesses.** Three concrete end-states from what the
   agent knows about the user, plus a first-class escape hatch ("none of
   these — tell me in a sentence"); for a stranger: "two sentences: who
   are you, and why this topic?" The chosen terminal task becomes line 1
   of the map.
3. **Research ruling — announced, not asked.** One dial: is cutoff
   knowledge adequate to design this course (`research: no` — e.g.
   British history) or not (`research: yes` — e.g. AI economics, sweep
   reports/newsletters/lecture summaries now, at bootstrap, via whatever
   tools exist; adapters are optional recipes with graceful
   degradation). Stated in one line; overridable; never asked.
4. **Three path bundles** — angle × session count × artifact (or none) —
   with one-line trade-offs. Session counts 10/20/30/40/50; the agent
   recommends from the terminal task ("conversant" → 20, "produce
   professional work" → 40; default 30).
5. **Design studio (agent-only, async).** Research sweep if ruled;
   over-generate concept inventory; **backward-design prune** to ~0.75 ×
   session count (granularity rule: one concept = one session's
   teachable unit = one interpretable evidence judgment); tag 5–8
   threshold concepts; sequence within the DAG's slack (the thing the
   user came for early, heavy/light alternation, confusable pairs
   adjacent, units framed as questions — a topological sort is a
   validity check, never the sequencer); author unit 1–2 assets,
   rubrics, and interleaved problem sets; distill and bind sources;
   copy in schedule.py and SKILL.md; run `schedule.py check` (must
   pass, see §7); write everything.
6. **Default-accept gate.** The ~10-line unit sequence. "Reply *go*, or
   tell me what to change."
7. **Schedule setup.** Days/times; cron where the platform has it, else
   user-initiated (dispatch derives everything from state). Recommend
   ≥3 sessions/week with the reason (short review intervals stretch at
   lower cadence and early consolidation weakens).
8. `git init`, identity configured (or the skill commits with
   `git -c user.name=… -c user.email=…`), first commit.

**Session 1 is taught, then measured.** It opens with one striking
flagship idea from the terminal task — the user's first experience is
learning the thing they came for. Then the placement probe (5–8
questions across claimed prior knowledge), framed as "finding your
starting line," seeds initial state via `schedule.py seed`. Interview
claims are probe-selection hints, never grounds for seeded mastery.

---

## 5. Session skill

### Dispatch — explicit priority ladder, pure function of state

Read plan.md. First match wins for the session body:

1. `course-status` ≠ active → lifecycle handling only (§8), no session.
2. `repair-pending: <id>` → **repair session** (fractional number, e.g.
   `17r`: does not advance `next-session`, so unit ranges and the shot
   clock never shift). Body: reteach the concept from its assets via its
   worked example, then one application; a pass grade clears the flag.
   Max one repair per unit boundary.
3. Unit's final session → **teach-back session**.
4. Otherwise → **standard session**.

Composition rules (always): the **opening hook, retrieval block, and
close run in every session type** — modes replace only the middle. Every
7th session appends the **checkpoint report** to its close, whatever the
type.

### Prep step (agent-only, before the user is pinged)

1. **Recovery gate:** if `.session-inprogress` exists and the tree is
   dirty → prior session crashed mid-flight → `git reset --hard`,
   proceed fresh. If the sentinel is absent but the tree is dirty → a
   completed close whose commit failed → commit as-is, then proceed.
   Clean tree → normal. (Three cases, all decidable from structure.)
2. Write `.session-inprogress` (contains the session number — also the
   single-writer lock; a concurrent trigger seeing it stops).
3. `schedule.py check` (integrity, §7) and `schedule.py queue`.
4. Read: plan.md, knowledge-state.md, review-queue.md, current unit's
   asset file and named source notes, last 2 logs, history.md.
5. Draft the opening; send the nudge: curiosity hook + "today: X."

Grades are **not** applied during the session. The agent records
structured grade lines in the log draft as evidence comes in; state
mutates once, at close.

### Standard session body

1. **Hook** — a surprising claim or question tied to today's concept.
2. **Retrieval block** — the queued concepts (≤5), cold, answers may be
   one word or a short phrase (production, not recognition). **After
   every item, a mandatory corrective-feedback turn**: the stored
   answer, plus which named misconception a miss matched. Failed items
   get one re-probe later in the session. Each item yields a log grade
   line.
3. **New material** — the plan's next concept: worked example first
   (faded variants as the unit progresses), then Socratic questioning,
   explicit connection to two previously learned concepts, and one
   self-explanation prompt ("why is that true?"). ≤1 new concept per
   session, always.
4. **Apply** — one problem from the unit's **interleaved set** (spanning
   earlier units; the user must identify the applicable concept before
   applying it) or one artifact step. `verify: use` concepts surface
   here via their pre-authored application prompts — this is their
   spaced re-encounter; the agent never improvises their exercises.
5. **Tangents are budgeted, not banned:** the user may pull the session
   off-script for 1–2 exchanges; the agent then parks the thread as the
   log's open question, where it becomes future application fodder.

### Close — a fixed template, structure not memory

In order, always: write `log/{date}-{n}.md` (session number, what was
taught, grade lines, open question, ≤15 lines) → `schedule.py
commit-grades log/<file>` (applies every grade atomically: mastery
transitions, dates, statuses, repair-pending, queue regeneration) →
update plan.md counters (next-session, attendance-streak, unit status,
`next-assets`) → every ~10th log, distill the oldest 5 into history.md
and record `distilled-through: <n>` there → `git add -A && git commit`
→ delete `.session-inprogress`.

If the user never engages a nudge, no session occurred; nothing
advances; the next trigger re-delivers the same numbered session. The
lifecycle (§8) bounds how long that repeats.

### Teach-back session (unit boundary)

Middle section replaces new-material/apply: the agent plays a
smart-but-confused student and the user teaches **the unit's 1–2
keystone concepts only**. Voice notes and bulleted answers are welcome
(say so). Probes come from the misconception lists. Grading is against
the stored rubric — required claims present, named misconceptions absent
— never holistic impression. A rubric pass yields grade line
`pass`; **`solid` is only awarded on the *delayed* re-probe**: the next
session's retrieval block re-tests the keystone, and passing *that*
yields grade line `solid` (fluency today is not storage tomorrow). A
rubric fail on a concept that is a prereq edge into the next unit makes
`commit-grades` set `repair-pending`.

**The teach-back close additionally authors assets/unit-(N+1).md** —
quiz items with keys, rubrics, worked examples, interleaved problems —
from the map and existing sources, then flips `next-assets: authored`.
Dispatch will not start the next unit while it is `pending`; the gate is
structural, not remembered.

### Checkpoint report (every 7th session, appended to close)

10 lines from `schedule.py report` plus agent prose: progress vs shot
clock, attendance streak, decaying concepts (script-computed), plateaued
concepts with the agent's best guess ("you decide"), plan changes +
reasons, one genuinely interesting question as the re-engagement hook.
**Adjudication flow-back:** the user's verdict on a plateaued concept —
"count it" (grade line `pass` with note), "keep trying" (fails counter
reset), "drop it" (`schedule.py set-verify <id> none`) — is recorded at
the next close. **Reprune offer:** if the user is ≥2 weeks behind their
chosen cadence, the checkpoint offers to shrink the course — re-run the
backward-design prune, drop non-threshold untaught concepts, keep every
interval on what remains — so a stalled user finishes *something*
(Principle 5, mid-course).

---

## 6. Mastery, evidence, verification

- **Three evidence-anchored bands** (replacing 0–5):
  - `exposed` — taught, no retrieval evidence yet.
  - `retrievable` — passed cued/cold retrieval with corrective feedback.
  - `solid` — transfers cold: delayed rubric-passed teach-back, or an
    application/artifact judged against stored criteria.
- Mechanisms: `verify: quiz` (retrieval against stored keys),
  `verify: use` (evidence only through application/teach-back; never
  quizzed as recall), `verify: none` (exposure, untracked).
  `ceiling: retrievable` marks tacit/judgment concepts — the system is
  forbidden from demanding stronger evidence than "conversant," because
  stronger evidence doesn't exist; they get pre-authored re-encounters,
  not re-tests.
- All transitions live in `schedule.py`'s stated table; the agent
  supplies only grade lines with notes. Evidence is named in the note.
- **Failure steps back one interval** (16→7), never to the floor;
  repeated consecutive failure (`fails: 3`) → `status: plateaued`,
  surfaced at the next checkpoint. Never loop.

## 7. schedule.py — the deterministic core

Verbs:

```
check                      # integrity: DAG (errata-merged); cross-file id
                           #   agreement (map = knowledge-state = plan =
                           #   assets; no orphans/dupes/multi-line records);
                           #   concept count in band; 5-8 threshold tags;
                           #   every startable unit's assets exist with >=1
                           #   key per quiz concept. Run at bootstrap AND
                           #   every prep. Loud failure.
queue                      # regenerate review-queue.md: status active,
                           #   next <= today (course timezone), cap 5,
                           #   oldest first, overflow rolls
seed <id> <band>           # calibration: set initial mastery + first date
commit-grades <logfile>    # parse grade lines; apply the transition table,
                           #   intervals, statuses, repair-pending; guarded
                           #   by session number (re-running is a no-op)
set-verify <id> <mech>     # adjudication verdicts
report                     # progress, decaying, plateaued — for checkpoints
```

Scheduling: intervals 1 → 3 → 7 → 16 → 35 → **90 → 180** days. There is
no permanent retirement while the course runs: post-35 passes simply
stretch toward the retention horizon. Due-ness uses the course timezone
via `zoneinfo`. Unattended days never reset anything. Queue cap 5,
oldest first — absence produces a longer tail, never a wall.

**Course terminal state:** all units taught/verified and the counter
exhausted → **graduation is a moment**: the capstone (finished artifact
or a final cumulative teach-back) is the closing act; the course report
is the trophy. *Then* maintenance is the default continuation — one
short review session per ~2 weeks servicing the 90/180-day tail — with
opt-out, framed as "keeping it, not still studying it."

## 8. Lifecycle (adherence machinery)

- `course-status: active | paused | dormant | closed` in plan.md.
- After 3 consecutive silent triggers → `paused`, one low-shame message
  ("say *resume* whenever — everything keeps"), pings drop to at most
  fortnightly, each built on the last checkpoint's hook question.
- `resume` → re-entry session: warm, review-only, no new material, no
  backlog framing ("here's where we are" not "here's what you owe").
- An explicit quit → `closed` + a graceful exit report (what was
  learned, what's fragile). Closing is a recorded outcome, not a
  failure state.
- Attendance streak (not correctness streak) is the one positive
  counter, shown at closes and checkpoints.

## 9. Recovery, portability, packaging

- The course directory is a git repo; every close is a commit; a private
  remote is the user's one optional backup step.
- Resurrection preconditions, stated in README: python3 ≥3.9, git. The
  directory contains SKILL.md and schedule.py, so a fresh agent needs
  nothing else. The resurrection test is run once at bootstrap for real:
  fresh context, directory only, "run the next session."
- Skill package:

```
tutor/
  SKILL.md             # session dispatch + flows, <2k words
  bootstrap.md         # the §4 procedure
  scripts/schedule.py
  templates/           # every state file, with format headers
  example-course/      # one complete tiny course — format documentation
                       #   an LLM actually learns from
```

- No external service dependencies anywhere in the session path.
  Ingestion adapters are optional bootstrap recipes with degradation
  ("or paste a transcript").

## 10. Invariants

1. `next-session` only increments; repairs are fractional; nothing
   mastery-related stalls the plan except one repair per unit boundary.
2. Mastery moves only via `schedule.py`'s transition table on grade
   lines; grades come only from stored keys and rubrics; evidence is
   named in the note.
3. Weak concepts never block; they persist in the capped queue until
   evidenced, plateaued (→ human adjudication), or the course closes.
4. The agent never does date arithmetic, never decides mastery moves,
   never improvises grading criteria or exercises for `use` concepts.
5. All state is human-legible markdown inside the course directory. No
   hidden state. The resurrection test must pass.
6. Raw external content never enters the directory or any session
   context; distilled, dated notes only; ingestion happens only at
   bootstrap.
7. Concept ids are immutable; graph corrections are machine-form errata,
   merged by every script run.
8. State mutates once per session, at the close, then commits; the
   sentinel + dirty-tree rules make every crash window decidable.
9. Missed days cost calendar time — never progress, never intervals.
   Every retrieval ends with corrective feedback. Failure steps back
   one interval, never to zero.
10. Compression is pruning — at bootstrap and at reprune. Content is
    never covered faster.

## 11. Defaults

| Parameter | Default |
|---|---|
| Course size | 30 sessions (10/20/30/40/50) |
| Concept budget | ~0.75 × sessions |
| Session length | ~15 min, calibrated down from pilot data |
| Cadence | user-chosen days; ≥3/week recommended |
| Unit size | 3–5 sessions; final = teach-back on 1–2 keystones |
| Checkpoint | every 7th session |
| Intervals | 1/3/7/16/35/90/180; fail steps back one |
| Queue cap | 5/session, oldest first |
| New material | ≤1 concept/session |
| Plateau | 3 consecutive fails → checkpoint adjudication |
| Auto-pause | after 3 silent triggers; fortnightly ping in paused |
| Reprune trigger | ≥2 weeks behind chosen cadence, offered at checkpoint |
| Source notes | ≤800 words, ≤4/unit, bootstrap-time only |
| Threshold concepts | 5–8 per course |
| Tangent budget | 1–2 exchanges, then parked as open question |

## 12. Open questions

1. Turn/length calibration — measure real elapsed time in the pilot;
   default conservative.
2. Asset quality at teach-back-close authoring (weaker context than
   bootstrap) — inspect unit-3+ assets in the pilot.
3. Placement probe sizing for users with deep partial knowledge.
4. Whether `solid` via artifact evidence needs its own rubric form.
5. The novice default-accept paradox (least able to critique the
   syllabus are most likely to accept it) — does the reprune loop
   sufficiently correct bad bootstraps?
6. v2 extension: per-unit source refresh as a separate tool-bearing
   mode, for fast-moving fields beyond the pilot.

## 13. Roadmap

1. `schedule.py` (transition table, all verbs) + templates +
   example-course — the deterministic layer, test-first.
2. SKILL.md + bootstrap.md against the templates.
3. Pilot: bootstrap the AI-economics course for real; run 3 sessions.
4. Resurrection test from the pilot directory in a fresh context.
5. Calibrate turn budgets and asset quality from pilot friction; then
   package for export.
