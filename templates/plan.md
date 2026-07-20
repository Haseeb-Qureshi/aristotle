<!-- FORMAT — the living syllabus. Agent-writable (schedule.py reads it,
     and rewrites concept lists on reprune).
     Header fields:
       course-status   active | paused | maintenance | closed
       next-session    N/M  (integer counter / course size)
       cadence         sessions per week the user chose
       sessions-done   cumulative attended count (never resets, never breaks)
       last-attended   YYYY-MM-DD of the last completed session
       re-entry-pending yes | no   (set on resume; consumed by rung 2)
       next-assets     authored | pending  (gate for starting the next unit)
     Unit blocks are QUESTION-framed. Session ranges are NOT stored —
     derive them from `sessions:` counts so fractional repair sessions
     (17r) never force renumbering.
-->
course-status: active
next-session: 1/30
cadence: 3
sessions-done: 0
last-attended: -
re-entry-pending: no
next-assets: authored

## Unit 1: <the question this unit answers>
sessions: 3
concepts: [concept-a, concept-b, concept-c]
keystones: [concept-a]
artifact-milestone: <one concrete step, or "none">
sources: [unit-01-a]
status: untouched

<!-- status: untouched | in-progress | taught | verified
     keystones: the 1-2 concepts teach-back examines (not all of them)
     Reordering/splitting units is allowed; log the reason in the session
     log. Units are never re-entered — interleaved application revisits.
-->
