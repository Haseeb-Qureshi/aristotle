# Course: Espresso extraction

An **elenchus** course directory. Everything about this course — the
curriculum, what the learner knows, every session's record — is in these
files. There is no state anywhere else.

**Terminal task:** diagnose a bad shot from taste and timing alone, and
name the single variable to change next.

## Resuming this course (any agent, any machine)

Requires `python3` ≥ 3.9 and `git`.

1. Read `SKILL.md` in this directory — it is the complete session procedure.
2. `python3 scripts/schedule.py --course . recover`
3. Follow SKILL.md's dispatch table.

That's the whole handoff. If an agent can't run the next session from
this directory alone, something is missing and should be fixed here.

## What's what

| Path | |
|---|---|
| `domain-map.md` | concept graph + misconceptions; frozen, errata append-only |
| `plan.md` | units, counters, lifecycle state |
| `knowledge-state.md` | what the learner knows — written only by schedule.py |
| `review-queue.md` | generated; what's due now |
| `assets/` | pre-authored quiz keys, examples, rubrics, interleaved problems |
| `sources/` | distilled source notes (never raw scraped text) |
| `log/` + `history.md` | session records, rotated and distilled |

## Note

This is the **bundled example** shipped with elenchus: a real, valid,
9-session course kept deliberately small so the file formats are readable
end to end. It is mid-flight — 4 sessions done, unit 2 in progress — so
every state a live course reaches is visible somewhere in here.
