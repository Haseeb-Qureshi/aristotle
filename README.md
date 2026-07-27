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
python3 -m unittest discover -s tests          # 140 tests
python3 scripts/schedule.py --course example-course check
```

## Using it

**As a skill.** Install the four procedure files plus `scripts/` and
`templates/` wherever your agent loads skills. Ask it to create a course;
it reads `bootstrap.md`. A session trigger fires; it reads `SKILL.md`.

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
