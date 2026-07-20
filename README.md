# elenchus

*ἔλεγχος — the Socratic method of eliciting truth by cross-examination.*

A chat-based AI tutor that teaches you one topic over a finite course of
short, scheduled sessions — designed for **long-term retention first**,
completion second, coverage third. The agent is stateless; the entire
course lives in one human-readable markdown directory you can read, edit,
git-push, and resurrect on any machine, any platform, any model.

**Status: complete and runnable, not yet piloted.** The spec survived two
adversarial five-reviewer critique panels; the scheduling engine, the
skill procedures, the file templates, and a bundled example course are
all implemented and verified. Next: run a real course end to end.

## How it works

- **Map, plan, session.** A one-time bootstrap interviews you (~5 taps),
  researches the domain if needed, and writes a frozen concept graph
  (`domain-map.md`), a mutable syllabus (`plan.md`), and pre-authored
  teaching assets — quiz keys, teach-back rubrics, worked examples,
  misconception distractors. Sessions are generated from those files.
- **Forward motion is unconditional; verification is advisory.** The
  course advances on a session counter ("17/30"), never blocked by
  mastery. Weak concepts persist in a capped spaced-review queue
  (1/3/7/16/35/90/180-day intervals) until evidenced.
- **The agent never grades from vibes and never does date math.**
  Grading is comparison against stored keys and rubrics. Scheduling,
  mastery transitions, integrity checks, and crash recovery live in
  [`scripts/schedule.py`](scripts/schedule.py) — stdlib-only Python,
  copied into every course directory.
- **The resurrection test.** A fresh agent handed only the course
  directory must run the next session correctly with zero explanation.
  That one property is disaster recovery, platform portability, and
  exportability at once.

## Repository

| File | What it is |
|---|---|
| [`SKILL.md`](SKILL.md) | The session procedure — dispatch, flow, close |
| [`bootstrap.md`](bootstrap.md) | Course creation: interview → design → assets |
| [`checkpoint.md`](checkpoint.md) | Checkpoints, adjudication, pause, graduation |
| [`scripts/schedule.py`](scripts/schedule.py) | The deterministic core (stdlib only) |
| [`templates/`](templates) | Every state file, self-documenting |
| [`example-course/`](example-course) | A complete 9-session course, mid-flight |
| [`tests/test_schedule.py`](tests/test_schedule.py) | Written first; pins every interface |
| [`SPEC.md`](SPEC.md) | The design spec (v2.1) |
| [`CRITIQUE.md`](CRITIQUE.md) · [`CRITIQUE-R2.md`](CRITIQUE-R2.md) | Two adversarial panel rounds, in full |

```
python3 -m unittest discover -s tests -v          # 55 tests
python3 scripts/schedule.py --course example-course check
```

The three procedure files are split by **progressive disclosure**: a
session loads `SKILL.md` (~1k words) and nothing else, until dispatch
sends it to `checkpoint.md`. Bootstrap is a separate skill because it is
the only part that needs research tools.

## Design lineage

The spec was drafted, then critiqued twice by panels of five independent
LLM reviewers (fresh-eyes + learning-science + hostile-executor +
adherence/churn + state-audit lenses). Both critique reports are
committed in full — the repo is the design history. The recurring lesson,
recorded in round 2's disposition: every defect that survived prose
review lived in an interface that existed only as prose, which is why the
deterministic layer was built test-first before any further spec editing.

Implementation notes where the code supersedes SPEC v2.1 (v2.2 will
absorb these):

- All script-owned course flags (`committed-sessions`, `solid-pending`,
  `repair-pending`) live in a header block *inside* `knowledge-state.md`,
  not `plan.md` — one `os.replace` write covers grades and flags
  atomically.
- The grade-line grammar:
  `- grade: <id> | result: taught|pass|fail|rubric-pass|rubric-fail | note: ...`
  — `solid` is not writable; the script derives it from a delayed
  re-probe plus survival of the 35-day interval.
- Session tokens: digits with optional `r`-suffix (`17`, `17r`, `17r2`);
  the idempotency guard keys on the exact string.
