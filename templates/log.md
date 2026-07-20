<!-- FORMAT — log/YYYY-MM-DD-<session>.md, written at close.
     <session> is the session token: digits, optional r-suffix (17, 17r).
     KEEP IT <=15 LINES. The grade lines are the ONLY channel into the
     state machine — schedule.py commit-grades parses them and hard-errors
     on anything malformed, so the grammar is exact:

       - grade: <concept-id> | result: <result> | note: <free text, no "|">

     results (the complete writable set):
       taught       first teaching of a concept   -> exposed, due tomorrow
       pass         retrieval/application correct -> band up, interval up
       fail         missed                        -> interval steps back one
       rubric-pass  teach-back rubric satisfied   -> schedules delayed re-probe
       rubric-fail  teach-back rubric not met     -> may schedule repair

     `solid` is NOT writable. The script awards it only when a delayed
     re-probe has passed AND the concept survived the 35-day interval.
     Note the EVIDENCE, not the vibe: which misconception was hit, what
     the learner actually said.
-->
session: N

## taught
<one line: what was covered>

## grades
- grade: concept-a | result: pass | note: clean, cited the marginal case
- grade: concept-b | result: fail | note: hit M1, confused avg with marginal
- grade: concept-c | result: taught | note: intro via worked example

## open question
<the thread to reopen next session — a parked tangent, or the hook>
