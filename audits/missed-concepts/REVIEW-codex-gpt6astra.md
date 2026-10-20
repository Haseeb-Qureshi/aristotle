Aristotle is usable, and the next lesson is correctly selected. The main weaknesses are in recovery, lifecycle integration, and the information supplied to the tutor—not basic scheduling arithmetic.

All execution happened under `/tmp/aristotle-review.RpgEo5`. No live files were changed. The live course’s contents still match the untouched snapshot.

| Check | Result |
|---|---|
| `python3 -m unittest discover -s tests` | **265 tests passed** |
| Course `check` | `ok`; one historical unit-1 padding warning |
| `./install.sh --check` | All three standard installations current |
| `./install.sh --check-course <copy>` | Live-course snapshot and example course current |
| Assets and sources | All 33 concept sections present; plan source references resolve |
| Visuals | All 21 pass lint; stored review hashes match |
| Requested simulator run | 18 lessons completed, then graduation stopped the 22-iteration run |

The transition rules, duplicate-grade rejection, fresh session tokens after recovery, catch-up derivation, prerequisite validation, and protection against failing untaught concepts are substantial strengths. The historical failures have produced useful, concrete safeguards. The temporary picture overlay is explicitly authorized and bounded; I would not classify its existence as drift.

The October 21 [dry-run brief](/tmp/aristotle-review.RpgEo5/next-brief.txt) says:

```text
session: 34r of 47
bookend: Session 34 · catch-up 1 of 4
type: catch-up
teach: neocloud-model
quiz these (2): cache-economics, benchmark-construction
```

Review is split between the open and exit ticket. Cache economics also receives its owed pricing/example material. Subsequent catch-ups address workload-shapes, depreciation-debate, and allocation-not-purchase teach-backs before ordinary session 34 resumes.

**Executive summary**

- The next lesson is runnable; unattended recovery still has a reliability blocker.
- All 265 tests pass, and current runtime copies match the repository.
- The live course has 20 due concepts, four catch-ups, and 14 owed-material entries.
- Simulation clears the catch-ups but graduates with two owed entries unpaid.
- Power markets receives no further probe: a 36-day gap on a seven-day interval.
- Keep varied review placement; improve selection and coverage guarantees before increasing load.
- The largest tutor risks are incomplete briefs, lost context, and grading newly invented cases.

**Ranked findings**

1. **Blocker for unattended reliability — recovery is not consistently evidence-preserving or transactional.**

   Three independent probes reproduced problems:

   - A stale draft containing `cache-economics.q1` under `## asked`, but no grades, is deleted by recovery. The bank item becomes available again. The reset path runs `git clean` over untracked logs at [schedule.py:1772](/home/haseeb/projects/aristotle/scripts/schedule.py:1772).
   - Injecting a crash after grade persistence but before owed-material bookkeeping leaves the token committed. Recovery and repeated close then skip the remaining work:

     ```text
     recover: replayed
     closed session 34r (noop)
     committed: 34r
     sessions-done: 33
     last-attended: 2026-10-19
     cache owed remains: True
     ```

     The early committed-token return is at [schedule.py:647](/home/haseeb/projects/aristotle/scripts/schedule.py:647); subsequent close work depends on `applied` at [schedule.py:2230](/home/haseeb/projects/aristotle/scripts/schedule.py:2230).
   - Replaying an October 21 draft on October 30 records attendance as October 21, but concept `last/next` as October 30/31. Grades use recovery-day `_today()` at [schedule.py:695](/home/haseeb/projects/aristotle/scripts/schedule.py:695). The existing date regression test checks only attendance, at [test_schedule.py:2386](/home/haseeb/projects/aristotle/tests/test_schedule.py:2386).

   **Recommended change:** preserve abandoned logs with questions or coverage; quarantine malformed drafts instead of deleting them. Add a durable close transaction containing the evidence date and intended bookkeeping changes, so recovery can finish every phase exactly once. Test interruption at each persistence boundary and assert concept dates as well as attendance. [Reproduction script](/tmp/aristotle-review.RpgEo5/probes.py), [results](/tmp/aristotle-review.RpgEo5/probes.txt).

