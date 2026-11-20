# Lesson-first: teach the lesson, then ask

2026-11-20. The learner's complaint after 39 sessions of the AI-economics course: "too much quizzing and not enough teaching … I'm just getting questions and sometimes getting them wrong or right but not enough communication of mental models or specific information." He contrasted it with the earlier fintech course (30 lessons, hand-rolled, no engine), which he called solid: lessons cohered around one concept, and questions felt fair because the lesson had already taught what they asked for.

## Evidence

Both courses ran in the same Telegram chat, so the transcripts are directly comparable (Hermes `state.db`).

| | Fintech (lessons 13-14, May) | AI economics (all sessions) |
|---|---|---|
| Tutor words per lesson | ~2,500-3,500 | ~400-1,200 (teaching sessions), ~100-600 (catch-ups) |
| Median tutor message | ~150 words | 30-80 words; 29 in November |
| Source the tutor taught from | a ~1,150-word lesson file per session | one "worked example" paragraph per concept, in a file that is otherwise a quiz bank |
| What a tutor turn did | confirmed the answer, added 2-4 paragraphs of new material, ended on a question that led into the next piece | one-line verdict, then the next question |
| Questions on other topics | none; earlier lessons came back only where today's lesson stood on them | 1-2 cold retrievals of unrelated concepts at the open and as an exit ticket, every session |

Two examples. `training-amortization`, a unit keystone, was "taught" in session 30 in one 70-word paragraph between three quiz questions. And from 2026-10-21 to 2026-11-19 (twelve sittings) the course delivered one new concept; the rest were "catch-up" teach-backs of concepts first taught in August and September, each a string of invented underwriting cases ("what would you need to see before…"). He called two of those questions out as unfair or pointless, correctly.

## Why the method produced this

1. **The session was specified as evidence collection.** Retrieval at the open, an exit ticket, an interleaved problem, "close as soon as he has answered one application question", twelve minutes, about ten turns. Teaching was left one or two turns.
2. **There was no lesson to teach.** A concept's teachable content was a single dense paragraph. Three to six quiz items per concept against one example: the asset format itself ranked quizzing first.
3. **Feedback was a verdict.** "One message holding the verdict, the correction, and the next question" became verdict plus next question.
4. **Whole sessions carried no information.** Unit-end teach-backs, review blocks, catch-ups for ungraded teach-backs and repairs were all question-only. An ungraded teach-back generated a catch-up session, and a catch-up interrupted mid-way restarted from a new cold question the next day.
5. **Novelty rules manufactured contrived cases.** Single-use items and "never re-ask" pushed the tutor to invent a fresh case for every probe; the cases drifted into generic cleverness (date windows, arithmetic) dressed in the subject's vocabulary.

## The change

The principle order in the README was "retention first, completion second, coverage third". It becomes: **understanding first** (the lesson is taught, completely), **retention second** (what was taught comes back, where it fits), completion third.

1. **A session is a lesson, taught from a lesson file.** `lessons/<concept>.md`: 900-1,400 words in 5-8 sections, each with the model, the mechanism, dated numbers and a named case, plus a question that opens the next section. The tutor walks it one section per turn. `begin` names the file on a `lesson:` line; `check` warns when an untaught concept has none.
2. **A turn has three parts**: answer what they said with substance; teach the next section (120-250 words); end on one question they can answer from what has been taught plus reasoning.
3. **Questions must be fair.** Nothing is asked that the lesson has not already made answerable. A question the learner calls unclear is dropped and the point taught directly.
4. **One subject per session.** No cold open, no exit ticket. Up to two earlier concepts come back as callbacks, only where today's lesson stands on them (`bring back:`; prerequisites of today's concept are listed first). A callback's answer always gets a real re-teach, which is also where owed material is repaid.
5. **Length follows the lesson**, about 8-12 tutor turns and 20-30 minutes. A lesson interrupted mid-way resumes at the next section (`## progress` in the log, `resume-lesson:` in the next brief) instead of restarting.
6. **No session is question-only.** The unit's last session is a **case study**: a real company or deal taught as a lesson, with the unit's concepts doing the work, ending on the learner's own read, which is graded quietly against the keystone rubric. Review blocks are integrated case studies. An ungraded case study is not owed: catch-up sessions exist only for concepts never taught.
7. **The close is a recap.** Their takeaway, then four to six lines of the models to keep, then the teaser.

What stays: all state in the course directory, `begin`/`close` as the only state verbs, evidence-only grading, the spacing ladder, the asked ledger and the presented record, recovery, pictures.

## Flow-through effects

