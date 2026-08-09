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
finding ten defects, three of them live in production. That is the
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

## The bootstrap verdict

Given one uninterrupted turn and a complete brief, GPT-5.6-Codex built
a course that passes `check` clean and would be a genuinely good thing
to study from:

- three units, all question-framed, each sized exactly `concepts + 1`;
- a `## Review:` block between units 2 and 3 and the final session left
  for synthesis — the distributed shape the pilot argued for, produced
  without being asked;
- quiz items with answer keys and distractors mapped to real
  misconception ids, worked examples with concrete numbers (*"Dough A
  is 26 C, risen 50%, side bubbles… shape A; continue bulk on B"*),
  apply prompts that demand judgment rather than recall;
- rubrics whose claims are the actual load-bearing ideas;
- all seven concepts left `untaught` — it did not seed from what the
  learner claimed, which is the one instruction most tempting to
  ignore;
- a `history.md` that says, in as many words, *"No baseline answer has
  been invented during bootstrap."*

Two design flaws, both now guarded in `bootstrap.md`: it tagged all
seven concepts `threshold: yes` and made every concept a keystone
(tagging everything is tagging nothing), and it wrote a plan section
the scheduler silently ignores (defect 10).

The conclusion that matters for portability: **the procedure transferred
to a different model family without adaptation.** What did not transfer
was everything outside the procedure files.

## The session verdict

The course was then taught, twice — once abandoned mid-lesson on
purpose, then resumed. Every load-bearing behaviour held:

- `begin` dispatched `placement`, and the tutor bounced to the Session-1
  procedure instead of quizzing cold. It opened with the idea, not an
  exam: *"A dense loaf is not a diagnosis; it's only a symptom."*
- Told the learner's guess was "not enough time," it validated the
  guess and then corrected the frame — *"even excessive fermentation
  makes dough too weak to retain gas"* — which is `M2` in its own map,
  reached without being prompted with the id.
- On resume, `recover: reset` fired with the abandoned-session NOTE, and
  the tutor said *"I'm recovering it without replaying the old opening;
  I'll first check what stuck"* — then asked exactly that. The
  don't-re-teach-verbatim instruction worked on a model that had never
  seen it before.
- **It closed itself.** No goodbye was given and none was waited for —
  the defect the live pilot was built to fix did not recur here.
- The log it wrote is correct in every field that matters: a `taught`
  grade with evidence in the note, a real `## asked` ledger mixing bank
  item ids (`fermentation-readiness.apply1`) with free-text case
  signatures, and an open question worth reopening on (*"How can two
  equally dense loaves require opposite corrections?"*).
- Placement seeded from evidence, not self-report: `retrievable` for
  what the learner demonstrated, `exposed` and `none` elsewhere — and
  the verbatim baseline went into `history.md` for the graduation
  delta.

End to end on a foreign model, with no human in the loop but a scripted
learner: bootstrap → course → session → abandonment → recovery →
teach → close → state advance → commit.

## The ten defects

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

**6. Bootstrap never said where a course lives.**
Step 6 said "write the course directory" without saying *where*. The
agent chose its own path and ignored the one it had been given. The
path is load-bearing — the scheduler, the nudge job, and every future
session must find it — so a course written somewhere nobody recorded is
a course that runs once.
*Fix:* Step 6 states the convention and requires reporting the absolute
path back to the user.

**7. "Schedule the course" was read as "make a calendar event".**
Told to schedule, the agent reached for a Google Calendar skill. A
calendar event reminds a human; what a course needs is a job that
fires, heals state, and nudges whether or not anyone remembered.
*Fix:* `scheduling.md` says so in its first paragraph, where the agent
reads it.

**8. The longest stretch of work had no durable anchor.**
Partway through the design studio the agent lost the interview answers
to context compaction — then guessed the topic back from directory
mtimes and contradicted itself on the session count (20 sessions in one
message, 30 in the next). Everything the user had said lived only in
the conversation.
*Fix:* Step 5 now writes `brief.md` — topic, terminal task, counts,
cadence, path — *before* the studio begins. Anything a later you would
have to re-ask the user for belongs on disk before the long work
starts. (Notably, the recovery it improvised — reading the filesystem —
is the resurrection property half-working. Give it something correct to
read and it works fully.)

**9. A plan section can claim sessions the scheduler ignores.**
The bootstrap wrote `## Terminal synthesis (session 12)` with
`sessions: 1`. Only `Unit N:` and `Review:` blocks consume sessions, so
the line was dropped — harmless at that count, silently wrong at any
other, and invisible either way.
*Fix:* `course_warnings()` flags any non-unit section declaring
`sessions:`.

**10. "Isolated" profiles are not isolated.**
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
