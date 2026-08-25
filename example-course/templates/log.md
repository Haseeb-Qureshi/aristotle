<!-- FORMAT — log/YYYY-MM-DD-<session>.md, written at close, before
     `S close` is run. <session> is the token `S begin` printed: digits,
     optional r-suffix for a repair (14, 14r, 14r2).

     KEEP IT SHORT (~25 lines). Grade lines are the ONLY channel into the state
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

     '## taught' is the coverage record — one line per concept whose
     facts you presented this session, first teaching AND substantive
     feedback (feedback teaches):

       - <concept-id>: <what you presented> | without: <what you didn't>

     The `| without:` clause is optional; omit it when nothing notable
     was held back. Keep each taught-line ONE physical line — a wrapped
     continuation reads as prose and is dropped — and every `- ` bullet
     under '## taught' is parsed as this grammar, so put commentary
     elsewhere. Ids match case-insensitively, and `close` HARD-ERRORS
     if a `result: taught` grade has no taught-line for that concept.
     `begin` replays these records to the next session, which grades ONLY
     against them — a fact absent here goes into its question instead of
     being asked for. So when unsure whether you presented something, put
     it under `without:`: over-claiming coverage fails a learner for your
     elision; under-claiming only makes future questions more generous.

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
- concept-c: worked example, the cost curve | without: the 2025 teardown
- concept-b: feedback on marginal vs average, one number redone

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
