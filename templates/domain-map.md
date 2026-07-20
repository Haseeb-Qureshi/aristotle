<!-- FORMAT — the anti-drift anchor. Written once at bootstrap.
     Concept IDS ARE IMMUTABLE (knowledge-state rows point at them).
     Corrections go in the append-only errata section at the bottom,
     in machine-applicable form, merged by every schedule.py run.
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
     prereqs are HARD edges: design-time sequencing constraints,
     validated by `check`. They are never a runtime gate.
     verify:  quiz (retrieval vs stored keys) | use (application only)
              | none (exposure, untracked)
     ceiling: solid | retrievable  — use `retrievable` for tacit and
              judgment concepts: the system is FORBIDDEN from demanding
              stronger evidence than "conversant", because it doesn't exist.
     threshold: yes for the 5-8 gateway concepts that reframe the field.
     misconceptions: Mn ids are machine-form — quiz distractors and
              teach-back rubrics reference them, and `check` verifies it.
-->

### concept-id
def: one line, plain language
prereqs: []
verify: quiz
ceiling: solid
threshold: no
misconceptions:
  M1: the common wrong model
  M2: the other one

## Controversies
<!-- schools of thought; fuel for spar/debate-style application items -->

## Sources
<!-- the best ~10; bound to units in plan.md, distilled into sources/ -->

## Errata
<!-- APPEND ONLY. Machine-applicable forms:
       erratum YYYY-MM-DD: remove-edge <from> -> <to>
       erratum YYYY-MM-DD: add-edge <from> -> <to>
     Prose notes are allowed but only edge ops are machine-merged.
-->
