# elenchus — checkpoint, adjudication, lifecycle

Loaded only when SKILL.md dispatch says so: every 7th session
(`sessions-done % 7 == 0`), or when `course-status` ≠ `active`.

`S = python3 $C/scripts/schedule.py --course $C`

## Checkpoint (appended to a normal close)

Run `S report`. **That output is for you, not for them** — never paste it.
Read it and send at most:

1. **One sentence of progress**, anchored to the finish and the goal.
   "Session 14 of 30 — you've got the whole diagnostic axis solid, and
   that's the half that actually changes what you do at the machine."
2. **The hook** — one genuinely interesting question the course hasn't
   answered yet. This is the re-engagement payload; make it good.
3. **At most one ask** — an adjudication or the reprune offer, never both.

Also: mention `sessions-done` as a cumulative count if it's a nice number.
Never frame it as a streak, and never mention a broken one.

## Adjudication (plateaued concepts)

`report` lists concepts stuck at `plateaued` (3 consecutive fails). You
cannot verify these; say so plainly and hand them the call:

> "I can't get a clean read on channeling — three tries, three misses,
> and I don't think the problem is you. My guess is you've got the idea
> but not the vocabulary. Your call: count it and move on, keep it in
> rotation, or drop it?"

Record their verdict at the next close:

| Verdict | Action |
|---|---|
| count it | `- grade: <id> \| result: pass \| note: user-adjudicated` |
| keep trying | `- grade: <id> \| result: taught \| note: re-entering rotation` |
| drop it | `S set-verify <id> none` |

## Reprune (the course is too long for the life they have)

Offer when they are ≥2 weeks behind their `cadence`, **or** at re-entry
after a long gap, **or** whenever they ask. Never auto-apply — silently
shrinking someone's course is deciding they're a quitter.

Frame it as **locking in a win**, never as lowering the bar:

> "You've got 11 sessions left at 3/week, and life clearly isn't
> 3/week right now. I can cut this to a 5-session finish that still
> gets you to diagnosing a shot cold — we'd drop the refractometry
> detour and keep the diagnostic core. Want that, or keep the long
> version?"

If accepted:

```
S reprune --drop <comma,separated,ids>
```

The script refuses to drop a concept another kept concept depends on,
excludes dropped concepts from the queue, and keeps every surviving
interval. Then update `plan.md`: `next-session: <n>/<new total>`, and
remove emptied units. Never drop a `threshold: yes` concept.

## Pause / dormancy

Compute silence from `plan.md`: `last-attended` + `cadence`.

**~14 days of silence → pause.** Not three missed triggers — a busy week
is not a churn signal, and pausing an engaged user reads as being given
up on. Set `course-status: paused`, commit, and send **one** message that
offers a smaller door:

> "Course is on hold, nothing lost — your spot and everything you've
> learned are exactly where you left them. Want a 5-minute rust-knock
> when you're ready, or should I just hold it?"

While paused: at most one message per fortnight. Do not lead with a
content question — a quiz about a half-forgotten concept confirms the
avoidance. Lead with the door.

**On `resume`:** set `course-status: active`, `re-entry-pending: yes`,
commit. Dispatch rung 2 handles the session.

**On an explicit quit:** `course-status: closed`, write a graceful exit
report — what they actually learned, what's still fragile, what it would
take to pick up. Closing is a recorded outcome, not a failure.

## Graduation

When every unit is `taught`/`verified` and the counter is exhausted.

**The capstone is a mirror, not a measurement. Write no grade lines.**
Do not run "a final cumulative teach-back" as an exam. Instead:

1. The artifact, finished — or, with no artifact, ask them to explain the
   whole domain to a beginner in five minutes, recorded or written, as
   something they keep.
2. Show them the delta explicitly: a question from session 1 they
   couldn't answer, beside their answer now. This is the payoff.
3. Hand over the report as a trophy: what's durable, what's fragile,
   what they can now do that they couldn't.

*Then* offer maintenance, framed as keeping rather than still studying:

> "That's the course. Want me to keep it alive? One short review every
> couple of weeks and this stays yours instead of fading by Christmas."

If yes: `course-status: maintenance`. Run review-only sessions on the
queue — **weekly** until every concept has cleared the 35-day interval,
fortnightly after that. If no: `course-status: closed`.
