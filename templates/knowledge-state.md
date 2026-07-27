<!-- aristotle:state
committed-sessions:
repair-pending: none
-->
<!-- FORMAT — written ONLY by scripts/schedule.py. Never hand-edit; the
     agent's write surface is grade lines in a session log.
     One concept per PHYSICAL line, led by "- ". Fields are label-parsed
     (order does not matter), " | " separated, note last and may not
     contain "|". Every value is validated on load — a typo here is a
     loud error, not silent corruption.
       verify    quiz | use | none
       status    untaught | active | plateaued | dropped
       interval  days to the next review; the ladder is 1/3/7/16/35/90/180
       fails     consecutive misses; 3 marks the concept plateaued
     Dates are YYYY-MM-DD in the course timezone; "-" means unset.

     There is no mastery field. `S report` derives a display band from
     interval and fails, so there is no number to inflate and nothing to
     keep in sync.
-->
- id: CONCEPT-ID | verify: quiz | status: untaught | last: - | next: - | interval: 0 | fails: 0 | note:
