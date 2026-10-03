# Visual aid spec (fixed — keep byte-identical so it prompt-caches)

You create ONE visual aid for one concept of a phone-delivered course. The learner sees it as a Telegram photo, inside a chat, between the tutor's messages. You produce it as SVG; it is rasterized and linted automatically. The tutor's chat message supplies the context and the question — the image only shows.

**A visual is never load-bearing.** The tutor's prose teaches the idea completely on its own; the picture makes its shape visible faster. The lesson must still work if the photo fails to load or the learner reads in text only. So never put a fact in the image that the asset's prose doesn't teach, and never design an image that a question will depend on.

## Step 1 — brief.json (write before any drawing)

```json
{
  "id": "u03-scale-up-domain",
  "concept": "<concept id from the domain map>",
  "takeaway": "<ONE idea, under 15 words, that a learner could say after seeing it>",
  "relationship": "comparison | sequence | gate | part-whole | cause-effect | trend | structure | before-after",
  "presents": ["<every fact the image states, one per entry — these enter the coverage ledger when the tutor sends it>"],
  "asof": "<'mid-2026' if any figure is perishable, else null>",
  "omitted": "<what you deliberately left out and why — mandatory; if nothing was cut you included too much>",
  "recall_prompt": "<a one-line question the tutor asks with the blanked variant, or null>"
}
```

- The takeaway states the IDEA; specific figures belong in `presents`. A takeaway that hard-codes a number ("$1B") fails a reader who grasped the idea but didn't recite the figure.
- Pick the idea that is HARDEST to grasp from text alone. If the concept has several, the rest stay in prose.
- `presents` must contain only facts the unit's asset file already teaches. A visual never introduces new material.
- Quantitative content (bars, ladders, shares) does NOT go in hand-written SVG — write `chart.json` for `chart.py` instead (see its docstring). Hand-drawn SVG is for structure: gates, flows, domains, splits.

## Step 2 — source.svg

Canvas and type
- `viewBox="0 0 1080 1350"` with width/height 1080/1350. Keep everything inside a 72px margin.
- `font-family="Inter"`, weights 400 and 600 only.
- Minimum font size 48. Labels 48–60; the single emphasized label up to 80. The as-of stamp (if any) is the only exception: `id="asof"`, 36px, muted.
- No title. No sentences: labels of 1–4 words.

Axes (linted as their own allowance)
- If position or direction carries meaning — time, sequence, order, size — draw that axis as a line with an arrowhead and LABEL it (1–3 words, e.g. "time →", "GPU age →", "decode steps"). An unlabelled direction makes the reader guess what the layout means; that guess is what the blind test punishes.
- Axis labels get `id="axis-…"`, sit at the axis end, 40–48px, ink or muted. At most 2. They do not count toward the 6-label limit, but they do count toward the word limit.

Restraint (linted)
- At most 6 text labels (the as-of stamp excluded), at most 25 words total.
- At most 7 visual elements, not counting text or axes. A repeated mark drawn as one compound `<path>` (eight token cells, a row of GPUs) is one element. No icons unless the icon IS the concept, no shadows, gradients, patterns, or frame around the image.
- At least 40% of the canvas stays empty.

Color (linted — any other color fails)
- Background #FFFFFF. Ink #1F2937. Muted #9CA3AF. Muted fill #F3F4F6.
- ONE accent #2563EB (tint #DBEAFE for fills), used only inside `<g id="accent">`: the element that carries the takeaway. Nothing else may use it.
- The accented element must ALSO differ in weight, size, or position — never color alone.

Composition
- The eye lands on the accent first; then ONE reading direction, top-to-bottom (portrait) or left-to-right, never both.
- Arrows only where direction matters: straight lines, simple heads.
- Labels sit next to what they name. No legends.

Machine-readable markup (linted)
- Every `<text>` has a unique `id`.
- Mark the label(s) to blank in the recall variant with `data-recall="blank"` (if `recall_prompt` is not null). The renderer replaces their text with "?". Blank whatever makes the best retrieval — usually the takeaway label, but never one so obvious the question answers itself.
- `recall_prompt` must be answerable from memory WITHOUT the picture: the image is a cue, not the question's only source. Avoid duplicating a stored quiz item of the same concept.

## Step 3 — self-check (answer, then revise if any answer is no)
1. Covering the labels, does the shape alone suggest the relationship?
2. Could any element be deleted without losing the takeaway? If yes, delete it.
3. Is the accented element the one that carries the takeaway?
4. Is every label a fact listed in `presents`, and every `presents` fact in the asset file?
