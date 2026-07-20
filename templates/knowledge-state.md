<!-- elenchus:state
committed-sessions:
solid-pending: none
repair-pending: none
-->
<!-- FORMAT — this file is written ONLY by scripts/schedule.py.
     Never hand-edit; the agent's write surface is grade lines in the
     session log. One concept per PHYSICAL line, led by "- ".
     Fields are label-parsed (order does not matter), " | " separated,
     note is always last and may not contain "|".
       verify   quiz | use | none
       ceiling  solid | retrievable          (cap on mastery)
       mastery  none | exposed | retrievable | solid
       status   untaught | active | plateaued | dropped
       reprobe  - | pending | done           (delayed-solid gate)
     Dates are YYYY-MM-DD in the course timezone; "-" means unset.
-->
- id: CONCEPT-ID | verify: quiz | ceiling: solid | mastery: none | status: untaught | last: - | next: - | interval: 0 | fails: 0 | reprobe: - | note:
