<!-- FORMAT — the living syllabus.
     The header block is written by `S close`; don't hand-edit it during
     a session. Unit blocks are authored at bootstrap.
     Header fields (all required, values validated by `check`):
       course-status     active | paused | maintenance | closed
       next-session      N/M  (counter / course size)
       cadence           sessions per week the user chose
       sessions-done     cumulative attended count; never resets
       last-attended     YYYY-MM-DD, or '-' before the first session
       re-entry-pending  yes | no
     Session ranges are NOT stored — they are derived from the `sessions:`
     counts, so fractional repair sessions (17r) never force renumbering.
-->
course-status: active
next-session: 1/30
cadence: 3
sessions-done: 0
last-attended: -
re-entry-pending: no

## Unit 1: <the question this unit answers>
sessions: 3
concepts: [concept-a, concept-b]
keystones: [concept-a]
artifact-milestone: <one concrete step, or "none">
sources: [unit-01-a]
status: untouched

<!-- status     untouched | in-progress | taught   (set by `S close`)
     keystones  the 1-2 concepts teach-back examines; each must be one of
                this unit's own concepts, and each needs a misconception
                in the map
     ARITHMETIC, enforced by `check`:
       sessions >= len(concepts) + 1     one per concept, plus teach-back
       sum(sessions) <= course size - 2  leave room to consolidate
     Reordering or splitting units is allowed; log the reason. Units are
     never re-entered — interleaved application revisits them.
-->