2. **Should-fix — the brief omits information required for fair teach-backs and reliable resumption.**

   The next workload-shapes catch-up prints:

   ```text
   teach-back: workload-shapes
   read: assets/unit-02.md lines 21-27 (workload-shapes)
   ```

   Its rubric starts at [unit-02.md:29](/home/haseeb/projects/ai-economics/assets/unit-02.md:29). Its presented history is also absent: the engine prints coverage only for review IDs, excluding the main teach-back target. See [schedule.py:2039](/home/haseeb/projects/aristotle/scripts/schedule.py:2039) and [schedule.py:2075](/home/haseeb/projects/aristotle/scripts/schedule.py:2075).

   This conflicts with “read exactly” the supplied sections and “grade only against” presented facts. Standard sessions similarly require an interleaved problem without supplying that section’s read pointer.

   After compaction, [AGENTS.md:105](/home/haseeb/projects/bombot/AGENTS.md:105) reloads the skill, plan, state, and current draft. The draft preserves IDs but not the complete brief, prior question ledger, or coverage history.

   **Recommended change:** include rubric and eligible interleaved sections, plus coverage for every graded target. Persist the full pinned brief and expose a read-only `resume` command. Make the compaction instructions reload it. [Teach-back brief](/tmp/aristotle-review.RpgEo5/teachback-brief.txt).

3. **Should-fix — the cron’s lifecycle and reconstruction contracts do not match the engine.**

   The current [cron prompt, jobs.json:227](/home/haseeb/.hermes/cron/jobs.json:227) has several concrete mismatches:

   - After 17 days without attendance, `recover` returned `ok` and `pointer` still reported `course-status: active`; `dispatch` reported `dormant`. The cron never calls dispatch, so silence alone does **not** activate its fortnightly nudge policy.
   - It routes every non-active status through dormancy handling, including `closed` and `maintenance`.
   - Its reconstruction marker is `AI economics · Session N —`; catch-ups now insert `· catch-up X of Y` before the dash.
   - Reconstruction permits only `taught`, but `close` rejects that grade for a briefed teach-back. I reproduced that rejection.
   - For a missing log it requests the sentinel’s date, but the sentinel contains only `session: <token>`.

   **Recommended change:** give cron a deterministic engine command returning the effective lifecycle and permitted nudge action. Handle closed, paused, maintenance, and dormant separately. Persist reconstructable session metadata, update marker matching, and leave missing teach-back evidence owed rather than converting it into `taught`. [Additional probe results](/tmp/aristotle-review.RpgEo5/edge_checks.txt).

4. **Should-fix — review variety is appropriate, but the selection policy provides insufficient protection against neglect.**

   The [simulation](/tmp/aristotle-review.RpgEo5/sim22.txt) produced:

   | Measure | Result |
   |---|---:|
   | Teaching-session review average | 27 / 16 = **1.69** |
   | Review misses | 7 / 37 = **18.9%** |
   | Power-markets gap at final lesson | **36 days** |
   | Power-markets scheduled interval | **7 days** |
   | Unpaid owed entries | **2** |

   The missing material is power-market deal unbundling/heat-rate options and batching’s second owed item. Graduation reports untaught concepts and missing teach-backs, but not remaining `owed.md` material: [schedule.py:1948](/home/haseeb/projects/aristotle/scripts/schedule.py:1948).

   A comparison pinned to two reviews added only **five probes** across the remaining course and reached power markets, though batching’s second debt still remained.

   **My judgment:** retain no-review sessions and exit tickets. A five-week gap is difficult to justify for a concept currently scheduled at seven days. Alternating fresh/backlog queues is an improvement, but relative lateness alone does not provide a service guarantee.

   **Recommended change:** reserve some existing review capacity for concepts approaching a maximum acceptable gap; report when available capacity cannot meet it. Include unpaid owed material in checkpoints and graduation, and explicitly repay or retire it. Test this at several attendance cadences and miss patterns before changing the average workload.

5. **Should-fix — “expensive author, cheap executor” breaks down once the tutor must invent transfer questions.**

   [SKILL.md:40](/home/haseeb/projects/aristotle/SKILL.md:40) requires fresh cases after bank use, and review sessions prohibit bank items altogether. However, most concepts have case-specific answer keys, not reusable scoring criteria. Interleaved problems have prompts and concept lists but no required scoring key: [templates/assets-unit.md:63](/home/haseeb/projects/aristotle/templates/assets-unit.md:63).

   Thus a weaker tutor must invent the case, supply missing facts, judge novelty, and construct its evidence standard. That is considerable authoring work at runtime.

   There is also an unresolved teach-back conflict: “every claim present” versus “never fail on an unpresented fact.” The archived catch-up audit explicitly awarded `rubric-pass` while recording an absent rubric fact supplied only in closing feedback. That is evidence of an ambiguous contract, not proof that the current model will always repeat it.

   **Recommended change:** author reusable concept-level scoring criteria and several transfer structures with required evidence. Define how a teach-back handles previously unpresented rubric claims, separating newly supplied instruction from demonstrated retention.

