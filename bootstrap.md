---
name: aristotle-bootstrap
description: Create a new Aristotle course — interview the user briefly, design a curriculum by backward design, author teaching assets, and write the course directory. Run once per course. To run a session in an existing course, read SKILL.md instead.
---

# Aristotle — bootstrap

You are designing a course. This is the one place with research tools and
the one place that spends real tokens: **everything you can author now,
you must author now**, because runtime is short and a session must never
improvise an evidence standard.

**User-minutes are scarce; your tokens are not.** Onboarding is about
five taps. Don't interview at length, and don't ask anything you can
decide yourself and announce.

The exemplars below are **shape, not wording**. Write your own.

## Step 1 — Topic

> "What do you want to learn?"

## Step 2 — Terminal task (one tap)

Offer three concrete end-states — things they'll be able to *do*, not
motivation categories — plus a first-class escape hatch:

> "AI economics — got it. Guessing at your angle: **(a)** pressure-test
> moat and margin claims in diligence, **(b)** write investable theses
> about where value accrues, **(c)** hold your own on unit economics with
> technical founders. Or tell me in a sentence — none of these is fine."

If you know nothing about them, ask who they are and why this topic in
the same breath as offering the three, so they can answer with one tap if
they want to.

The chosen terminal task is **line 1 of the map**. Every concept must
justify its seat by tracing to it. Two courses on one topic with
different terminal tasks share maybe half their concepts.

## Step 3 — Research ruling (announced, not asked)

Decide whether your training knowledge is enough to *design* this course,
and say so in one line. British history, thermodynamics, Roman law →
`research: no`. AI economics, a live regulatory regime, anything moving
monthly → `research: yes`, and sweep now.

> "This field moves fast enough that I'll pull current sources — my
> training data alone would shortchange you."

They can override; they are never asked to decide. Ingestion happens
**only here**: distill into `sources/` notes (≤800 words each: key
claims, numbers, quotable lines, URL, retrieval date). Raw scraped text
never enters the course directory. If no research tool is available, ask
for a link or a pasted transcript, or proceed on training knowledge and
say that you did.

For material that only exists as a talk or lecture, `tools/venice.py`
will actually watch a public YouTube video and answer questions about it:

```
python3 tools/venice.py --video <url> "the distillation prompt"
```

Distill the result into a `sources/` note like any other source. Do not
paste a video URL into an ordinary prompt — the model will answer from
training data for famous videos and disclaim access for the rest.

## Step 4 — Three paths (one tap)

Three coherent bundles — angle × session count × artifact — each with a
one-line trade-off. Counts are 10/20/30/40/50; recommend one from the
terminal task ("conversant" → 20, "produce professional work" → 40;
default 30).

> "**A — 20, practitioner-first.** Straight to diagnosis; artifact is a
> diligence checklist you'll use. Thin on theory.
> **B — 30, balanced.** Mechanisms *and* practice; artifact is a written
> thesis on one part of the stack.
> **C — 40, foundations-first.** You'll derive the arguments, not just
> use them. Slowest to feel useful."

Choosing between three whole bundles is far easier than answering six
abstract questions.

## Step 5 — Design studio

**First, tell them what's happening and roughly how long.** This is the
longest silence in the whole product and they are holding a phone:

> "Give me about twenty minutes to pull sources and build the course —
> I'll message you the outline when it's ready."

Then work, in order:

1. **Research sweep** if ruled. Distill into `sources/`.
2. **Over-generate** a candidate concept inventory — everything a course
   on this could contain.
3. **Backward-design prune** to `~0.75 ×` the session count. Every
   survivor traces to the terminal task; everything else is cut, however
   interesting. *Compression is pruning — a 20-session course is fewer
   concepts, never the same concepts rushed.*
   - Granularity: one concept = one session's teachable unit = one
     interpretable evidence judgment. If no single retrieval question
     separates a strong learner from a weak one, resize it.
4. **Tag 5–8 threshold concepts** — the transformative reframings. They
   get generous time and multiple angles. `reprune` will refuse to drop
   them later, so tag deliberately.
5. **Sequence** within the dependency graph's slack. The graph says
   what's *valid*; craft picks which valid order:
   - the thing they came for goes early — motivation beats logical
     purity, and you can backfill theory once they care
   - alternate heavy and light sessions
   - put confusable pairs adjacent so they get contrasted, not blurred
   - **frame every unit as a question**, never a topic
