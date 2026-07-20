---
name: elenchus-bootstrap
description: Create a new elenchus course — interview the user briefly, design a curriculum by backward design, author teaching assets, and write the course directory. Run once per course. To run a session in an existing course, read SKILL.md instead.
---

# elenchus — bootstrap

You are designing a course. This is the one place with research tools and
the one place that spends real tokens: **everything you can author now,
you must author now**, because runtime is fragile and a session must never
improvise an evidence standard.

**Budget discipline: user-minutes are scarce, your tokens are not.**
Onboarding is ~5 taps. Do not interview at length. Do not ask the user
anything you can decide yourself and announce.

## Step 1 — Topic

> "What do you want to learn?"

## Step 2 — Terminal task (one tap)

Offer **three concrete end-states** — things they'll be able to *do*, not
motivation categories — using whatever you know about them. Always include
a first-class escape hatch.

> "AI economics — got it. Guessing at your angle:
> **(a)** pressure-test AI startups' moat and margin claims in diligence,
> **(b)** write investable theses about where value accrues in the stack,
> **(c)** hold your own on unit economics with technical founders.
> Or tell me in a sentence — none of these is fine."

If you know nothing about them: *"Two sentences: who are you, and why this
topic?"* — then offer the three.

The chosen terminal task is **line 1 of the map**. Every concept must
justify its seat by tracing to it. Two courses on the same topic with
different terminal tasks share maybe half their concepts.

## Step 3 — Research ruling (announced, not asked)

Decide yourself whether your training knowledge is adequate to *design*
this course, and say so in one line:

- British history, thermodynamics, Roman law → `research: no`. Skip the
  web; bootstrap is faster and cheaper.
- AI economics, a current regulatory regime, anything moving monthly →
  `research: yes`. Sweep reports, newsletters, lecture summaries **now**.

> "This field moves fast enough that I'll pull current sources — my
> training data alone would shortchange you."

They can override. They are never asked to decide. Ingestion happens
**only here**: distill everything into `sources/` notes (≤800 words, key
claims, numbers, quotable lines, URL, retrieval date). Raw scraped text
never enters the course directory. If a research tool isn't available,
degrade gracefully — ask for a link or a pasted transcript, or proceed on
training knowledge and say you did.

## Step 4 — Three paths (one tap)

Offer three coherent **bundles** — angle × session count × artifact — each
with a one-line trade-off. Session counts: 10/20/30/40/50; recommend one
derived from the terminal task ("conversant" → 20, "produce professional
work" → 40; default 30).

> "**A — 20 sessions, practitioner-first.** Straight to diagnosis; artifact
> is a diligence checklist you'll actually use. Thin on theory.
> **B — 30 sessions, balanced.** The mechanisms *and* the practice; artifact
> is a written thesis on one part of the stack.
> **C — 40 sessions, foundations-first.** You'll be able to derive the
> arguments, not just use them. Slowest to feel useful."

Choosing between three whole bundles is far easier than answering six
abstract questions.

## Step 5 — Design studio (agent-only, no user contact)

This is the work. In order:

1. **Research sweep** if ruled. Distill into `sources/`.
2. **Over-generate** a candidate concept inventory — everything a course
   on this could contain.
3. **Backward-design prune** to `~0.75 × session count`. Every survivor
   traces to the terminal task; everything else is cut, however
   interesting. *Compression is pruning — a 20-session course is fewer
   concepts, never the same concepts rushed.*
   - Granularity: one concept = one session's teachable unit = one
     interpretable evidence judgment. If no single retrieval question
     separates a strong learner from a weak one, resize it.
4. **Tag 5–8 threshold concepts** — the transformative reframings. They
   get generous time and multiple angles.
5. **Sequence** within the dependency graph's slack. The graph tells you
   what's *valid*; craft picks which valid order:
   - the thing they came for goes early (motivation beats logical purity —
     backfill theory once they care)
   - alternate heavy and light sessions
   - place confusable pairs adjacent so they get contrasted, not blurred
   - **frame every unit as a question**, never a topic
6. **Author assets for units 1–2** per `templates/assets-unit.md`: quiz
   items *with answer keys*, distractors drawn from the map's
   misconceptions, worked + faded examples, self-explanation prompts,
   application prompts for every `verify: use` concept, a rubric per
   keystone, and ≥3 interleaved problems. `check` validates all of this
   structurally — placeholder work will fail.
7. **Write the directory** (§6), then:
   ```
   python3 scripts/schedule.py --course $C check
   ```
   Fix everything it reports. It validates the DAG, cross-file id
   agreement, and asset quality.

## Step 6 — Write the course directory

Copy `templates/*` into place and fill them; copy in `scripts/schedule.py`
**and `SKILL.md`** (a course directory must be self-sufficient — that's
the resurrection test). Then:

```
course/
  README.md  domain-map.md  plan.md  knowledge-state.md
  history.md  log/  assets/  sources/  artifact/  scripts/  SKILL.md
```

`knowledge-state.md`: one row per concept, all `status: untaught`,
`mastery: none`. Do **not** seed from what they claimed in the interview —
self-report is exactly the input evidence-gating exists to distrust.

README.md must state: what this directory is, that `python3 ≥3.9` and
`git` are required, and how an agent resumes (`read SKILL.md, then run
scripts/schedule.py --course . recover`).

## Step 7 — Default-accept gate (one tap)

Show the **~10-line unit sequence** — the question-framed unit titles and
session counts. Not the concept list.

> "Reply **go**, or tell me what to change."

Most people say go. That's fine: the plan is mutable, and checkpoints are
the correction loop.

## Step 8 — Schedule and first commit

Ask for days/times. Create the platform's scheduled trigger if it has one;
otherwise the skill works user-initiated (dispatch derives everything from
state). Record `cadence:` in `plan.md` — the lifecycle math needs it in
the directory, not in cron config.

Recommend **≥3 sessions/week**, with the reason: at ≤2/week the short
review intervals stretch and early consolidation measurably weakens.

Then `git init`, configure identity, and commit.

## Session 1 — teach first, then measure

**Never open a course with an exam.** First impressions decide whether
there's a session 2.

1. **Teach one striking idea** from the terminal task — the single most
   interesting thing in the whole course. They came for this. Give it to
   them in the first five minutes.
2. **Then the placement probe**, framed as orientation: *"Let me find your
   starting line so I don't waste your time on things you've got."* 5–8
   questions across the concepts they might plausibly know.
3. Seed the results — evidence, not self-report:
   ```
   S seed <concept-id> <none|exposed|retrievable>
   ```
4. Close as normal (log, `commit-grades`, plan update, commit). Grade the
   flagship concept `taught`.

## Finally — run the resurrection test for real

Open a **fresh context** with only the course directory and no skill
installed, and ask it to run session 2. If it can't, the directory is
missing something — fix that before handing the course to anyone.
