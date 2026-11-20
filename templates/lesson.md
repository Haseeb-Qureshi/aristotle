<!-- FORMAT — lessons/<key>.md, one file per session that teaches.

     <key> is the concept id for an ordinary lesson; `unit-NN-case` for a
     unit's last session (a case study); `review-NN` for the review block
     after unit NN; `final` for the closing synthesis. `begin` prints the
     file on a `lesson:` line and the tutor teaches it section by section,
     one section per turn. Nothing here is parsed by the engine except
     that the file exists: write for the learner and the tutor.

     This is the course material itself, written out in full, the way a
     good textbook chapter or a strong analyst note is. The session is
     only as good as this file: a tutor handed one paragraph teaches one
     paragraph. Write the whole lesson.

     WHAT A LESSON IS
     - ONE idea, developed. 5-8 numbered sections that build on each
       other, each a complete thought: the claim in plain words, the
       mechanism behind it, real numbers with their dates, and a named
       real case. 120-220 words a section; 900-1,400 words of teaching
       in all (the Ask / Listen-for lines and the back matter are extra).
     - Literal and specific. "Chime earns roughly $150-200 a user a
       year" teaches; "neobanks have limited monetization" does not.
       Every number comes from the course's sources/ notes or assets,
       never from memory.
     - Plain words. Define each term of art the first time it appears,
       in the sentence that uses it. Prefer a concrete picture or an
       analogy from the learner's own field to an abstraction.
     - It says what the idea is FOR: what a person who knows this does
       differently (reads a pitch, sizes a risk, asks a question).

     THE QUESTIONS
     - Each section ends with one **Ask:** and its **Listen for:**.
       The Ask opens the NEXT section: a prediction or a piece of
       reasoning the learner can do with what the lesson has already
       given them. Never a recall check on the paragraph just read, never
       a riddle, never "what evidence would you want to see".
     - The fairness test, applied to every Ask: could a sharp reader who
       has read only this lesson so far (plus the lessons under
       "Builds on") answer it in one or two sentences? If it needs a
       fact that comes later, move the fact or cut the question.
     - **Listen for:** tells the tutor what a good answer contains, what
       the likely wrong turn is, and what to add either way.

     A CASE STUDY (unit-NN-case, review-NN, final) has the same shape,
     but its sections walk one real company, deal or document from the
     outside in, with the unit's concepts doing the work, and its last
     Ask is the learner's own read ("so would you lend against this?").
     The Listen-for on that last Ask names the keystone's rubric claims
     in plain words.
-->
# <The lesson's title: a claim or a question, not a topic label>

> **Concept:** <id> · Unit N: <the unit's question>
> **Builds on:** <earlier lessons this one stands on, in plain words>
> **Goal:** <what the learner can do after this, in one line>
> **Figures as of:** <month year>. Refresh anything dated before teaching.

## Why this matters

<60-120 words. A concrete hook: a real deal, a number that looks wrong, a claim someone will make to the learner next month. Why a person in their seat needs this.>

**Ask:** <a guess that gets them thinking before the mechanics>
**Listen for:** <a guess is fine; what to pick up from it>

## 1. <Section title that states the idea>

<120-220 words: the claim, the mechanism, the numbers, the named case.>

**Ask:** <the question that opens section 2>
**Listen for:** <what a good answer has; the likely wrong turn; what to add>

## 2. <...>

## The model in one screen

- <4-6 lines: the mental models to keep, each a full sentence>

## Discussion questions

1. **<An application in the learner's own work.>**
   *A strong answer:* <what it covers>

## Sources

- `sources/<note>.md` (<which parts>)
