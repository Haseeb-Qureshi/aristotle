# Critique round 3 — the built system

Rounds 1 and 2 reviewed a **spec**. This round reviewed the **running
system**, with an inverted mandate: *harden and simplify for optimal
pedagogy, but not overly prescriptive — trust the agent delivering the
curriculum.* Reviewers were told to prefer deletion, to justify every
rule as a bet that a competent model would otherwise get it wrong, and to
pay for any addition by naming what it replaced.

Five independent reviewers: fresh-eyes designer, learning science,
hostile cold-start executor, engine audit, adherence/product. Three of
them executed rather than read — running the course, simulating 30
sessions against the real transition table, and mutation-testing the
suite.

---

## The headline

**The disease of rounds 1 and 2 had reproduced itself in code.** Round 2's
lesson was "every defect that survived prose review lived in an interface
that existed only as prose." Round 3 found the same shape one level down:
`SKILL.md` and `checkpoint.md` *promised* state transitions that no line
of `schedule.py` performed.

- `SKILL.md`: *"Pass clears the flag; fail clears it too."* Nothing
  cleared `repair-pending`. Every session after one failed teach-back was
  a repair session, forever.
- `checkpoint.md`: *"re-entering rotation."* `plateaued` had no exit, so
  all three adjudication verdicts were no-ops and every future checkpoint
  re-asked the same question.
- `SKILL.md`: *"`S check` will reject placeholder work."* An asset file
  whose every field was the literal string `TODO` passed.

Three reviewers found the first two independently. The lesson generalises
past "write the code": **a promise in the procedure file is a test you
have not written yet.**

## The other headline

**The most elaborate machinery in the system computed nothing.** `mastery`
was written by two functions and read at exactly one site — the band
histogram in `cmd_report`, which `checkpoint.md` orders the agent never
to show anyone. Nothing scheduled on it. And it was nearly unreachable:
`solid` required a teach-back `rubric-pass`, *then* a delayed re-probe,
*then* surviving a 35-day interval. A 30-session simulation put that at
0–2 concepts per course; the bundled 9-session example could reach it for
none.

So the whole axis — `mastery`, `ceiling`, `_band_cap`, `reprobe`,
`solid-pending`, the "solid is not agent-writable" rule — was deleted.
`report` now derives a display band from `interval` and `fails`. This
removed three defects for free, including a single-slot `solid-pending`
that silently dropped one promotion when a unit had two keystones.

---

## Findings and dispositions

### Course-killers — fixed

