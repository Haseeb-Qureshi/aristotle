<!-- FORMAT — assets/unit-NN.md. The pre-authored teaching material for
     one unit. Runtime ADAPTS these; it never improvises evidence
     standards. `schedule.py check` validates this file structurally —
     placeholder assets FAIL, so authoring it lazily wedges the course.

     Required, per unit:
       * every verify:quiz concept: >=1 quiz item WITH an answer key,
         and a worked example
       * every verify:use concept: >=1 apply prompt
       * every keystone: a rubric block with >=1 claim and >=1 avoid
       * >=3 interleaved problems spanning EARLIER units
     Distractor and avoid ids must exist in that concept's
     misconceptions list in domain-map.md.
-->
<!-- elenchus:assets unit: NN -->

## concept: concept-id
- quiz: <question, cold-retrievable in one line> | a: <expected answer> | distractor: M1
- quiz: <a case-judgment item if the concept's terminal use is judgment, not recall> | a: <key> | distractor: M2
- example: worked | <fully worked example — shown at first teaching>
- example: faded | <same skill, last step left to the learner — shown at
  this concept's FIRST spaced re-encounter, not to a later concept>
- self-explain: <"why does that follow?" prompt>
- apply: <application prompt; required for verify:use concepts, which are
  never quizzed as recall>

## rubric: keystone-id
<!-- Teach-back grading is comparison against THIS, never holistic
     impression. Pass = all claims present AND no avoided misconception. -->
- claim: <required claim the learner's explanation must contain>
- claim: <another>
- avoid: M1

## interleaved
<!-- Mixed set spanning earlier units. The learner must first IDENTIFY
     which concept applies — that discrimination is the transfer skill.
     Run one per standard session; run the FULL set in the unit-review
     session before teach-back. -->
- problem: <problem text> | concepts: concept-a, concept-b
- problem: <problem text> | concepts: concept-c
- problem: <problem text> | concepts: concept-a
