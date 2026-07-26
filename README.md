# elenchus

*ἔλεγχος — the Socratic method of eliciting truth by cross-examination.*

A chat-based AI tutor that teaches you one topic over a finite course of
short, scheduled sessions — designed for **long-term retention first**,
completion second, coverage third. The agent is stateless; the entire
course lives in one human-readable markdown directory you can read, edit,
git-push, and resurrect on any machine, any platform, any model.

**Status: complete and runnable, not yet piloted.** Three adversarial
review rounds — two against the spec, one against the built system, the
last of which executed the course rather than reading it. Next: run a
real course end to end with a real learner.

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
| [`scripts/schedule.py`](scripts/schedule.py) | The deterministic core (stdlib only) |
| [`templates/`](templates) | Every state file, self-documenting |
| [`example-course/`](example-course) | A complete 12-session course, mid-flight |
| [`tests/test_schedule.py`](tests/test_schedule.py) | Written first; pins every interface |
| [`CRITIQUE.md`](CRITIQUE.md) · [`CRITIQUE-R2.md`](CRITIQUE-R2.md) · [`CRITIQUE-R3.md`](CRITIQUE-R3.md) | Three adversarial panels, in full |
| [`SPEC.md`](SPEC.md) | **Superseded** — the v2.1 design spec, kept for history |

```
python3 -m unittest discover -s tests          # 140 tests
python3 scripts/schedule.py --course example-course check
```

The procedure files are split by **progressive disclosure**: a session
loads `SKILL.md` (~1k words) and nothing else, unless `begin` sends it to
`checkpoint.md`. Bootstrap is separate because it is the only part that
needs research tools.

## Design lineage

The spec was drafted, then critiqued by three panels of five independent
LLM reviewers. All three reports are committed in full — the repo is the
design history.

Round 2's lesson: *every defect that survived prose review lived in an
interface that existed only as prose* — which is why the deterministic
layer was then built test-first.

Round 3 found the same disease one level down, in code: `SKILL.md` and
`checkpoint.md` promised state transitions (`"Pass clears the flag"`,
`"re-entering rotation"`) that no line of `schedule.py` performed, so a
single failed teach-back locked the course in a permanent repair loop and
every plateaued concept became an un-adjudicable ghost. Generalised: **a
promise in a procedure file is a test you haven't written yet.**

Round 3 also cut roughly a third of the system's conceptual surface. The
mastery-band apparatus — four bands, per-concept ceilings, a delayed
re-probe, a promotion slot — turned out to compute a number that no
decision read and that reached 0–2 concepts per course. Deleting it took
three latent defects with it. `CRITIQUE-R3.md` has the full ledger.
