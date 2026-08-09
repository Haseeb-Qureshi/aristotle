# Aristotle — scheduling a course

How to put a course on a recurring trigger so it runs itself. Read this
once, at the end of bootstrap. Everything here is platform-agnostic; the
worked example at the bottom is one concrete wiring.

**"Scheduling" here means a recurring trigger that wakes *you*, the
agent — a cron entry, a scheduled job, a task runner.** It does not mean
putting an appointment in the user's calendar. A calendar event reminds
a human to do something; what this course needs is a job that fires,
heals the course state, and sends a message even when nobody is
thinking about sourdough. (A clean-room agent reached for a calendar
tool here and created nothing that would ever run.) If your platform
has no scheduler, say so plainly and hand the user the one command that
starts a session, rather than inventing a reminder that cannot heal
state.

A scheduled Aristotle deployment has exactly **two moving parts**:

| | Runs | Job |
|---|---|---|
| **The nudge** | on the schedule, unattended | heal state, send ONE short message, stop |
| **The session** | when the user replies | teach one session, close it |

Keep them separate. A nudge that tries to teach will teach to nobody —
the user is not there yet — and a session that tries to schedule itself
will drift. **The nudge never teaches. The session never waits.**

## Choosing a cadence

Ask the user for days and a time, and record it as `cadence:` in
`plan.md` (sessions per week). The lifecycle math reads it from there,
never from the scheduler's config — so the course stays portable.

- **Recommend ≥3/week.** Below that the short review intervals (1, 3, 7
  days) stretch past their spacing and early consolidation measurably
  weakens. 5/week is comfortable for 10–20 minute sessions.
- **Daily** is fine and works well for short courses; the queue simply
  has fewer items due each day.
- **Weekly** is a different product: expect to spend the first third of
  every session on re-anchoring, and prefer a shorter course (10–20
  sessions) so the whole thing doesn't outlive the user's interest.
- Pick a **time when the user is reachable but not busy** — the nudge
  competes with everything else on their phone. Early evening beats
  mid-morning for most people.

Never make the schedule authoritative over the course. If a trigger
fires and the user ignores it, nothing changes: no counter moves, no
grades are written, nobody is "behind." The counter advances on
*sessions taught*, not days elapsed.

## The nudge job

Runs unattended on the cadence. Its whole job, in order:

1. **Heal, and heal before you look.** Any run may follow a session that
   crashed or was abandoned. Run `schedule.py recover` — it replays a
   finished-but-uncommitted close, or discards mid-flight debris, and
   commits either way. If it prints `locked`, a session is live right
   now: **send nothing and stop.**
2. **Reconcile a missed close** *before* step 1 if your platform can
   search its own conversation history. This is the most valuable
   safety net in a scheduled deployment — see below.
3. **Read exactly two things**: `plan.md` (for `course-status` and
   `next-session`) and the newest file in `log/` (for its
   `## open question`). Nothing else. A nudge job that starts exploring
   the filesystem will burn a minute and a lot of tokens rediscovering
   things this file already told it.
4. **If `course-status` is not `active`**, follow `checkpoint.md`'s
   dormancy rules instead — at most one gentle message per fortnight,
   and check your own message history so you don't double-send.
5. **Otherwise send ONE message, 1–2 sentences**: the session number and
   the open question as a hook. That open question is the whole reason
   the previous session wrote one.

> "Session 7 whenever you have 15 minutes — we left off on why the
> cheapest chip in the rack is the one nobody can buy. Reply to start."

Never put script output, file paths, concept ids, or grades in a nudge.

## Reconciling a missed close

**The single most common failure in a scheduled deployment**: the
session teaches a real lesson and never closes, because the user drifted
off and the tutor kept waiting for a goodbye. The lesson is real; the
record is empty.

Symptom, checkable without any history: `.session-inprogress` exists, is
**older than two hours**, and `log/` contains **no file whose name ends
in that sentinel's token**.

If your platform can search past conversations, reconstruct rather than
discard. **Sessions are bookended for exactly this** (`SKILL.md` §2):
every session opens `Session N —` and its goodnight opens `Next time:`.
So the search is deterministic, not a guess about topic words:

1. Search history for the last `Session N —`, **case-insensitively** —
   tutors do not capitalize a course label consistently ("AI economics"
   one session, "AI Economics" the next), and a case-sensitive search
   silently misses the very session it exists to find. If no
   `Next time:` follows the marker, that session was abandoned, and the
   messages between the marker and the end of the thread are what was
   actually covered.
2. If a real lesson happened, write `log/<date>-<token>.md` from what was
   actually taught and how the learner answered.
3. **Grade `taught` only — never `pass`, `fail`, or `rubric-*`.** You
   did not witness the retrieval, so you may not award evidence. Note
   "reconstructed" in each grade line.
4. Run `schedule.py close` on it.

Then continue to `recover` as normal. If no lesson is found, do nothing
— `recover` cleans up safely.

**Chat history is short-lived.** Assistants compact or truncate long
conversations, and a compacted transcript is *gone* — in the pilot,
five of six sessions' raw messages had been destroyed within two weeks.
Reconciliation therefore only works for the *most recent* session, in
the window before the next compaction; it is a next-day safety net, not
an archive. Anything the course needs durably — grades, open questions,
the asked ledger — must be in the course directory, never left to the
conversation.