| Finding | Disposition |
|---|---|
| `repair-pending` set, never cleared → infinite repair loop | `_apply_grade` clears it on any grade for that concept; a fail also plateaus, as the prose promised. Tests pin both. |
| `plateaued` terminal → all adjudication verdicts dead | `taught` and `pass` un-plateau; `taught` zeroes `fails`; `set-verify none` drops the concept so `report` stops nagging. |
| `pass` on an untaught row → climbs intervals while invisible | Any pass or fail activates the row. A pass is evidence of contact whatever the row claimed. |
| `recover` crashed off-repo (the README's own first command) | `begin`/`recover` initialise the repo and write a `.gitignore`. |
| `recover` ran `git reset --hard` on the **parent** repo — deleted an entire course in testing, and reverted an unrelated file two directories up | Replaced with `git checkout -- .` + `git clean -fd -- .`, scoped to the course subtree. All commits are pathspec-scoped too. |
| Sentinel age used a system clock against a course-timezone timestamp → a 5-minute-old **live** session read as stale and was reset | Age now comes from the sentinel's own mtime. No clock, timezone or agent-authored string can enter the decision. `started:` is gone. |
| A tz-aware ISO timestamp raised an uncaught `TypeError`; a `Z` suffix failed differently on 3.10 vs 3.11 | Same deletion. |
| Unvalidated sentinel token: `7/9` (the literal reading of the instruction) globbed nothing, so a **finished** session was classified as a crash and its log deleted | Token validated; an unreadable sentinel returns `locked` — refuse to destroy when you know least. |
| `IntegrityError` escaped the replay path and wedged the course forever | Caught alongside `FormatError`. |
| `validate_assets` made the bundled example **unauthorable** at unit 3 — a keystone with no map misconceptions had no legal asset file | `avoid:` is required only where the map declares misconceptions. The example's keystone got real misconceptions too. |
| ...while accepting a file of empty strings and `TODO`s | Validation is now on *content*: non-empty, non-placeholder, and interleaved problems must name real concept ids. |
| `check` validated no field **values** — corrupt state passed green and crashed later | Every value validated on load; plan header and unit statuses too. `STATUSES`, previously dead, now has a job. |
| The 14-day pause rule was **structurally unreachable** — it lived in a file dispatch only loaded when already paused | `dormant` is a dispatch type computed from `last-attended`. |
| Course arithmetic overran the counter: ~22 concepts + 2 non-teaching sessions per unit > 30 | `unit-review` folded into teach-back; `check` enforces `sessions >= concepts + 1` per unit and reserves ≥2 consolidation sessions. |
| Counter exhausting matched **no** dispatch rung — `31/30`, `32/30`, standard sessions forever, graduation never firing | `graduation` fires on an exhausted counter whatever is left untaught, and names the gaps. |
| A course directory lacked `checkpoint.md` and `templates/` — the resurrection claim was false | Bootstrap copies both; the example course carries them. |
| Duplicate grade lines applied twice, silently erasing a `fail` — breaking the documented "the fail stands" | One verdict per concept per log; a second is a hard error. |
| `## Sources` / `## Controversies` rewrote the last concept's fields | Concept bodies truncate at the next `## `. |
| Grade lines were parsed anywhere, so an example quoted in prose mutated mastery | Only the `## grades` section is scanned. |
| Near-miss grade lines (en-dash bullet, `- **grade:**`) vanished silently | They now fail loudly. |
| Errata silently no-opped on 3 of 5 plausible spellings | Regex tolerates bullets, indentation and case. |
| No `encoding=`; a `LC_ALL=C` container broke every read | UTF-8 everywhere, with a test. |
| Any non-`FormatError` reached the agent as a raw traceback | `main` catches `Exception`, prints `ERROR:`, exits 2. |
| Close committed the sentinel, then deleted it — a junk `recover: commit-as-is` commit every session | `.gitignore` ships with every course; `close` owns the ordering. |
| Placement evidence was discarded — `seed retrievable` still scheduled review for tomorrow | Seed maps evidence to a real interval. |
| Oldest-first queue starved the material the current unit is about | Sorted by interval then date, so fresh material isn't crowded out by a long-interval backlog. |
| `rubric-fail` changed nothing — the hardest assessment in the system had no scheduling consequence | It now behaves as a fail, then considers the repair. |

### Simplifications — taken

Measured against the reviewers' count of "distinct concepts a reader must
hold." Deleted outright: the mastery/`ceiling`/`reprobe`/`solid-pending`
axis; the `next-assets` flag (replaced by a file-existence test nobody can
forget to flip); the `unit-review` session type; the `verified` unit
status; `history.md` log distillation and its counter; `example: faded`
and `self-explain:` assets (parsed, validated by nothing, referenced by
no procedure); `## Controversies`; the four `Never` bullets that restated
rules given earlier; the standard-middle choreography ("Socratic
questioning, then connect it explicitly to **two** concepts…"); the
Tangents section; the five-line justification attached to the
corrective-feedback rule; three of checkpoint.md's four verbatim scripts.

`threshold:` was parsed and never read while `checkpoint.md` promised
"never drop a threshold concept" — rather than delete it, `reprune` now
enforces the promise.

**Prep and close collapsed into two verbs.** The cold-start executor
measured bookkeeping at ~23 of ~30 operations against ~6 turns of
teaching, and named the close's `plan.md` edits as the thing it would
skip under time pressure. `S begin` now does recover + lock + check +
dispatch + queue; `S close` does grades + `plan.md` + queue + git +
unlock. This also deleted the largest *guess* surface in the system —
two reviewers derived different session types for the same session, and
nothing detected the divergence — plus the date-drift guess and the whole
`plan.md` false-accept class.

### Additions — each paid for

- **Consolidation sessions.** The simulation showed concepts taught after
  ~session 21 received two retrievals against four or five for unit 1,
  and then the course simply stopped. The last sessions now run mixed
  retrieval over the weakest material, ignoring due dates. Paid for by
  the deleted band machinery.
- **Item variation.** `check` requires only one quiz item per concept,
  which then gets asked at three to five spaced reviews — item-specific
  learning, quietly reintroducing the failure the interleaved set exists
  to prevent. One clause: vary the wording, grade against the stored
  answer. Paid for by the deleted `self-explain:` asset.
- **An ending.** The close was six file operations with no user-facing
  step, so every session terminated in silence and the `## open question`
  hook was written to a file instead of spoken. Now step 1 of the close.
- **A session-1 baseline.** Graduation's best moment — "here's what you
  couldn't answer in session 1" — depended on evidence log distillation
  destroyed. `history.md` now carries a verbatim baseline that is never
  rotated.
- **A turn budget**, and explicit permission to end early.

### Leakage — closed

`SKILL.md` used to instruct the agent to name the misconception the
learner hit *by id* ("M1", "M2"). Concept ids, band names, session tokens
like `17r`, rubric text and raw script output were all reachable in
user-facing speech; only `report` carried a "never paste this" guard.
That guard is now a general rule.

---

## What round 3 did not settle

- **Nothing here has taught a human.** Every claim above is verified
  against tests, execution, or simulation — not against a learner. The
  turn budget (~12 minutes, ~10 turns) is an estimate, not a measurement.
- **Assets authored under context pressure at unit 5+** remain untested;
  the validator can enforce non-emptiness, not quality.
- The engine auditor's mutation run scored the *old* suite at 55%. The
  new suite adds the missing classes (atomicity, CLI contract, sequences,
  recovery matrix, asset behaviour) but has not itself been mutation-
  tested.
