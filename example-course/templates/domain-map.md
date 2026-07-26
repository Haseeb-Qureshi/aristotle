<!-- FORMAT — the anti-drift anchor. Written once at bootstrap.
     Concept IDS ARE IMMUTABLE (knowledge-state rows point at them).
     Corrections go in the append-only errata section at the bottom, in
     machine-applicable form, merged by every schedule.py run.
     Cap ~4k words so the whole map always fits in context.
-->
topic: <topic>
terminal-task: <the concrete thing the user will be able to DO — every
  concept below must justify its seat by tracing to this line>
research: yes|no
timezone: America/Los_Angeles
sessions: 30

<!-- CONCEPTS — roughly 0.75 x session count.
     Granularity rule: one concept = one session's teachable unit = one
     interpretable evidence judgment. If no single retrieval question
     separates a strong learner from a weak one, it is mis-sized.
     prereqs   HARD edges: design-time sequencing constraints, validated
               by `check`. Never a runtime gate.
     verify    quiz (retrieval against stored keys) | use (application
               only — judgment and tacit skills are never quizzed as
               recall) | none (exposure, untracked)
     threshold yes for the 5-8 gateway concepts that reframe the field.
               `reprune` refuses to drop them, so tag deliberately.
     misconceptions  Mn ids are machine-form: quiz distractors and
               teach-back rubrics reference them and `check` verifies it.
               Every KEYSTONE needs at least one, or its rubric has
               nothing to warn against.

     There is no mastery or ceiling field. Mastery is derived from the
     review interval; nothing in the system stores a band.
-->

### concept-id
def: one line, plain language
prereqs: []
verify: quiz
threshold: no
misconceptions:
  M1: the common wrong model
  M2: the other one

## Sources
<!-- the best ~10; bound to units in plan.md, distilled into sources/ -->

## Errata
<!-- APPEND ONLY. Machine-applicable forms (case and bullets tolerated):
       erratum YYYY-MM-DD: remove-edge <from> -> <to>
       erratum YYYY-MM-DD: add-edge <from> -> <to>
     Prose notes are allowed but only edge ops are machine-merged.
     Everything after a '## ' heading is outside the concept blocks, so
     prose here cannot corrupt the last concept's fields.
-->
