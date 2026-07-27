# Course: Espresso extraction

An **Aristotle** course directory. Everything about this course — the
curriculum, what the learner knows, every session's record — is in these
files. There is no state anywhere else.

**Terminal task:** diagnose a bad shot from taste and timing alone, and
name the single variable to change next.

## Resuming this course (any agent, any machine)

Requires `python3` ≥ 3.9 and `git`.

1. Read `SKILL.md` in this directory — it is the complete session
   procedure.
2. ```
   python3 scripts/schedule.py --course . begin
   ```
   It initialises the git repo if this isn't one yet, recovers from any
   interrupted session, and prints which session to run and what to quiz.

That's the whole handoff. If an agent can't run the next session from
this directory alone, something is missing and should be fixed here.

## What's what

| Path | |
|---|---|
| `domain-map.md` | concept graph + misconceptions; frozen, errata append-only |
| `plan.md` | units, counters, lifecycle state |
| `knowledge-state.md` | what the learner knows — written only by schedule.py |
| `review-queue.md` | generated; what's due now |
| `assets/` | pre-authored quiz keys, worked examples, rubrics, interleaved problems |
| `sources/` | distilled source notes (never raw scraped text) |
| `log/` | one short record per session |
| `history.md` | the session-1 baseline, and long-lived notes |
| `SKILL.md`, `checkpoint.md`, `templates/` | the procedure, carried with the course |

## Note

This is the **bundled example** shipped with Aristotle: a real, valid,
12-session course kept deliberately small so the file formats are
readable end to end. It is mid-flight — 5 sessions done, unit 1 taught,
unit 2 in progress, one concept carrying a recorded miss — so most states
a live course reaches are visible somewhere in here.