| Change | Touches | Effect and handling |
|---|---|---|
| `lessons/` and the `lesson:` line | brief, `check`, bootstrap authoring, course-email full export | Printed only when the file exists, so courses without lessons run as before (the SKILL tells the tutor to outline a lesson of the same size from the worked example and sources). New courses cost more to author. The weekly status email is unaffected (it parses plan header fields only); the full export picks the files up as ordinary markdown. |
| `## progress` and resume | log template, draft creation, `begin`'s stale-draft cleanup, `recover`, `close`, `pointer`, the cron's missed-close reconciliation | A draft holding only progress must survive cleanup and recovery (both treated it as empty). `close` stamps the log `<!-- closed -->` so a finished lesson is never "resumed". Progress with no grade still counts as attendance, or a learner mid-lesson could be declared dormant. The cron must stop reconstructing-and-closing a half-delivered lesson: it leaves it for resume. The nudge names the lesson in progress. |
| Callbacks replace open/exit quizzes | review shapes, queue order, brief text, `close`'s off-brief warning, tests | Fewer graded retrievals per session and a bias toward connected concepts: unconnected due concepts roll forward until a case study exercises them. Measured retention evidence gets thinner; that is the trade the learner asked for. Old log comments (`review=open:2`) still parse. The heavy-backlog escalation (more quizzing when many concepts are due) is removed. |
| Ungraded unit-end sessions are not owed | `owed_items`, dispatch, graduation summary, bookend label, tests | Catch-ups shrink to never-taught concepts. Live course: the two pending catch-ups (teach-backs of `allocation-not-purchase` and `training-amortization`) disappear and session 34 teaches `benchmark-failure-modes`. Those two keystones never get a rubric grade; they stay in ordinary rotation. The last log's open question was hand-edited toward the dropped catch-up and is reverted. |
| `teach-back` becomes `case-study` | printed type, SKILL, cron prompt, tests | The log key `back=` and the rubric-only rule are unchanged, so old logs and the close guard keep working. A rubric-fail still schedules a repair, which is a re-teach. |
| SKILL rewrite | every skill root (via `install.sh`), each course's own copy, Bombot's `AGENTS.md` invariants, the `ai-econ-lesson` wrapper, the cron prompt | Three places restate the old budget ("6-10 exchanges", "short messages", "~12-15 minutes", "close as soon as he has answered one application question") and would override the new SKILL if left. All are changed together. Engine and SKILL in a course directory must move together; the sourdough course keeps its old pair until deliberately synced. |
| Longer sessions | the 2-hour live-lock, Telegram's 4,096-character limit | A 250-word message is ~1,700 characters. A pause over two hours lets the cron clear the lock; the next reply resumes from progress. |
| Lesson content for the live course | `lessons/` (new), nothing else | Asset banks, ids and the single-use ledger are untouched. Units 1-5 were taught thin and get no retroactive lessons; their material returns through callbacks, owed items and case studies. |

## What the test showed

Three lessons from different units were each run end to end three ways, with a simulated learner built from the real learner's replies (median 20 words, blunt, quick to call out an unfair question). "Key facts" is a fixed list of 16-23 figures and names per lesson, counted in the tutor's messages.

| | Tutor words | Key facts delivered | Typical message |
|---|---|---|---|
| As originally taught (real transcripts) | 377-687 | 2-3 of ~20 | 44-111 words |
| Lesson file + the old ten-line "teach it conversationally" note, GPT-6.2 Sol | 587-877 | 2-4 of ~20 | ~100 words |
| Lesson file + this SKILL.md, GPT-6.2 Sol | 1,862-2,045 | 16/16, 22/23, 19/19 | ~250 words |
| Lesson file + the ten-line note, Claude Opus | 1,687-2,555 | 16/16, 21/23, 19/19 | 230-310 words |

Two things follow. The written lesson file is necessary under every arrangement. And how much procedure a tutor needs depends on the model: one expanded a full lesson from ten lines of instruction, the other compressed the same file into short Socratic turns built on toy arithmetic until the turn anatomy in SKILL.md §2 told it not to. The procedure is written for the model that needs it.

The first runs also showed a status line before every tool call, figures looked up mid-lesson, three to five source links per message and research added beyond the lesson; SKILL.md was tightened for each and the runs repeated.

## Rollback

Every repo is tagged `pre-lesson-first`. Engine changes land as separate commits (lesson line; progress and resume; callbacks; owed/case-study), then the procedure, then the course's adoption in one commit, so the course can return to the old method by reverting that one commit while keeping its lesson files. The live deployment's cron prompt lives outside git; its text before and after the change is kept in the course's own repository.
