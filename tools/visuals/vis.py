#!/usr/bin/env python3
"""Visual-aid toolchain for Aristotle courses. See SPEC.md.

A visual lives in its own directory:  <course>/visuals/<id>/
  brief.json      the takeaway-first brief (author writes)
  source.svg      hand-written SVG (author writes) — OR —
  chart.json      data for chart.py-style generation (author writes)
  teach.png       rendered (build)
  recall.png      rendered with data-recall="blank" labels as "?" (build)
  meta.json       lint result, blind-review sentence, verdict (build)

  vis.py build <dir> [--force]   chart -> lint -> render -> blind review
  vis.py preview <dir>           lint + render, no model call
  vis.py lint <dir>              zero-token checks only
Model calls happen only in `blind`/`judge` (gpt-6-sol via codex, ~30 output
tokens) and are skipped when the source hash is unchanged.
"""
import hashlib, json, re, subprocess, sys, tempfile
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
NS = "{http://www.w3.org/2000/svg}"
W, H, MARGIN = 1080, 1350, 72
MIN_FONT, ASOF_FONT, AXIS_FONT, MAX_LABELS, MAX_WORDS = 48, 36, 40, 6, 25
MAX_AXES = 2
ACCENT = {"#2563eb", "#dbeafe"}
ALLOWED = {"#ffffff", "#1f2937", "#9ca3af", "#f3f4f6"} | ACCENT
BANNED_TAGS = {"linearGradient", "radialGradient", "filter", "pattern",
               "image", "foreignObject"}
# Sol for both roles (2026-10-03): luna-as-judge gave reasons its own
# input contradicted, and a sharper reader is the stricter test anyway —
# it still never sees the brief, so it stays blind.
REVIEWER = "gpt-6-sol"
JUDGE = "gpt-6-sol"


def resvg():
    for p in (Path.home() / ".local/bin/resvg", Path("/usr/local/bin/resvg")):
        if p.exists():
            return str(p)
    return "resvg"


def render(svg: Path, png: Path):
    subprocess.run([resvg(), "--skip-system-fonts", "--use-fonts-dir",
                    str(FONTS), "-w", str(W), str(svg), str(png)],
                   check=True, capture_output=True)


def recall_variant(svg: Path, out: Path) -> bool:
    """Same drawing, takeaway label(s) replaced by '?'. Free retrieval."""
    ET.register_namespace("", NS[1:-1])
    tree = ET.parse(svg)
    hit = False
    for t in tree.iter(NS + "text"):
        if t.get("data-recall") == "blank":
            for child in list(t):
                t.remove(child)
            t.text = "?"
            hit = True
    if hit:
        tree.write(out, encoding="unicode")
    return hit


# ------------------------------------------------------------- lint
def _style(el):
    out = {}
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _attr(el, name):
    return _style(el).get(name) or el.get(name)


def _norm(c):
    c = c.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", c):
        c = "#" + "".join(ch * 2 for ch in c[1:])
    return {"white": "#ffffff"}.get(c, c)


