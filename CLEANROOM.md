# The clean-room test

*A fourth review, after three critique panels and a live pilot: hand the
skill to a different model, on a different harness, with no context —
and see what breaks.*

**Setup (2026-08-09).** A dedicated Hermes profile (`tutorlab`) running
**GPT-5.6-Codex** instead of the Claude models this system was built
and piloted on. One skill installed. Telegram credentials stripped so
the instance could not message the operator or contend with the running
gateway. A fresh workspace. The instruction was a sentence an ordinary
user would type — *"set me up a proper course on sourdough"* — with no
mention of Aristotle, this repo, or any file.

The test was meant to evaluate teaching. It never got there before
finding six defects, three of them live in production. That is the
result worth recording: **the portability failures were not in the
pedagogy, they were in everything around it.**

## What the harness got right

Skill discovery worked cold. A plain request found `aristotle` by its
frontmatter description alone, read `SKILL.md`, correctly bounced to
`bootstrap.md`, and executed the interview steps by the book: three
concrete end-states with a recommendation and an escape hatch, then the
research ruling *announced* rather than asked. It did this while its
host personality file insisted it was a single-purpose bot that should
refuse anything outside Portuguese and fintech lessons. The procedure
files out-argued the system prompt.

## The six defects

**1. Skill roots drift, and the stale copy can win.**
The runtime loaded `~/.agents/skills/aristotle` — a six-day-old copy
with no question ledger, no review blocks, no elapsed-gap rule — while
three current copies sat in other roots. Agents resolve skills from
whichever root the loader reaches first; hand-copying to N locations
guarantees one is stale and gives no signal which one ran.
*Fix:* [`install.sh`](install.sh) syncs every root; `--check` reports
drift and exits non-zero.

**2. The runtime agent had patched the skill in place.**
After being called out for repeating questions, the production tutor
wrote its own reference file into its skill install — mandating a
`## prompts` log section. The engine parses `## asked`. A tutor
following it would have written a ledger the parser silently ignored,
reintroducing the exact defect the ledger exists to prevent, invisibly.
*Fix:* adopted into [`references/`](references) with the grammar
corrected. The general lesson: **skill installs are writable and agents
will write to them.** Check for agent-authored files before syncing
over them — and prefer adopting to deleting, because the runtime is
often right about the failure it just lived through.

**3. The example course taught the shape the pilot disproved.**
`example-course/` still had no review blocks, two stacked terminal
consolidation sessions, and assets for only two of three units — the
pre-pilot pattern that `bootstrap.md` now forbids. It is the highest
fidelity artifact an agent imitates, and it contradicted the
instructions.
*Fix:* rebuilt to the current shape. Exemplars are documentation; they
rot like documentation.

**4. Documented rules that nothing enforced were violated — by us.**
Grading two real courses against `bootstrap.md` found the live course
missing a `README.md` (a stranger agent had no entry point) and a
`history.md` baseline (graduation had no delta to show), plus a padded
unit. Both courses were "passing" `check`.
*Fix:* `course_warnings()` — advisory `warn:` lines on padded units,
missing review blocks, unauthored assets, keystones with no
misconceptions, and missing scaffolding. Advisory by construction: bad
shape is not corrupt state, and a running course must never stop
because its design is dated.

**5. A dangling instruction shipped the same day it was written.**
`SKILL.md` gained a pointer to `references/`, but Step 6's copy list
did not — so every newly bootstrapped course would have carried an
instruction pointing at a file it did not contain.
*Fix:* Step 6 copies `references/`, and now says explicitly not to seed
a course from `example-course/`'s state files.

**6. "Isolated" profiles are not isolated.**
`hermes profile create --clone` copies `SOUL.md` and `memories/`, so
the clean-room instance began the test believing it was the operator's
personal bot and reporting the wrong course topic from a memory file.
Not an Aristotle bug, but a testing hazard worth writing down: verify
your clean room is clean before trusting what it tells you.

## The generalisation

Round 2 found defects in interfaces that existed only as prose. Round 3
found the same disease in code — procedure files promising transitions
no line performed. The pilot found what simulation could not, because
the simulator controlled the transition. This round found the layer
below all of them:

**A skill is not its repository. It is whichever copy the loader
happens to find, on whatever machine, patched by whatever agent ran
last.** Correctness in the repo buys nothing if the installed artifact
has drifted, the exemplar contradicts the instructions, or the runtime
has edited the procedure underneath you. Distribution is part of the
design surface, and until this round it had no owner, no test, and no
command.