6. **Do the arithmetic, or the course won't fit.** Each unit needs
   `len(concepts) + 1` sessions — one per concept at one new concept per
   session, plus the teach-back — and **no more**: a unit padded past its
   material forces the extra sessions to manufacture recall, which is
   how a course ends up re-asking its own questions. Then distribute the
   review, don't stack it at the end:
   - after every 2–3 units, insert a `## Review: <title>` block
     (`sessions: N`, no concepts, no assets) — mixed retrieval reaching
     back across *all* prior units, run per SKILL.md's `review` type
   - leave **at least one session** at the very end unclaimed: the
     terminal synthesis (artifact-centered), not a second recall block —
     two adjacent review sessions over the same material are not spaced,
     they are the same session twice
   `check` enforces the floor and the fit; if it doesn't fit, cut
   concepts, not sessions.
7. **Author assets for ALL units now** per `templates/assets-unit.md` —
   the author/tutor asymmetry: the agent bootstrapping a course is
   usually running with more context, more sources, and often a
   stronger model than the agent that will teach session 23 on a
   Tuesday. Compile once, execute many: the more judgment you pre-bake
   into assets, the less the runtime tutor improvises. Date every
   perishable figure ("as of <month year>") — the tutor's job at teach
   time is to REFRESH numbers, never to redesign concepts. (Authoring
   only units 1–2 and leaving the rest to `author-after-close` is the
   fallback for when bootstrap time is genuinely short — accept that
   those assets will be written by whatever model happens to be
   running that day.)
   Give every keystone at least one `misconceptions:` entry in the map —
   a keystone with none has nothing for its rubric to warn against.
8. **Write the directory** (§6), then run `S check` and fix everything it
   reports. It validates the DAG, cross-file ids, the session arithmetic,
   and asset quality.

## Step 6 — Write the course directory

A course directory must be self-sufficient — that is the resurrection
test. Copy in `scripts/schedule.py`, **`SKILL.md`, `checkpoint.md`, and
`templates/`**, and write a `.gitignore`:

```
course/
  README.md  domain-map.md  plan.md  knowledge-state.md
  history.md  review-queue.md  .gitignore
  log/  assets/  sources/  artifact/
  scripts/  templates/  SKILL.md  checkpoint.md
```

`.gitignore` must contain `.session-inprogress`, `*.tmp`, `__pycache__/`.

`knowledge-state.md`: one row per concept, all `status: untaught`. Do
**not** seed from what they claimed in the interview — self-report is
exactly the input evidence-gating exists to distrust.

`README.md` states what the directory is, that `python3 ≥3.9` and `git`
are required, and how an agent resumes: *read SKILL.md, then run
`python3 scripts/schedule.py --course . begin`.*

## Step 7 — Default-accept gate (one tap)

Show the ~10-line unit sequence — question-framed titles and session
counts, not the concept list.

> "Reply **go**, or tell me what to change."

Most people say go. That's fine: the plan is mutable and checkpoints are
the correction loop.

## Step 8 — Schedule and first commit

Ask for days and times, then **read `scheduling.md`** — it covers
cadence choice, the nudge/session split, and the wiring that keeps a
scheduled course healing itself.

Record `cadence:` (sessions per week) in `plan.md`. The lifecycle math
needs it in the directory, not in the scheduler's config — that is what
keeps the course portable.

Recommend **>=3 sessions/week**, with the reason: below that the short
review intervals stretch and early consolidation measurably weakens.
Daily is fine; weekly is a different product and wants a shorter course.

Then `git init` and commit (or just run `S begin`, which initialises the
repo if it isn't one).

## Session 1 — teach first, then measure

**Never open a course with an exam.** First impressions decide whether
there's a session 2.

1. **Teach one striking idea** from the terminal task — the single most
   interesting thing in the whole course. They came for this; give it to
   them in the first five minutes.
2. **Then a short placement probe**, framed as orientation: *"Let me find
   your starting line so I don't waste your time on what you've got."*
   Three to five questions, not a battery.
3. Seed the results — evidence, not self-report:
   ```
   S seed <concept-id> <none|exposed|retrievable>
   ```
   `retrievable` schedules a real interval, so a concept they already
   know won't come back tomorrow.
4. **Write the baseline.** Append to `history.md` under `## baseline`:
   one probe question and their answer, both verbatim. Graduation shows
   them this delta; it is the payoff for the whole course, and nothing
   else preserves it.
5. Close as normal. Grade the flagship concept `taught`.
