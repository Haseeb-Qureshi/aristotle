# Aristotle

*Alexander had Aristotle. You have a phone.*

A chat-based AI tutor that teaches you one topic over a finite course of
short, scheduled sessions — designed for **long-term retention first**,
completion second, coverage third. The agent is stateless; the entire
course lives in one human-readable markdown directory you can read, edit,
git-push, and resurrect on any machine, any platform, any model.

**Status: piloted.** Three adversarial review rounds (two against the
spec, one against the built system), then a real course with a real
learner on a real schedule. The pilot immediately found a defect no
review round had: the tutor taught an excellent lesson and never closed
it, because **the learner never says goodbye** — there is no terminal
event in a chat, so a tutor that waits for one waits forever. Fixed in
`SKILL.md` §4 (the tutor owns the close trigger) and `scheduling.md`
(the nudge job reconciles a missed close from history).

## Install

```
./install.sh            # sync the skill everywhere an agent might load it
./install.sh --check    # report drift, change nothing
```

Agents load skills from several roots (`~/.agents/skills`,
`~/.hermes/skills`, `~/.claude/skills`), and whichever the loader finds
first is the one that runs. Hand-copying drifted them apart until a
runtime loaded a six-day-old procedure while three current copies sat
beside it — so syncing is a script, and `--check` belongs in any
pre-flight. Course directories are not installs: they receive these
files at bootstrap and own them afterwards.

## How it works

- **Map, plan, session.** A one-time bootstrap interviews you (~5 taps),
  researches the domain if it's a moving target, and writes a frozen
  concept graph (`domain-map.md`), a mutable syllabus (`plan.md`), and
  pre-authored teaching assets — quiz keys, teach-back rubrics, worked
  examples, misconception distractors. Sessions are generated from those.
- **Forward motion is unconditional; verification is advisory.** The
  course advances on a session counter, never blocked by mastery. Weak
  concepts persist in a capped spaced-review queue (1/3/7/16/35/90/180
  days) until evidenced, and the last sessions consolidate the weakest
  material regardless of what's due.
- **Two commands per session.** `begin` recovers, locks, validates,
  decides the session type and builds the queue; `close` applies grades,
  advances the plan, and commits. Everything deterministic lives in
  [`scripts/schedule.py`](scripts/schedule.py) — stdlib-only Python,
  copied into every course — so the agent spends its attention teaching
  and never does date math or picks a mastery level.
- **The agent never grades from vibes.** Grading is comparison against
  stored keys and rubrics. Mastery is *derived* from the review interval,
  never stored, so there is no band to inflate.
- **It runs itself.** Put the course on a recurring trigger and it
  nudges, heals, and resumes without supervision — see
  [`scheduling.md`](scheduling.md). A dropped notification costs one
  nudge, never state.
- **The resurrection test.** A fresh agent handed only the course
  directory must run the next session correctly with zero explanation.
  That one property is disaster recovery, platform portability, and
  exportability at once.

## Repository

| File | What it is |
|---|---|
| [`SKILL.md`](SKILL.md) | The session procedure — one page |
| [`bootstrap.md`](bootstrap.md) | Course creation: interview → design → assets |
| [`checkpoint.md`](checkpoint.md) | Checkpoints, adjudication, dormancy, graduation |
| [`scheduling.md`](scheduling.md) | Putting a course on a recurring trigger |
| [`scripts/schedule.py`](scripts/schedule.py) | The deterministic core (stdlib only) |
| [`templates/`](templates) | Every state file, self-documenting |
| [`tools/venice.py`](tools/venice.py) | Optional research helper: text + real YouTube ingestion |
| [`example-course/`](example-course) | A complete 12-session course, mid-flight |
| [`tests/test_schedule.py`](tests/test_schedule.py) | Written first; pins every interface |
| [`CRITIQUE.md`](CRITIQUE.md) · [`CRITIQUE-R2.md`](CRITIQUE-R2.md) · [`CRITIQUE-R3.md`](CRITIQUE-R3.md) | Three adversarial panels, in full |
| [`SPEC.md`](SPEC.md) | **Superseded** — the v2.1 design spec, kept for history |

```
python3 -m unittest discover -s tests          # 161 tests
python3 scripts/schedule.py --course example-course check
```

## Using it

**As a skill.** Run `./install.sh` (above), then ask your agent to
create a course — it reads `bootstrap.md`. When a session trigger
fires, it reads `SKILL.md`. Skill discovery is by description: a plain
"set me up a course on X" is enough for an agent that has never been
told this repo exists.

**By hand.** Copy `example-course/` as a starting shape, or run
bootstrap against any topic. Every course directory is self-sufficient:
it carries its own copy of the procedure and the engine, so it works on a
machine that has never heard of this repo.

The procedure files are split by **progressive disclosure**: a session
loads `SKILL.md` (~1k words) and nothing else, unless `begin` sends it to
`checkpoint.md`. Bootstrap and scheduling are separate because they run
once per course, not once per session.

## Design lineage

Drafted as a spec, critiqued by three panels of five independent LLM
reviewers, then piloted. All three critique reports are committed in
full — the repo is the design history.

**Round 2:** *every defect that survived prose review lived in an
interface that existed only as prose* — which is why the deterministic
layer was then built test-first.

**Round 3** found the same disease one level down, in code: `SKILL.md`
and `checkpoint.md` promised state transitions (`"Pass clears the flag"`,
`"re-entering rotation"`) that no line of `schedule.py` performed, so a
single failed teach-back locked the course in a permanent repair loop and
every plateaued concept became an un-adjudicable ghost. Generalised: **a
promise in a procedure file is a test you haven't written yet.** That
round also cut roughly a third of the system's conceptual surface — the
mastery-band apparatus computed a number no decision read and that
reached 0–2 concepts per course; deleting it took three latent defects
with it.

**The pilot** found what no reviewer could, because every reviewer was
also the tutor and therefore chose when to stop: real sessions have no
ending. Generalised: **simulation cannot test the transitions the
simulator controls.**

**The pilot's final session** found the subtler cousin of the round-3
class: two consecutive review sessions asked the learner the *same three
questions*, near-verbatim, and the learner noticed before the system
did. Not forgetting — convergence: two stateless tutors given the same
state and the same policy produce the same output, and the standing
instruction to "vary the wording" made it worse, because paraphrase
feels novel to the generator and identical to the recipient.
Generalised: **you cannot exhort a stateless agent into novelty — you
have to change the state it sees.** Hence the asked ledger: every
question a session poses lands in its log, `begin` replays the recent
ones, and asset-bank items burn on first use.

**The learner** then caught what the engine's own review had not: those
two adjacent sessions had also inflated the schedule. Consolidation
ignores due dates by design, but the transition table climbed the
ladder on *any* pass — so two probes one day apart promoted concepts to
the 35-day rung on evidence that never exceeded a six-day gap.
Generalised: **an interval is a claim about demonstrated retention, and
a pass may only climb it by the gap it actually survived.** Early
passes now keep the rung and restart the clock; early fails still step
down, because failing one day after the last retrieval is worse news,
not better.

**The author/tutor asymmetry** became explicit when the pilot expanded
to a full course: the agent that designs a course is usually running
with more context, more sources, and a stronger model than the agent
that teaches session 23 on a Tuesday. The course directory is therefore
a *compilation target* — the expensive model compiles once (map, plan,
every unit's assets, with perishable figures dated), and the cheap
model executes ~40 times, refreshing numbers but never redesigning.
Every piece of judgment pre-baked into the files is a piece the runtime
tutor cannot get wrong.