def lint(d: Path):
    errs = []
    brief = json.loads((d / "brief.json").read_text())
    if len(brief.get("takeaway", "").split()) >= 15:
        errs.append("brief: takeaway must be under 15 words")
    for k in ("omitted", "presents"):
        if not brief.get(k):
            errs.append(f"brief: '{k}' is mandatory")
    svg = d / "source.svg"
    root = ET.parse(svg).getroot()
    if root.get("viewBox") != f"0 0 {W} {H}":
        errs.append(f"viewBox must be '0 0 {W} {H}'")

    labels, words, axes, ids = 0, 0, 0, set()
    blanks = 0

    def walk(el, size, in_accent):
        nonlocal labels, words, blanks, axes
        tag = el.tag.replace(NS, "")
        if tag in BANNED_TAGS:
            errs.append(f"<{tag}> is not allowed")
        fs = _attr(el, "font-size")
        if fs:
            size = float(re.sub(r"px$", "", fs))
        acc = in_accent or el.get("id") == "accent"
        for prop in ("fill", "stroke", "stop-color", "color"):
            v = _attr(el, prop)
            if not v or v in ("none", "transparent"):
                continue
            c = _norm(v)
            if c not in ALLOWED:
                errs.append(f"color {v} on <{tag} id={el.get('id')}> "
                            "is outside the palette")
            elif c in ACCENT and not acc:
                errs.append(f"accent color on <{tag} id={el.get('id')}> "
                            "outside <g id=\"accent\">")
        if tag == "text":
            tid = el.get("id")
            if not tid:
                errs.append("every <text> needs an id")
            elif tid in ids:
                errs.append(f"duplicate text id {tid}")
            ids.add(tid)
            content = "".join(el.itertext()).strip()
            axis = bool(tid) and tid.startswith("axis")
            floor = ASOF_FONT if tid == "asof" else AXIS_FONT if axis else MIN_FONT
            if size is None or size < floor:
                errs.append(f"font-size {size} on '{content}' below {floor}")
            if axis:
                axes += 1
                words += len(content.split())
            elif tid != "asof":
                labels += 1
                words += len(content.split())
            if el.get("data-recall") == "blank":
                blanks += 1
            return
        for child in el:
            walk(child, size, acc)

    walk(root, None, False)
    if labels > MAX_LABELS:
        errs.append(f"{labels} labels, max {MAX_LABELS}")
    if axes > MAX_AXES:
        errs.append(f"{axes} axis labels, max {MAX_AXES}")
    if words > MAX_WORDS:
        errs.append(f"{words} words, max {MAX_WORDS}")
    if brief.get("recall_prompt") and not blanks:
        errs.append("recall_prompt set but no data-recall=\"blank\" label")

    # geometry from the real renderer: margins and overlaps
    q = subprocess.run([resvg(), "--skip-system-fonts", "--use-fonts-dir",
                        str(FONTS), "--query-all", str(svg)],
                       capture_output=True, text=True)
    boxes = {}
    for line in q.stdout.splitlines():
        i, x, y, w, h = line.split(",")
        if i in ids:
            boxes[i] = (float(x), float(y), float(w), float(h))
    for i, (x, y, w, h) in boxes.items():
        if x < MARGIN or y < MARGIN or x + w > W - MARGIN or \
                y + h > H - MARGIN:
            errs.append(f"text '{i}' breaks the {MARGIN}px margin "
                        f"(box {x:.0f},{y:.0f} {w:.0f}x{h:.0f})")
    items = list(boxes.items())
    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            (ia, (ax, ay, aw, ah)), (ib, (bx, by, bw, bh)) = items[a], items[b]
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                errs.append(f"texts '{ia}' and '{ib}' overlap")

    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "x.png"
        render(svg, png)
        im = Image.open(png).convert("L")
        white = sum(im.histogram()[250:]) / (im.width * im.height)
    if white < 0.40:
        errs.append(f"only {white:.0%} empty canvas, need 40%")
    return errs