The deeper fix belongs in the session, not the nudge: `SKILL.md` §4 puts
the close trigger in the tutor's hands precisely so this stays rare.

## Orientation: leave a breadcrumb

If the interactive session runs in a general-purpose assistant that does
many other things, it will not remember your course exists. Have the
nudge job overwrite a **single pointer file in the assistant's own
working directory** on every run:

```
# <course name> — next-session pointer
session: 7/30
open-question: <one line from the newest log>
course: /abs/path/to/course
to-start: read SKILL.md in the course dir, then run:
  python3 scripts/schedule.py --course /abs/path/to/course begin
NOTE: begin is the source of truth — this file is orientation only.
```

Then tell the assistant, in whatever its standing instructions are:
*orient from this one file; do not search.* Without it, a session that
starts "let's do the lesson" spends a dozen tool calls rediscovering the
course before saying a word. With it, three.

## Multiple courses, one chat

Several scheduled courses delivering into the same conversation is
normal and safe *as state* — each course directory is independent, and
`begin`/`close` are atomic and idempotent per course. Nothing one course
does can corrupt another.

What does collide is everything that lives in the **shared chat**:

- **Label every marker.** The session bookends (`SKILL.md` §2) carry the
  course label — `AI economics · Session 7 —` — precisely so that
  reconciliation can tell two courses' sessions apart in one transcript.
  An unlabelled `Session 7 —` is ambiguous the moment a second course
  exists, and reconstruction will attribute the wrong lesson to the
  wrong course. `begin` prints the label; use it verbatim.
- **Name the course in the nudge**, for the same reason plus the obvious
  one: "Session 7" means nothing to a user running three courses.
- **One pointer file per course** (`<course>-next.md`), never a shared
  one.
- **Stagger the trigger times.** Two nudges arriving together train the
  user to ignore both.
- **Accept that a live session can be interrupted.** If course B's nudge
  lands while course A is mid-session and the user switches, A's
  sentinel goes stale and A's lesson is reconstructed or discarded on
  its next run — the normal abandonment path, no corruption. Staggering
  makes this rare; nothing needs to prevent it.

## Failure modes this survives

| What happens | Result |
|---|---|
| Nudge is dropped / never delivered | One missed nudge. No state change. Next trigger proceeds normally. |
| Trigger fires twice | Second run sees a fresh sentinel, prints `locked`, stays silent. |
| Session crashes mid-teach | Next `recover` discards debris; nothing partial is committed. |
| Session teaches but never closes | Reconciliation rebuilds the log (`taught` only); otherwise safely discarded. |
| User ignores the course for a month | `dormant` dispatch → one gentle message per fortnight, never a guilt trip. |
| Whole machine dies | Course is a git repo. Clone it anywhere and run `begin`. |

State moves **only** through `begin` and `close`. Both are atomic; every
close commits. That is what makes a flaky scheduler harmless.

## Worked example: cron + a chat assistant

One concrete wiring, for a chat-based assistant with a cron facility
that can deliver to a messaging platform.

**Cron job** (`0 18 * * 1,3,5` — Mon/Wed/Fri 18:00, delivering to chat):

```
You are the <course> lesson scheduler. Do NOT teach. Everything you need
is in this prompt — do not explore. Course dir: $C (it exists).

1. mkdir -p $C/log
2. If $C/.session-inprogress exists and is younger than 2 hours: respond
   [silent] and stop.
   If it is older than 2 hours and no $C/log file matches its token:
   search conversation history for the last "Session N —" with no
   "Next time:" after it; if one is found, write
   $C/log/<date>-<token>.md (format: $C/templates/log.md, `taught`
   grades only, note "reconstructed"), then run
   python3 $C/scripts/schedule.py --course $C close $C/log/<file>
3. python3 $C/scripts/schedule.py --course $C recover
   (if it prints "locked": respond [silent] and stop)
4. Read $C/plan.md and, if log/ is non-empty, the newest log's
   "## open question". Nothing else.
5. Overwrite <assistant working dir>/<course>-next.md with the pointer
   block from "Orientation" above.
6. If course-status is not active: follow $C/checkpoint.md dormancy.
7. Otherwise your reply IS the nudge: 1-2 sentences, session number +
   open question as a hook. No paths, no ids, no script output.
```

**Assistant standing instructions** (its always-loaded config):

```
## <Course> tutoring

When the user replies to a lesson nudge, or asks for the lesson:
0. Orient from <course>-next.md. Do not search.
1. Read SKILL.md in the course dir — it is the full procedure and
   overrides anything here. Then run `schedule.py ... begin`.
2. Teach per SKILL.md. ONE new concept. Short messages.
3. Close per SKILL.md §4 — after ~6-10 exchanges, without waiting for
   the user to say goodbye. Silent. Keep chatting afterwards if they do.
```

That is the entire integration: one cron prompt, one paragraph of
standing instructions, and a pointer file. Everything else — what to
teach, what is due, what counts as evidence — is already in the course
directory.