6. **Should-fix — the capstone artifact is materially behind the syllabus.**

   The plan assigns serving-economics, fleet/residual-value, and moat sections to units 2–4. The current [CoreWeave memo](/home/haseeb/projects/ai-economics/artifact/coreweave-memo.md:7) contains two substantive sections—what CoreWeave sells and customer/model tenor—with unit 2 still an open thread at [line 57](/home/haseeb/projects/ai-economics/artifact/coreweave-memo.md:57).

   Unit 8’s application assumes those sections already exist: [unit-08.md:28](/home/haseeb/projects/ai-economics/assets/unit-08.md:28). The engine prints artifact milestones, but the standard-session procedure never clearly allocates time to completing or recording them.

   **Recommended change:** reconcile missing artifact sections now, using learner-authored reasoning already captured in logs where available. At checkpoints, report artifact progress separately from concept coverage and assign one bounded writing task. Avoid leaving the final session to assemble several missing units’ work.

7. **Should-fix — several remaining procedure instructions cannot be followed literally.**

   | Contract gap | Evidence | Recommended change |
   |---|---|---|
   | Placement needs a file bootstrap explicitly excludes from the course | [SKILL.md:73](/home/haseeb/projects/aristotle/SKILL.md:73), [bootstrap.md:238](/home/haseeb/projects/aristotle/bootstrap.md:238) | Include a small placement procedure in every course. |
   | Reprune still requires hand-editing the engine-owned counter | [checkpoint.md:64](/home/haseeb/projects/aristotle/checkpoint.md:64) | Extend the engine command to perform validated resizing. |
   | “Keep trying” prescribes `taught` without the coverage line required by close | [checkpoint.md:35](/home/haseeb/projects/aristotle/checkpoint.md:35) | Require actual reteaching and coverage, or provide a separate adjudication transition. |
   | Runtime must refresh figures, while session instructions prohibit raw external content and bootstrap confines ingestion to authoring | [bootstrap.md:51](/home/haseeb/projects/aristotle/bootstrap.md:51), [bootstrap.md:165](/home/haseeb/projects/aristotle/bootstrap.md:165), [SKILL.md:92](/home/haseeb/projects/aristotle/SKILL.md:92) | Define a source-refresh stage that updates notes before teaching; otherwise use explicitly dated historical examples. |

   Also update `scheduling.md` from the tested cron contract: its worked example still reads the newest log directly and only reconstructs when the log is missing, overlooking empty drafts.

8. **Should-fix — validation can report a healthy installation with required components missing.**

   Removing `templates/` and `references/` from a disposable course produced both `check: ok` and a successful `--check-course`. The installer deliberately skips absent directories at [install.sh:57](/home/haseeb/projects/aristotle/install.sh:57).

   Separately, a state date of `2026-99-99` passed `check`; dates are regex-checked rather than calendar-validated at [schedule.py:192](/home/haseeb/projects/aristotle/scripts/schedule.py:192).

   **Recommended change:** fail on missing required runtime resources and validate dates with `date.fromisoformat`. Current live resources are present; these are weaknesses in the health checks, not current installation drift.

9. **Nit — the simulator’s description overstates its tutor fidelity.**

   It is useful for queue dynamics, but it writes no asked ledger, always passes teach-backs, and fabricates a `token-pnl` pass when no grades exist. It also prints failures without making them a failing process exit. See [simulate.py:25](/home/haseeb/projects/aristotle/audits/missed-concepts/simulate.py:25).

   **Recommended change:** describe it as a scheduler simulation, remove fabricated fallback evidence, fail loudly, and add interrupted sessions and rubric failures. Keep separate capped-student tests for novelty, factual fairness, and instruction compliance. Its current results establish scheduling behavior, not successful learning.

10. **Nit — the stated runtime model is outdated.**

    [config.yaml:2](/home/haseeb/.hermes/config.yaml:2) sets the primary default to **`gpt-6.1-sol`**; `gpt-6-sol` is configured for compression. The gateway is active and started after that configuration file’s modification time. Individual session overrides remain possible.

    **Recommended change:** record the effective model and procedure/engine revision with future behavioral audits, so “tested on the production tutor” is verifiable.

**Top 3 next steps**

1. **Fix recovery first:** preserve question/coverage logs, retain evidence dates, and make interrupted close completion idempotent across every write boundary.
2. **Complete the runtime contract:** persist resumable briefs, include teach-back coverage/rubrics, and align cron lifecycle and reconstruction behavior with the engine.
3. **Keep review variety while bounding neglect:** test an age-aware selection policy, expose remaining owed material at graduation, and catch up the capstone artifact alongside the four already-scheduled catch-ups.