# ------------------------------------------------------------ chart
def chart(d: Path):
    """chart.json -> source.svg, so quantities are scaled exactly.

    {"type": "bars", "items": [{"label": "H100 air", "value": 40,
      "text": "40 kW"}, ...], "accent": 2, "asof": "mid-2026"}
      horizontal bars, one row per item, label above its bar. Optional
      "axis": "rack power" draws a labelled value axis under the bars.
    {"type": "stack", "items": [...same...], "accent": 0, "asof": ...}
      one vertical column split into parts, labels to the right.
    The accented item is drawn in the accent color AND its label in
    weight 600; its text gets data-recall="blank".
    """
    spec = json.loads((d / "chart.json").read_text())
    items, acc = spec["items"], spec.get("accent")
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" '
           f'height="{H}" viewBox="0 0 {W} {H}" font-family="Inter">',
           f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>']
    top, bottom = 150, H - 170

    def label(i, x, y, s, size=52, anchor="start"):
        bold = i == acc
        recall = ' data-recall="blank"' if bold else ""
        fill = "#2563EB" if bold else "#1F2937"
        return (f'<text id="t{i}{"v" if size != 52 else ""}" x="{x}" y="{y}" '
                f'font-size="{size}" font-weight="{600 if bold else 400}" '
                f'fill="{fill}" text-anchor="{anchor}"{recall}>{escape(s)}</text>')

    if spec["type"] == "bars":
        vmax = max(it["value"] for it in items)
        row = min(190, (bottom - top) / len(items))
        y0 = top + ((bottom - top) - row * len(items)) / 2
        barmax = W - 2 * MARGIN
        for i, it in enumerate(items):
            y = y0 + i * row
            w = max(10, barmax * it["value"] / vmax)
            fill = "#2563EB" if i == acc else "#9CA3AF"
            bar = f'<rect x="{MARGIN}" y="{y + 70:.0f}" width="{w:.0f}" ' \
                  f'height="44" fill="{fill}"/>'
            lab = f'{it["label"]} · {it["text"]}'
            grp = [bar, label(i, MARGIN, y + 52, lab)]
            out.append(f'<g id="accent">{"".join(grp)}</g>' if i == acc
                       else "".join(grp))
        if spec.get("axis"):
            # value axis under the bars: what bar LENGTH measures
            ay = y0 + len(items) * row + 10
            out.append(f'<line x1="{MARGIN}" y1="{ay:.0f}" x2="{W - MARGIN - 4}" '
                       f'y2="{ay:.0f}" stroke="#1F2937" stroke-width="3"/>'
                       f'<path d="M{W - MARGIN} {ay:.0f} l-22 -11 v22 z" fill="#1F2937"/>'
                       f'<text id="axis-x" x="{W - MARGIN}" y="{ay + 56:.0f}" '
                       f'font-size="44" fill="#9CA3AF" text-anchor="end">'
                       f'{escape(spec["axis"])}</text>')
    elif spec["type"] == "stack":
        total = sum(it["value"] for it in items)
        x, cw, y = MARGIN, 260, top
        span, gap = bottom - top, 8
        for i, it in enumerate(items):
            h = span * it["value"] / total - gap
            fill = "#2563EB" if i == acc else ("#9CA3AF" if i % 2 else "#F3F4F6")
            stroke = '' if fill != "#F3F4F6" else ' stroke="#9CA3AF" stroke-width="2"'
            mid = y + h / 2
            grp = [f'<rect x="{x}" y="{y:.0f}" width="{cw}" height="{h:.0f}" '
                   f'fill="{fill}"{stroke}/>',
                   label(i, x + cw + 48, mid - 6, it["label"]),
                   label(i, x + cw + 48, mid + 58, it["text"], size=50)]
            out.append(f'<g id="accent">{"".join(grp)}</g>' if i == acc
                       else "".join(grp))
            y += h + gap
    else:
        sys.exit(f"unknown chart type {spec['type']}")
    if spec.get("asof"):
        out.append(f'<text id="asof" x="{W - MARGIN}" y="{H - MARGIN - 24}" '
                   f'font-size="36" fill="#9CA3AF" text-anchor="end">'
                   f'as of {escape(spec["asof"])}</text>')
    out.append("</svg>")
    (d / "source.svg").write_text("\n".join(out))


# ------------------------------------------------------------ blind
def _codex(prompt, image=None, model=REVIEWER):
    cmd = ["codex", "exec", "--ignore-user-config",
           "--dangerously-bypass-approvals-and-sandbox",
           "--skip-git-repo-check", "--ephemeral", "-m", model,
           "-c", 'model_reasoning_effort="low"', "--json"]
    if image:
        cmd += ["-i", str(image)]
    cmd.append("-")
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                       timeout=300, cwd=tempfile.gettempdir())
    msg = ""
    for line in r.stdout.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "item.completed" and \
                e["item"].get("type") == "agent_message":
            msg = e["item"]["text"].strip()
    if not msg:
        raise RuntimeError(f"reviewer returned nothing: {r.stderr[-300:]}")
    return msg


