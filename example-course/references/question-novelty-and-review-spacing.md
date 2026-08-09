# Question novelty and review spacing

Read this when a session is mostly retrieval — a `review` or
`consolidation` type, or any session whose queue is long.

<!-- PROVENANCE: first drafted by a runtime tutor (Hermes/Codex) after
     it repeated a session's questions and was called on it, then
     adopted here with its grammar corrected — it had invented a
     `## prompts` section the engine does not parse. Keep this file and
     the engine in the same grammar: `## asked`, parsed by
     scripts/schedule.py and replayed by `begin`. A procedure file that
     names a section the parser ignores is worse than no file. -->

## The failure this prevents

A session can quiz exactly the right concepts while merely paraphrasing
the last session's cases. That tests memory for the item, not transfer
of the idea — and the learner notices before the system does. Adjacent
review sessions over a small concept pool amplify it: two stateless
tutors, same state, same policy, same questions.

## The durable ledger

Every session log carries a `## asked` section — the exact grammar in
`templates/log.md`. One line per question posed:

- a **bank item id** when the asset provided one: `<concept>.q2`,
  `<concept>.apply1`, `<concept>.int1` (position in the assets file,
  counting from 1); or
- a **case signature** for anything you built: entity/domain, the
  decision being made, the evidence supplied, the inference required.

```
- cache-economics.q2
- diagnosis | SaaS refactor, bill doubled at flat usage, infer cache invalidation
```

`begin` replays the last three sessions' entries and every bank id ever
used, matched case-insensitively. Anything it lists is dead. Bank items
are **single-use for the whole course** — after first use, every probe
of that concept is a case you build.

## Item types — vary the type, not just the case

Rotating the *type* of question is the cheapest real novelty available,
and it tests different things:

- **mechanism recall** — rebuild the causal chain
- **numerical application** — derive a figure from the mechanism
- **counterfactual** — change one input, predict the direction
- **diligence judgment** — a claim in the wild: coherent or not?
- **cross-concept diagnosis** — which concepts even apply here?
- **Fermi estimation** — order of magnitude, graded within 2x

A concept probed three times should have met three types.

## The structural-transfer test

Changing names, numbers, or wording is not novelty. A transfer case must
materially change at least **two** of:

1. the decision the learner must make;
2. the evidence available;
3. the inference chain;
4. the combination of concepts required;
5. the setting or the stakeholder incentives.

A familiar company is fine when the decision and evidence structure are
new. If you cannot build a case that clears this bar, **skip the concept
this session** rather than paraphrase it — a skipped probe costs one
spaced repetition; a fake one corrupts the evidence record and teaches
the learner that the quizzing is theatre.

## Review placement

Never design two generic review sessions back-to-back over the same
pool. The shape that works:

- retrieval embedded in ordinary teaching sessions;
- a mixed review after every 2–3 units, reaching back across *all*
  prior units, not just the most recent;
- one terminal synthesis on the artifact or a genuinely integrated
  decision — **not** another recall block.

`bootstrap.md` step 6 builds this into the plan; `## Review:` blocks in
`plan.md` are how it is expressed. If you inherit a course whose plan
still stacks reviews at the end, the second one must exclude the first's
ledger entries and run as cross-unit synthesis.

## Before you open a retrieval-heavy session

- Read what `begin` printed under `asked recently` and `bank items
  used` — that is the ledger; you do not need to go hunting in logs.
- For each queued concept, pick an item type it has not met.
- Confirm you have a structurally fresh case for each. If you don't,
  cut that concept from the session rather than improvising a
  paraphrase.
- At close, record **every** question you actually asked under
  `## asked` — including the ones you improvised mid-session, and
  including any the learner answered badly. The next tutor is blind
  without it.
