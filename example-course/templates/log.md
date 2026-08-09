<!-- FORMAT — log/YYYY-MM-DD-<session>.md, written at close, before
     `S close` is run. <session> is the token `S begin` printed: digits,
     optional r-suffix for a repair (14, 14r, 14r2).

     KEEP IT SHORT (~20 lines). Grade lines are the ONLY channel into the state
     machine, and only lines under `## grades` are read — an example
     quoted in prose elsewhere cannot mutate mastery. The grammar is
     exact, and anything that looks like a grade but doesn't parse is a
     hard error:

       - grade: <concept-id> | result: <result> | note: <free text, no "|">

     results (the complete writable set):
       taught       first teaching             -> due tomorrow
       pass         retrieval/application correct -> interval up a rung
       fail         missed                     -> interval back one rung
       rubric-pass  teach-back rubric satisfied
       rubric-fail  teach-back rubric not met  -> may schedule a repair

     ONE verdict per concept per session. A same-session re-probe does
     not upgrade the original result, and two lines for one concept is a
     hard error — the next spaced appearance is the real evidence.

     Note the EVIDENCE, not the vibe: which misconception was hit, what
     the learner actually said. That note is what the next session reads.

     '## asked' is the question ledger — one line per question you posed,
     matched case-insensitively. A bank item is its id: <concept>.q2,
     <concept>.apply1, <concept>.int1 (position in the assets file, from
     1). A case you built is a one-line signature of the SITUATION, not
     the wording. `begin` replays recent entries and every bank id ever
     used; anything it lists is dead. Skipping this section is how the
     next session re-asks your questions and calls it retrieval.
-->
session: N

## taught
<one line: what was covered>

## grades
- grade: concept-a | result: pass | note: clean, cited the marginal case
- grade: concept-b | result: fail | note: hit M1, confused avg with marginal
- grade: concept-c | result: taught | note: intro via the worked example

## asked
- concept-a.q2
- concept-b.apply1
- vendor pitch claims X despite Y — is the claim coherent?

## open question
<the thread to reopen next session — the parked tangent, or the hook you
 left them on>
