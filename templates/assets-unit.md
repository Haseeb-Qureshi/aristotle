<!-- FORMAT — assets/unit-NN.md: the pre-authored teaching material for
     one unit. Runtime ADAPTS these; it never improvises an evidence
     standard. `schedule.py check` validates this file, and empty or
     placeholder values FAIL — authoring it lazily wedges the course.

     Required, per unit:
       * every verify:quiz concept: >=1 quiz item with a real question
         and a real answer key
       * every verify:use concept: >=1 real apply prompt
       * every keystone: a rubric block with >=1 real claim
       * >=2 interleaved problems, each naming real concept ids
         (the first unit needs only 1 — there is nothing to mix yet)

     Distractor and avoid values may be free text. If you write one in
     Mn form, it must be a real misconception id for that concept in
     domain-map.md — that cross-reference is what lets the session name
     the misconception the learner actually hit.

     Long values may wrap: an indented continuation line is appended to
     the item above it.
-->
<!-- aristotle:assets unit: NN -->

## concept: concept-id
- quiz: <question, cold-retrievable in one line> | a: <expected answer> | distractor: M1
- quiz: <a case-judgment item if this concept's terminal use is judgment rather than recall> | a: <key> | distractor: M2
- example: worked | <fully worked example, shown at first teaching>
- apply: <application prompt; required for verify:use concepts>

## rubric: keystone-id
<!-- Teach-back grading is comparison against THIS, never holistic
     impression. Pass = every claim present AND no avoided misconception
     asserted. Never shown or recited to the learner. -->
- claim: <required claim the learner's explanation must contain>
- claim: <another>
- avoid: M1

## interleaved
<!-- A mixed set spanning earlier units. The learner must first IDENTIFY
     which concept applies — that discrimination is the transfer skill.
     Run one per standard session; the consolidation sessions at the end
     of the course draw on every unit's set. -->
- problem: <problem text> | concepts: concept-a, concept-b
- problem: <problem text> | concepts: concept-c