def blind(d: Path):
    """A reviewer that never saw the brief says what the image teaches;
    a second text-only call checks it against the author's takeaway."""
    takeaway = json.loads((d / "brief.json").read_text())["takeaway"]
    seen = _codex("You are shown an image from an economics course. Do not "
                  "use any tools. In ONE sentence, what idea is this image "
                  "teaching?", image=d / "teach.png")
    return seen, judge(takeaway, seen)


def judge(takeaway, seen):
    return _codex(
        "Do not use any tools.\nA (what the author meant): " + takeaway +
        "\nB (what a reader took away): " + seen +
        "\nDoes B convey A's core idea? Count it as conveyed if A follows "
        "directly from what B states (numbers B gives that imply A's ratio "
        "count). B may be vaguer or add detail, but must not miss or "
        "contradict it. If B restates A in substance, that is a MATCH. "
        "Reply exactly MATCH or MISMATCH, then ' — ' and a reason under "
        "12 words.", model=JUDGE)


# ------------------------------------------------------------ build
def build(d: Path, force=False):
    if (d / "chart.json").exists():
        chart(d)
    errs = lint(d)
    meta_p = d / "meta.json"
    if errs:
        meta_p.write_text(json.dumps({"lint": errs}, indent=1))
        print(f"{d.name}: LINT FAIL")
        for e in errs:
            print("  -", e)
        return False
    render(d / "source.svg", d / "teach.png")
    with tempfile.TemporaryDirectory() as tmp:
        v = Path(tmp) / "recall.svg"
        if recall_variant(d / "source.svg", v):
            render(v, d / "recall.png")
    sha = hashlib.sha256((d / "source.svg").read_bytes() +
                         (d / "brief.json").read_bytes()).hexdigest()[:16]
    old = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    if old.get("sha") == sha and old.get("verdict") and not force:
        print(f"{d.name}: unchanged, blind review cached — {old['verdict']}")
        return old["verdict"].startswith("MATCH")
    seen, verdict = blind(d)
    meta_p.write_text(json.dumps({"sha": sha, "lint": [], "reviewer": seen,
                                  "verdict": verdict}, indent=1))
    print(f"{d.name}: {verdict}\n  reviewer saw: {seen}")
    return verdict.startswith("MATCH")


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:] or ["-h"]
    if cmd == "build":
        ok = all([build(Path(p).resolve(), "--force" in rest) for p in rest
                  if not p.startswith("--")])
        sys.exit(0 if ok else 1)
    elif cmd == "judge":
        # re-score the stored reader sentence; never re-rolls the reader
        d = Path(rest[0]).resolve()
        meta = json.loads((d / "meta.json").read_text())
        takeaway = json.loads((d / "brief.json").read_text())["takeaway"]
        meta["verdict"] = judge(takeaway, meta["reviewer"])
        # the brief changed; keep the cache key honest so build doesn't re-roll
        meta["sha"] = hashlib.sha256((d / "source.svg").read_bytes() +
                                     (d / "brief.json").read_bytes()).hexdigest()[:16]
        (d / "meta.json").write_text(json.dumps(meta, indent=1))
        print(f"{d.name}: {meta['verdict']}")
    elif cmd == "preview":
        # lint + render only — iterate on layout without spending a review
        d = Path(rest[0]).resolve()
        if (d / "chart.json").exists():
            chart(d)
        errs = lint(d)
        render(d / "source.svg", d / "teach.png")
        print("\n".join(errs) or f"lint ok — rendered {d / 'teach.png'}")
        sys.exit(1 if errs else 0)
    elif cmd == "lint":
        errs = lint(Path(rest[0]).resolve())
        print("\n".join(errs) or "lint ok")
        sys.exit(1 if errs else 0)
    else:
        print(__doc__)
