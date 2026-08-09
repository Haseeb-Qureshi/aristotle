#!/usr/bin/env python3
"""Aristotle schedule.py — the deterministic core.

Owns everything the teaching agent must never improvise: date arithmetic,
the mastery transition table, session dispatch, the review queue, integrity
checks, and crash recovery. The agent's entire write surface is grade lines
in a session log; this script does the rest.

Stdlib only (python3 >= 3.9). Copied into every course directory at
bootstrap so a resurrected course is self-contained.

The two verbs a session uses:
  begin                       recover + lock + check + dispatch + queue
  close <logfile>             grades + plan.md + git + unlock, atomically

The rest are for lifecycle and repair:
  check                       integrity pass (loud failure)
  queue                       regenerate review-queue.md
  report                      progress summary (for the AGENT, never shown)
  recover                     sentinel three-way recovery
  seed <id> <band>            placement calibration (idempotent)
  set-verify <id> <mech>      adjudication verdicts
  reprune <ids>               shrink the course coherently
  commit-grades <logfile>     apply grades only (close does this for you)

State ownership: knowledge-state.md and plan.md's header are written ONLY
by this script. Mastery is DERIVED from interval and fails, never stored —
there is no band to inflate.

Test hooks: ARISTOTLE_TODAY (YYYY-MM-DD) pins "today"; ARISTOTLE_NOW pins
the recovery clock.
"""

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

LADDER = [1, 3, 7, 16, 35, 90, 180]
STATUSES = {"untaught", "active", "plateaued", "dropped"}
VERIFIES = {"quiz", "use", "none"}
RESULTS = {"taught", "pass", "fail", "rubric-pass", "rubric-fail"}
RECORD_FIELDS = ["id", "verify", "status", "last", "next",
                 "interval", "fails", "note"]
INT_FIELDS = {"interval", "fails"}
COURSE_STATUSES = {"active", "paused", "maintenance", "closed"}
UNIT_STATUSES = {"untouched", "in-progress", "taught"}
SENTINEL = ".session-inprogress"
QUEUE_CAP = 5
TEACHING_CAP = 3          # cap when the session also teaches new material
PLATEAU_FAILS = 3
STALE_HOURS = 2           # a sentinel younger than this means a session is LIVE
DORMANT_DAYS = 14
MIN_CONSOLIDATION = 1     # reserved at the end for the terminal synthesis
ASKED_RECENCY = 3         # how many logs back `begin` replays asked items
DATE_RE = re.compile(r"^\d{4}-\d\d-\d\d$")


class FormatError(Exception):
    """A file or grade line does not match its grammar."""


class IntegrityError(Exception):
    """Cross-file state disagrees, or an operation would corrupt it."""


def _read(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _write(path: Path, text: str):
    """Atomic: the reader never sees a half-written file."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


# --------------------------------------------------------------- clock

def _today(course: Path) -> dt.date:
    env = os.environ.get("ARISTOTLE_TODAY")
    if env:
        return dt.date.fromisoformat(env)
    tz = _map_header(course).get("timezone")
    if tz:
        try:
            from zoneinfo import ZoneInfo
            return dt.datetime.now(ZoneInfo(tz)).date()
        except Exception:
            pass
    return dt.date.today()


def _now() -> dt.datetime:
    """Wall clock, naive local. Only ever compared against a file mtime
    from the same machine, so no timezone can enter the comparison."""
    env = os.environ.get("ARISTOTLE_NOW")
    if env:
        return dt.datetime.fromisoformat(env)
    return dt.datetime.now()


# ------------------------------------------------- knowledge-state file

STATE_FILE = "knowledge-state.md"
# legacy "elenchus:state" is still accepted on read; we always write the new one
HEADER_RE = re.compile(r"<!-- (?:aristotle|elenchus):state\n(.*?)\n-->\n?", re.S)


def parse_state(text: str):
    """Return (meta, records). Loud on any format or VALUE violation."""
    m = HEADER_RE.search(text)
    if not m:
        raise FormatError("knowledge-state.md missing aristotle:state header")
    meta = {"committed-sessions": [], "repair-pending": "none"}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("format:"):
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key == "committed-sessions":
            meta[key] = [t for t in re.split(r"[,\s]+", val) if t]
        elif key == "repair-pending":
            meta[key] = val or "none"
        else:
            raise FormatError(f"unknown state-header field: {key}")

    records = {}
    body = _strip_comments(text[m.end():])
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if not line.startswith("- "):
            raise FormatError(f"non-record line in state body: {raw!r}"
                              " (records are one physical line, '- ' led)")
        rec = {}
        for part in line[2:].split(" | "):
            key, sep, val = part.partition(": ")
            if not sep and not part.endswith(":"):
                raise FormatError(f"unparseable field {part!r} in {raw!r}")
            key = key.rstrip(":").strip()
            if key not in RECORD_FIELDS:
                raise FormatError(f"unknown record field {key!r} in {raw!r}")
            rec[key] = val.strip()
        missing = [f for f in RECORD_FIELDS if f not in rec]
        if missing:
            raise FormatError(f"record {rec.get('id')!r} missing {missing}")
        # value validation: a wrong value here is silent corruption later
        if rec["verify"] not in VERIFIES:
            raise FormatError(f"{rec['id']}: verify={rec['verify']!r} not in "
                              f"{sorted(VERIFIES)}")
        if rec["status"] not in STATUSES:
            raise FormatError(f"{rec['id']}: status={rec['status']!r} not in "
                              f"{sorted(STATUSES)}")
        for f in ("last", "next"):
            if rec[f] != "-" and not DATE_RE.match(rec[f]):
                raise FormatError(
                    f"{rec['id']}: {f}={rec[f]!r} is not YYYY-MM-DD or '-'")
        for f in INT_FIELDS:
            if not re.fullmatch(r"\d+", rec[f]):
                raise FormatError(
                    f"{rec['id']}: {f}={rec[f]!r} is not a non-negative int")
            rec[f] = int(rec[f])
        if rec["id"] in records:
            raise FormatError(f"duplicate concept id: {rec['id']}")
        records[rec["id"]] = rec
    return meta, records


def serialize_state(meta, records) -> str:
    head = ["<!-- aristotle:state",
            "committed-sessions: " + ",".join(meta["committed-sessions"]),
            f"repair-pending: {meta['repair-pending']}",
            "-->",
            "<!-- Written ONLY by scripts/schedule.py. Never hand-edit: the",
            "     agent's write surface is grade lines in a session log.",
            "     Mastery is derived from interval/fails, never stored. -->"]
    lines = []
    for rec in records.values():
        rec = dict(rec)
        # '|' is the field delimiter; it may never appear inside a value
        rec["note"] = str(rec["note"]).replace("|", "/")
        lines.append("- " + " | ".join(
            f"{f}: {rec[f]}" for f in RECORD_FIELDS))
    return "\n".join(head) + "\n" + "\n".join(lines) + "\n"


def load_state(course: Path):
    return parse_state(_read(Path(course) / STATE_FILE))


def save_state(course: Path, meta, records):
    """Single atomic write: grades and flags land together or not at all."""
    _write(Path(course) / STATE_FILE, serialize_state(meta, records))


def band(rec) -> str:
    """The DERIVED mastery band. Display only — nothing schedules on it."""
    if rec["status"] == "dropped":
        return "dropped"
    if rec["status"] == "plateaued":
        return "stuck"
    if rec["status"] == "untaught":
        return "untaught"
    if rec["interval"] >= 35 and rec["fails"] == 0:
        return "solid"
    if rec["interval"] >= 7:
        return "retrievable"
    return "exposed"


# ----------------------------------------------------------- domain map

CONCEPT_RE = re.compile(r"^### (\S+)\s*$", re.M)
ERRATUM_RE = re.compile(
    r"^\s*[-*]?\s*erratum\b[^:]*:\s*(remove-edge|add-edge)\s+(\S+)\s*->\s*"
    r"(\S+)", re.M | re.I)


def _map_header(course: Path) -> dict:
    text = _read(Path(course) / "domain-map.md")
    head = text.split("###", 1)[0]
    out = {}
    for line in _strip_comments(head).splitlines():
        k, sep, v = line.partition(":")
        if sep and " " not in k.strip():
            out[k.strip()] = v.strip()
    return out


def parse_map(course: Path):
    """Return {id: {prereqs, verify, threshold, misconceptions}} with errata
    already merged over the frozen graph (ids stay immutable; edges heal)."""
    text = _read(Path(course) / "domain-map.md")
    blocks = CONCEPT_RE.split(text)[1:]  # id, body, id, body ...
    concepts = {}
    for cid, body in zip(blocks[0::2], blocks[1::2]):
        # a concept's body ends at the next '## ' section (Sources,
        # Controversies, Errata) — otherwise their lines leak into it
        body = _strip_comments(re.split(r"^## ", body, 1, flags=re.M)[0])
        c = {"prereqs": [], "verify": "quiz", "threshold": "no",
             "misconceptions": []}
        in_misc = False
        for line in body.splitlines():
            indented = line.startswith((" ", "\t"))
            if line.strip() == "misconceptions:":
                in_misc = True
                continue
            if in_misc and indented and ":" in line:
                c["misconceptions"].append(
                    line.strip().split(":", 1)[0].strip())
                continue
            if line.strip() and not indented:
                in_misc = False
            k, sep, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k == "prereqs":
                c["prereqs"] = [p for p in
                                re.split(r"[,\s]+", v.strip("[]")) if p]
            elif k in ("verify", "threshold"):
                c[k] = v
        concepts[cid] = c
    for op, a, b in ERRATUM_RE.findall(text):
        if b in concepts:
            pre = concepts[b]["prereqs"]
            if op.lower() == "remove-edge" and a in pre:
                pre.remove(a)
            if op.lower() == "add-edge" and a not in pre:
                pre.append(a)
    return concepts


# ----------------------------------------------------------------- plan

UNIT_RE = re.compile(r"^Unit (\d+):\s*(.*)$")
# a '## Review: <title>' block occupies sessions like a unit but teaches
# nothing and owns no assets — rolling mixed review between units
REVIEW_RE = re.compile(r"^Review(?:\s+\d+)?:\s*(.*)$", re.I)
PLAN_HEADER_FIELDS = ["course-status", "next-session", "cadence",
                      "sessions-done", "last-attended", "re-entry-pending"]


def parse_plan(course: Path):
    """Return (header, units). Units carry their DECLARED number and their
    derived [start, end] session range."""
    text = _strip_comments(_read(Path(course) / "plan.md"))
    header = {}
    for line in text.split("\n## ", 1)[0].splitlines():
        k, sep, v = line.partition(":")
        if sep and k.strip() in PLAN_HEADER_FIELDS:
            header[k.strip()] = v.strip()
    missing = [f for f in PLAN_HEADER_FIELDS if f not in header]
    if missing:
        raise FormatError(f"plan.md header missing {missing}")
    if header["course-status"] not in COURSE_STATUSES:
        raise FormatError(f"course-status={header['course-status']!r} not in "
                          f"{sorted(COURSE_STATUSES)}")
    if not re.fullmatch(r"\d+/\d+", header["next-session"]):
        raise FormatError(
            f"next-session={header['next-session']!r} must be N/M")
    if header["re-entry-pending"] not in ("yes", "no"):
        raise FormatError("re-entry-pending must be yes|no")
    if header["last-attended"] != "-" \
            and not DATE_RE.match(header["last-attended"]):
        raise FormatError("last-attended must be YYYY-MM-DD or '-'")
    for f in ("cadence", "sessions-done"):
        if not re.fullmatch(r"\d+", header[f]):
            raise FormatError(f"{f}={header[f]!r} is not a non-negative int")

    units, cursor = [], 1
    for chunk in text.split("\n## ")[1:]:
        head = chunk.splitlines()[0].strip()
        m = UNIT_RE.match(head)
        rm = REVIEW_RE.match(head) if not m else None
        if not m and not rm:
            continue          # a non-unit '## ' section is not a unit
        if rm:
            unit = {"num": None, "review": True,
                    "title": rm.group(1).strip() or "mixed review",
                    "concepts": [], "keystones": [], "status": "-",
                    "sessions": 1, "artifact": ""}
            for line in chunk.splitlines()[1:]:
                k, sep, v = line.partition(":")
                if k.strip() == "sessions" and v.strip().isdigit():
                    unit["sessions"] = int(v.strip())
        else:
            unit = {"num": int(m.group(1)), "title": m.group(2).strip(),
                    "concepts": [], "keystones": [], "status": "untouched",
                    "sessions": 0, "artifact": ""}
            for line in chunk.splitlines()[1:]:
                k, sep, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if k in ("concepts", "keystones"):
                    unit[k] = [p for p in
                               re.split(r"[,\s]+", v.strip("[]")) if p]
                elif k == "status":
                    unit["status"] = v
                elif k == "sessions":
                    unit["sessions"] = int(v) if v.isdigit() else 0
                elif k == "artifact-milestone":
                    unit["artifact"] = v
            if unit["status"] not in UNIT_STATUSES:
                raise FormatError(f"unit {unit['num']}: status="
                                  f"{unit['status']!r} not in "
                                  f"{sorted(UNIT_STATUSES)}")
        unit["start"] = cursor
        unit["end"] = cursor + unit["sessions"] - 1
        cursor = unit["end"] + 1
        units.append(unit)
    return header, units


def course_size(header) -> int:
    return int(header["next-session"].split("/")[1])


def session_index(header) -> int:
    return int(header["next-session"].split("/")[0])


def write_plan_header(course: Path, updates: dict):
    """Rewrite header fields in place, preserving everything else."""
    path = Path(course) / "plan.md"
    text = _read(path)
    for key, val in updates.items():
        pat = re.compile(rf"^{re.escape(key)}:.*$", re.M)
        if not pat.search(text):
            raise IntegrityError(f"plan.md has no {key!r} line to update")
        text = pat.sub(f"{key}: {val}", text, count=1)
    _write(path, text)


def write_unit_status(course: Path, num: int, status: str):
    path = Path(course) / "plan.md"
    text = _read(path)
    chunks = text.split("\n## ")
    for i, chunk in enumerate(chunks[1:], start=1):
        m = UNIT_RE.match(chunk.splitlines()[0].strip())
        if m and int(m.group(1)) == num:
            chunks[i] = re.sub(r"^status:.*$", f"status: {status}",
                               chunk, count=1, flags=re.M)
    _write(path, "\n## ".join(chunks))


# ---------------------------------------------------------- grade lines

SESSION_TOKEN_RE = re.compile(r"^\d+(r\d*)?$")
GRADE_RE = re.compile(
    r"^- grade:\s*(\S+)\s*\|\s*result:\s*(\S+)\s*\|\s*note:\s*(.*)$")
LOOKS_LIKE_GRADE = re.compile(r"grade\s*\**\s*:", re.I)


def valid_session_token(tok: str) -> bool:
    return bool(SESSION_TOKEN_RE.match(tok))


def parse_log_grades(text: str):
    """Return (session_token, grades). Any line that LOOKS like a grade
    but doesn't parse is a loud error — silence is how mastery dies.

    If the log has a '## grades' section, ONLY that section is scanned:
    an example grade line quoted in prose must not mutate mastery."""
    session = None
    for line in text.splitlines():
        if line.strip().startswith("session:"):
            session = line.split(":", 1)[1].strip()
            break
    if session is None:
        raise FormatError("log has no 'session:' line")
    if not valid_session_token(session):
        raise FormatError(f"bad session token {session!r} "
                          "(grammar: digits, optional r-suffix e.g. 17r)")

    scope = text
    m = re.search(r"^##+\s*grades\s*$", text, re.M | re.I)
    if m:
        rest = text[m.end():]
        nxt = re.search(r"^##+\s", rest, re.M)
        scope = rest[:nxt.start()] if nxt else rest

    grades, seen = [], {}
    for line in scope.splitlines():
        line = line.strip()
        # catch the near-misses an LLM writes (en-dash bullet, bold label)
        # so they fail loudly instead of vanishing
        if not LOOKS_LIKE_GRADE.match(line.lstrip("-–—*• \t")):
            continue
        m = GRADE_RE.match(line)
        if not m:
            raise FormatError(
                f"malformed grade line: {line!r}\n"
                "  grammar: - grade: <id> | result: <r> | note: <text>")
        cid, result, note = m.groups()
        if result not in RESULTS:
            raise FormatError(
                f"invalid result {result!r} (allowed: {sorted(RESULTS)})")
        if cid in seen:
            raise FormatError(
                f"two grade lines for {cid!r} in one log "
                f"({seen[cid]!r} then {result!r}) — write ONE verdict per "
                "concept per session; a same-session re-probe does not "
                "upgrade the original result")
        seen[cid] = result
        grades.append({"id": cid, "result": result, "note": note.strip()})
    return session, grades


# ----------------------------------------------------- transition table

def ladder_up(iv: int) -> int:
    for step in LADDER:
        if step > iv:
            return step
    return LADDER[-1]


def ladder_down(iv: int) -> int:
    below = [s for s in LADDER if s < iv]
    return below[-1] if below else LADDER[0]


def _apply_grade(rec, grade, meta, today: dt.date, next_unit_needs):
    """The transition table. One grade, one record, pure and total."""
    result = grade["result"]
    iso = today.isoformat()
    was_repair = meta["repair-pending"] == rec["id"]

    if result == "taught":
        if rec["status"] in ("untaught", "plateaued"):
            rec["status"] = "active"
        rec["fails"] = 0
        rec["interval"] = 1
        rec["last"], rec["next"] = iso, (today + dt.timedelta(1)).isoformat()

    elif result in ("pass", "rubric-pass"):
        # a pass is evidence of contact, whatever the row claimed before
        if rec["status"] in ("untaught", "plateaued"):
            rec["status"] = "active"
        rec["fails"] = 0
        rec["interval"] = ladder_up(rec["interval"])
        rec["last"], rec["next"] = iso, \
            (today + dt.timedelta(rec["interval"])).isoformat()

    elif result in ("fail", "rubric-fail"):
        if rec["status"] == "untaught":
            rec["status"] = "active"
        # step back one rung, never to zero: a lapse is not amnesia
        rec["interval"] = ladder_down(rec["interval"])
        rec["fails"] += 1
        if rec["fails"] >= PLATEAU_FAILS:
            rec["status"] = "plateaued"
        rec["last"], rec["next"] = iso, \
            (today + dt.timedelta(rec["interval"])).isoformat()
        # only a failed hard prerequisite of the NEXT unit triggers repair
        if result == "rubric-fail" and rec["id"] in next_unit_needs \
                and not was_repair:
            meta["repair-pending"] = rec["id"]
            return

    if was_repair:
        # the repair session happened; the course moves on either way
        meta["repair-pending"] = "none"
        if result in ("fail", "rubric-fail"):
            rec["status"] = "plateaued"


def _next_unit_prereq_ids(course: Path):
    """Concept ids that the next untouched unit hard-depends on."""
    concepts = parse_map(course)
    _, units = parse_plan(course)
    for unit in units:
        if unit.get("review"):
            continue          # a review block must not mask the real unit
        if unit["status"] == "untouched":
            needed = set()
            for cid in unit["concepts"]:
                needed.update(concepts.get(cid, {}).get("prereqs", []))
            return needed
    return set()


def cmd_commit_grades(course: Path, logfile: Path):
    course = Path(course)
    session, grades = parse_log_grades(_read(Path(logfile)))
    meta, records = load_state(course)
    if session in meta["committed-sessions"]:
        return "noop"  # replay after crash/redo: exact-string guard
    unknown = [g["id"] for g in grades if g["id"] not in records]
    if unknown:
        raise IntegrityError(
            f"grade for unknown concept id(s) {unknown} — refusing to "
            "apply ANY grade from this log (all-or-nothing)")
    needs = _next_unit_prereq_ids(course)
    today = _today(course)
    for g in grades:
        _apply_grade(records[g["id"]], g, meta, today, needs)
        if g["note"]:
            records[g["id"]]["note"] = g["note"]
    meta["committed-sessions"].append(session)
    save_state(course, meta, records)  # one atomic write: grades + guard
    return "applied"


# ------------------------------------------------------------------ queue

def build_queue(course: Path, cap=QUEUE_CAP, terminal=False):
    course = Path(course)
    meta, records = load_state(course)
    today = _today(course).isoformat()
    live = [r for r in records.values()
            if r["status"] == "active" and r["verify"] != "none"]
    if terminal:
        # consolidation: ignore due dates, surface the least-evidenced first
        live.sort(key=lambda r: (-r["fails"], r["interval"]))
        return [r["id"] for r in live[:cap]]
    due = [r for r in live if r["next"] not in ("-", "") and r["next"] <= today]
    # oldest-first, but never let the backlog crowd out the material the
    # current unit is actually about
    due.sort(key=lambda r: (r["interval"], r["next"]))
    return [r["id"] for r in due[:cap]]


def cmd_queue(course: Path, cap=QUEUE_CAP, terminal=False):
    course = Path(course)
    ids = build_queue(course, cap=cap, terminal=terminal)
    meta, records = load_state(course)
    today = _today(course).isoformat()
    total_due = sum(1 for r in records.values()
                    if r["status"] == "active" and r["verify"] != "none"
                    and r["next"] not in ("-", "") and r["next"] <= today)
    rolled = max(0, total_due - len(ids))
    lines = ["<!-- GENERATED by schedule.py — never hand-edit -->",
             f"<!-- date: {today} | rolled-forward: {rolled} -->"]
    lines += [f"- {i}" for i in ids]
    _write(course / "review-queue.md", "\n".join(lines) + "\n")
    return ids


# ------------------------------------------------- seed / verify / prune

# placement evidence must reach the SCHEDULE, not just a display band
SEED_INTERVAL = {"none": 1, "exposed": 1, "retrievable": 7}


def cmd_seed(course: Path, cid: str, evidence: str):
    course = Path(course)
    if evidence not in SEED_INTERVAL:
        raise FormatError(f"unknown evidence level {evidence!r} "
                          f"(one of {sorted(SEED_INTERVAL)})")
    concepts = parse_map(course)
    if cid not in concepts:
        raise IntegrityError(f"seed: {cid!r} is not in the domain map")
    meta, records = load_state(course)
    today = _today(course)
    iv = SEED_INTERVAL[evidence]
    records[cid] = {   # upsert: rerunning session 1 cannot duplicate rows
        "id": cid, "verify": concepts[cid]["verify"],
        "status": "active" if evidence != "none" else "untaught",
        "last": today.isoformat(),
        "next": (today + dt.timedelta(iv)).isoformat(),
        "interval": iv, "fails": 0, "note": f"placement: {evidence}",
    }
    save_state(course, meta, records)


def cmd_set_verify(course: Path, cid: str, mech: str):
    course = Path(course)
    if mech not in VERIFIES:
        raise FormatError(f"unknown verify mechanism {mech!r}")
    meta, records = load_state(course)
    if cid not in records:
        raise IntegrityError(f"set-verify: unknown concept {cid!r}")
    records[cid]["verify"] = mech
    if mech == "none":
        # adjudicated away: stop reporting it as stuck
        records[cid]["status"] = "dropped"
    save_state(course, meta, records)


def cmd_reprune(course: Path, drop):
    """Shrink the course coherently: state + plan in one operation.
    Refuses to orphan a kept concept's prerequisite, or to drop a
    threshold concept."""
    course = Path(course)
    concepts = parse_map(course)
    meta, records = load_state(course)
    dropset = set(drop)
    for cid in dropset:
        if cid not in records:
            raise IntegrityError(f"reprune: unknown concept {cid!r}")
        if concepts.get(cid, {}).get("threshold") == "yes":
            raise IntegrityError(
                f"cannot drop {cid!r}: it is a threshold concept — the "
                "course does not mean the same thing without it")
    kept = {cid for cid, r in records.items()
            if cid not in dropset and r["status"] != "dropped"}
    for cid in kept:
        broken = dropset & set(concepts.get(cid, {}).get("prereqs", []))
        if broken:
            raise IntegrityError(
                f"cannot drop {sorted(broken)}: prerequisite(s) of kept "
                f"concept {cid!r}")
    for cid in dropset:
        records[cid]["status"] = "dropped"
    if meta["repair-pending"] in dropset:
        meta["repair-pending"] = "none"
    save_state(course, meta, records)
    # plan.md: remove dropped ids from concepts/keystones lists in place
    path = course / "plan.md"
    text = _read(path)

    def strip_ids(m):
        ids = [p for p in re.split(r"[,\s]+", m.group(2).strip("[]"))
               if p and p not in dropset]
        return f"{m.group(1)}: [{', '.join(ids)}]"
    text = re.sub(r"^(concepts|keystones):\s*(\[?[^\]\n]*\]?)",
                  strip_ids, text, flags=re.M)
    _write(path, text)


# ----------------------------------------------------------------- assets

MIN_INTERLEAVED = 2
MID_RE = re.compile(r"^M\d+$")


def parse_assets(text: str):
    """Parse an assets/unit-NN.md file into checkable structure.

    Grammar (see templates/assets-unit.md). Indented continuation lines
    append to the previous item, so long values may wrap:
      ## concept: <id>
      - quiz: <question> | a: <answer> | distractor: <Mid or free text>
      - example: worked | <text>
      - apply: <prompt>
      ## rubric: <keystone-id>
      - claim: <required claim>
      - avoid: <Mid>
      ## interleaved
      - problem: <text> | concepts: a, b
    """
    out = {"concepts": {}, "rubrics": {}, "interleaved": []}
    section = kind = None
    items = []          # flat list of (dict, key) for continuation appends
    last = None
    for raw in _strip_comments(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            head = line[3:].strip()
            key, _, val = head.partition(":")
            key, val = key.strip(), val.strip()
            if key == "concept":
                section, kind = val, "concept"
                out["concepts"].setdefault(
                    val, {"quiz": [], "apply": [], "example": {}})
            elif key == "rubric":
                section, kind = val, "rubric"
                out["rubrics"].setdefault(val, {"claims": [], "avoid": []})
            elif key == "interleaved":
                section, kind = None, "interleaved"
            else:
                raise FormatError(
                    f"unknown asset section: {head!r} "
                    "(sections are 'concept:', 'rubric:', 'interleaved')")
            last = None
            continue
        if not line.startswith("- "):
            if last is not None and raw.startswith((" ", "\t")):
                holder, hkey = last
                holder[hkey] = (holder[hkey] + " " + line).strip()
            continue
        field, _, rest = line[2:].partition(":")
        field, rest = field.strip(), rest.strip()
        last = None
        if kind == "concept":
            c = out["concepts"][section]
            if field == "quiz":
                q, _, tail = rest.partition(" | a:")
                if not tail:
                    raise FormatError(
                        f"quiz item for {section!r} has no ' | a:' answer")
                ans, _, dis = tail.partition(" | distractor:")
                item = {"q": q.strip(), "a": ans.strip(),
                        "distractor": dis.strip() or None}
                c["quiz"].append(item)
                last = (item, "a")
            elif field == "example":
                variant, _, body = rest.partition(" | ")
                c["example"][variant.strip()] = body.strip()
                last = (c["example"], variant.strip())
            elif field == "apply":
                c["apply"].append(rest)
                last = (c["apply"], len(c["apply"]) - 1)
            else:
                # a typo'd field would otherwise vanish without a trace
                raise FormatError(
                    f"unknown field {field!r} under '## concept: {section}' "
                    "(quiz, example, apply)")
        elif kind == "rubric":
            r = out["rubrics"][section]
            if field == "claim":
                r["claims"].append(rest)
                last = (r["claims"], len(r["claims"]) - 1)
            elif field == "avoid":
                r["avoid"].append(rest)
            else:
                raise FormatError(
                    f"unknown field {field!r} under '## rubric: {section}' "
                    "(claim, avoid)")
        elif kind == "interleaved":
            if field != "problem":
                raise FormatError(
                    f"unknown field {field!r} under '## interleaved' "
                    "(problem)")
            body, _, cons = rest.partition(" | concepts:")
            item = {"problem": body.strip(),
                    "concepts": [c for c in re.split(r"[,\s]+", cons) if c]}
            out["interleaved"].append(item)
            last = (item, "problem")
    return out


def validate_assets(unit, assets, concepts, where="", first_unit=False):
    """Quality gate. Every rule here is BOTH checkable and non-negotiable:
    it rejects empty and placeholder work, and it never demands a shape
    that good teaching material cannot take."""
    errs = []

    def blank(s):
        return not s or not s.strip() or s.strip().lower() in (
            "todo", "tbd", "...", "-", "n/a", "xxx", "placeholder")

    for cid in unit["concepts"]:
        spec = concepts.get(cid)
        if not spec:
            continue
        got = assets["concepts"].get(cid)
        if not got:
            errs.append(f"no '## concept: {cid}' block")
            continue
        if spec["verify"] == "quiz":
            live = [q for q in got["quiz"]
                    if not blank(q["q"]) and not blank(q["a"])]
            if not live:
                errs.append(f"{cid}: needs a quiz item with a real question "
                            "and a real answer key")
            for item in got["quiz"]:
                d = item["distractor"]
                # an Mn-shaped distractor must resolve; free text is fine
                if d and MID_RE.match(d) and d not in spec["misconceptions"]:
                    errs.append(
                        f"{cid}: distractor {d!r} is not a misconception id "
                        f"in the map ({spec['misconceptions'] or 'none'})")
        if spec["verify"] == "use":
            if not [a for a in got["apply"] if not blank(a)]:
                errs.append(f"{cid}: verify:use needs a real 'apply:' prompt")

    for key in unit["keystones"]:
        rub = assets["rubrics"].get(key)
        if not rub:
            errs.append(f"keystone {key!r} has no '## rubric: {key}' block")
            continue
        if not [c for c in rub["claims"] if not blank(c)]:
            errs.append(f"rubric {key!r}: needs a real 'claim:' line")
        known = concepts.get(key, {}).get("misconceptions", [])
        for mid in rub["avoid"]:
            if MID_RE.match(mid) and mid not in known:
                errs.append(
                    f"rubric {key!r}: avoid {mid!r} not a map misconception "
                    f"({known or 'none declared'})")

    need = 1 if first_unit else MIN_INTERLEAVED
    live = [p for p in assets["interleaved"]
            if not blank(p["problem"]) and p["concepts"]]
    if len(live) < need:
        errs.append(
            f"needs >={need} interleaved problem(s) with real text and a "
            f"'| concepts:' list, found {len(live)}")
    for p in live:
        unknown = [c for c in p["concepts"] if c not in concepts]
        if unknown:
            errs.append(f"interleaved problem names unknown concept(s) "
                        f"{unknown}")
    if errs:
        raise IntegrityError(f"{where}: " + "; ".join(errs))


def assets_path(course: Path, num: int) -> Path:
    return Path(course) / "assets" / f"unit-{num:02d}.md"


# ------------------------------------------------------------------ check

def cmd_check(course: Path):
    course = Path(course)
    concepts = parse_map(course)          # errata already merged
    meta, records = load_state(course)    # values validated on load
    header, units = parse_plan(course)

    # prereq edges must point at real concepts, and the graph must be a DAG
    for cid, c in concepts.items():
        for p in c["prereqs"]:
            if p not in concepts:
                raise IntegrityError(f"{cid}: unknown prereq {p!r}")
    seen, done = set(), set()

    def visit(cid, path):
        if cid in done:
            return
        if cid in seen:
            raise IntegrityError(
                f"prereq cycle: {' -> '.join(path + [cid])}")
        seen.add(cid)
        for p in concepts[cid]["prereqs"]:
            visit(p, path + [cid])
        done.add(cid)
    for cid in concepts:
        visit(cid, [])

    # cross-file id agreement
    missing = set(concepts) - set(records)
    if missing:
        raise IntegrityError(
            f"map concepts with no knowledge-state row: {sorted(missing)}")
    orphans = set(records) - set(concepts)
    if orphans:
        raise IntegrityError(
            f"knowledge-state rows not in map: {sorted(orphans)}")
    for cid, rec in records.items():
        # set-verify none is the one legal divergence; it drops the concept
        if rec["verify"] != concepts[cid]["verify"] \
                and rec["status"] != "dropped":
            raise IntegrityError(
                f"{cid}: verify disagrees with the map "
                f"({rec['verify']!r} vs {concepts[cid]['verify']!r})")
    for unit in units:
        for cid in unit["concepts"] + unit["keystones"]:
            if cid not in concepts:
                raise IntegrityError(
                    f"plan references unknown concept {cid!r} in unit "
                    f"{unit['num']}")
        for cid in unit["keystones"]:
            if cid not in unit["concepts"]:
                raise IntegrityError(
                    f"unit {unit['num']}: keystone {cid!r} is not one of "
                    "the unit's own concepts")

    # the course must FIT: one session per concept, plus a teach-back,
    # plus the terminal synthesis session at the end
    size = course_size(header)
    for unit in units:
        if unit.get("review"):
            if unit["sessions"] < 1:
                raise IntegrityError("a review block needs >=1 session")
            continue
        floor = len(unit["concepts"]) + 1
        if unit["sessions"] < floor:
            raise IntegrityError(
                f"unit {unit['num']} has {len(unit['concepts'])} concepts "
                f"but only {unit['sessions']} sessions — needs >={floor} "
                "(one per concept at <=1 new concept/session, plus the "
                "teach-back)")
    total = sum(u["sessions"] for u in units)
    if total > size - MIN_CONSOLIDATION:
        raise IntegrityError(
            f"units total {total} sessions of a {size}-session course; "
            f"leave >={MIN_CONSOLIDATION} free at the end for the terminal "
            f"synthesis session (max {size - MIN_CONSOLIDATION})")

    # assets: a started unit must HAVE them; any that exist must be good
    for unit in units:
        if unit.get("review"):
            continue          # a review block owns no assets
        path = assets_path(course, unit["num"])
        if not path.exists():
            if unit["status"] != "untouched":
                raise IntegrityError(
                    f"unit {unit['num']} is {unit['status']!r} but "
                    f"{path.name} is missing")
            continue
        validate_assets(unit, parse_assets(_read(path)), concepts,
                        where=path.name, first_unit=(unit["num"] == units[0]["num"]))
    return "ok"


# --------------------------------------------------------------- dispatch

def dispatch(course: Path):
    """Decide the session type. Deterministic from plan.md + state, so two
    agents never disagree about what session this is."""
    course = Path(course)
    header, units = parse_plan(course)
    meta, records = load_state(course)
    idx, size = session_index(header), course_size(header)
    out = {"index": idx, "size": size, "unit": None, "author": None,
           "cap": TEACHING_CAP, "terminal": False}

    if header["course-status"] != "active":
        out["type"] = "lifecycle"
        out["why"] = f"course-status is {header['course-status']}"
        return out
    if idx > size:
        out["type"] = "graduation"
        out["why"] = "the session counter is exhausted"
        return out
    if idx == 1:
        out["type"] = "placement"
        out["why"] = "first session"
        return out

    last = header["last-attended"]
    if last != "-":
        gap = (_today(course) - dt.date.fromisoformat(last)).days
        if gap >= DORMANT_DAYS:
            out["type"] = "dormant"
            out["why"] = f"{gap} days since the last session"
            return out
    if header["re-entry-pending"] == "yes":
        out["type"], out["cap"] = "re-entry", QUEUE_CAP
        out["why"] = "returning after a gap"
        return out
    if meta["repair-pending"] != "none":
        out["type"] = "repair"
        out["why"] = f"repair owed on {meta['repair-pending']}"
        out["concept"] = meta["repair-pending"]
        return out

    here = next((u for u in units if u["start"] <= idx <= u["end"]), None)
    if here is None:
        out["type"], out["cap"], out["terminal"] = "consolidation", QUEUE_CAP, True
        out["why"] = "every unit is taught; synthesis and transfer, not recall"
        return out
    if here.get("review"):
        out["type"], out["cap"] = "review", QUEUE_CAP
        out["why"] = "mixed review block — no new material"
        nxt = next((u for u in units if u.get("num") is not None
                    and u["start"] > here["end"]
                    and u["status"] == "untouched"), None)
        if nxt and not assets_path(course, nxt["num"]).exists():
            out["author"] = assets_path(course, nxt["num"]).name
        return out

    out["unit"] = here
    if not assets_path(course, here["num"]).exists():
        out["author"] = assets_path(course, here["num"]).name
    elif idx == here["end"]:
        nxt = next((u for u in units if u.get("num") is not None
                    and u["num"] > here["num"]), None)
        if nxt and not assets_path(course, nxt["num"]).exists():
            out["author"] = assets_path(course, nxt["num"]).name
    if idx == here["end"]:
        out["type"], out["cap"] = "teach-back", QUEUE_CAP
        out["why"] = f"last session of unit {here['num']}"
    else:
        out["type"] = "standard"
        out["why"] = f"session {idx - here['start'] + 1} of unit {here['num']}"
    return out


# ------------------------------------------------------------------ report

def cmd_report(course: Path):
    course = Path(course)
    meta, records = load_state(course)
    header, units = parse_plan(course)
    today = _today(course).isoformat()
    live = [r for r in records.values() if r["status"] != "dropped"]
    due = [r["id"] for r in live
           if r["status"] == "active" and r["verify"] != "none"
           and r["next"] not in ("-", "") and r["next"] <= today]
    stuck = [r["id"] for r in live if r["status"] == "plateaued"]
    counts = {}
    for r in live:
        counts[band(r)] = counts.get(band(r), 0) + 1
    lines = [
        f"session {header['next-session']} | cadence {header['cadence']}/wk "
        f"| attended {header['sessions-done']} | last {header['last-attended']}",
        "concepts: " + " ".join(f"{b}={n}" for b, n in sorted(counts.items())),
        f"due today: {len(due)} ({', '.join(due) or '-'})",
        f"stuck (needs your call): {len(stuck)} ({', '.join(stuck) or '-'})",
        f"repair-pending: {meta['repair-pending']}",
        "units: " + ", ".join(
            f"{'review' if u.get('review') else u['num']}:{u['status']}"
            for u in units),
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- git

def _git(course, *args, check=True):
    return subprocess.run(
        ["git", "-c", "user.name=aristotle", "-c",
         "user.email=aristotle@localhost", *args],
        cwd=course, check=check, capture_output=True, text=True)


def _is_repo(course) -> bool:
    return _git(course, "rev-parse", "--git-dir", check=False).returncode == 0


def _ensure_repo(course: Path) -> bool:
    """A course directory must be its own history. Returns True if created."""
    if _is_repo(course):
        return False
    _git(course, "init", "-q")
    gi = Path(course) / ".gitignore"
    if not gi.exists():
        _write(gi, f"{SENTINEL}\n*.tmp\n__pycache__/\n")
    _git(course, "add", "-A", "--", ".")
    _git(course, "commit", "-q", "-m", "aristotle: course directory")
    return True


def _dirty(course) -> bool:
    r = _git(course, "status", "--porcelain", "--", ".", check=False)
    return bool(r.stdout.strip())


def _commit(course, message):
    """Scoped to the course subtree, so a course nested inside a larger
    repo never sweeps up its parent's unrelated work."""
    _git(course, "add", "-A", "--", ".")
    if _dirty(course):
        _git(course, "commit", "-q", "-m", message, "--", ".")
        return True
    return False


# ---------------------------------------------------------------- recover

def cmd_recover(course: Path):
    """Three-way recovery, decidable from structure alone.

    fresh sentinel        -> a session is LIVE: lock, touch nothing
    stale + grades log    -> close finished but never committed: replay
    stale + no grades log -> genuine mid-flight crash: discard the debris

    Age comes from the sentinel's own mtime, so no clock, timezone, or
    agent-authored timestamp can enter the decision.
    """
    course = Path(course)
    if _ensure_repo(course):
        return "initialized"
    sentinel = course / SENTINEL
    if not sentinel.exists():
        return "ok"

    age = _now() - dt.datetime.fromtimestamp(sentinel.stat().st_mtime)
    if age < dt.timedelta(hours=STALE_HOURS):
        return "locked"  # NEVER reset a signature a live session presents

    fields = dict(
        line.partition(":")[::2] for line in
        _read(sentinel).splitlines() if ":" in line)
    session = fields.get("session", "").strip()
    if not valid_session_token(session):
        # we do not know what this session was; refuse to destroy anything
        return "locked"

    logs = sorted((course / "log").glob(f"*-{session}.md"))
    if logs:
        try:
            cmd_commit_grades(course, logs[-1])  # no-op if already applied
            sentinel.unlink()
            _commit(course, f"recover: replayed session {session}")
            return "replayed"
        except (FormatError, IntegrityError):
            pass  # unusable draft: treat as mid-flight crash

    # scoped to the course subtree — never `reset --hard` a parent repo
    _git(course, "checkout", "-q", "--", ".")
    _git(course, "clean", "-fdq", "--", ".")
    if sentinel.exists():
        sentinel.unlink()
    return "reset"


# ------------------------------------------------------------ begin / close

def _next_token(idx: int, kind: str, committed) -> str:
    if kind != "repair":
        return str(idx)
    for n in range(1, 50):
        tok = f"{idx}r" if n == 1 else f"{idx}r{n}"
        if tok not in committed:
            return tok
    raise IntegrityError(f"session {idx} has been repaired 49 times")


def course_label(course: Path) -> str:
    """Short human name for this course — disambiguates several courses
    sharing one chat. `name:` in domain-map.md wins; otherwise the
    directory basename, prettified."""
    try:
        n = _map_header(course).get("name", "").strip()
        if n:
            return n
    except Exception:
        pass
    return Path(course).resolve().name.replace("-", " ").replace("_", " ")


# The pilot's worst failure: two stateless tutors, same state, same
# policy, converged on the SAME quiz questions two sessions running.
# The fix is state the next tutor sees, not a stronger exhortation:
# every question asked lands in the log's '## asked' section, and begin
# replays the recent ones. All matching is case-insensitive — tutors do
# not capitalize consistently.
ASKED_HEAD_RE = re.compile(r"^##+\s*asked\s*$", re.M | re.I)
BANK_ID_RE = re.compile(r"^\S+\.(?:q|apply|int|ex)\d*$", re.I)


def _asked_items(text: str):
    m = ASKED_HEAD_RE.search(text)
    if not m:
        return []
    rest = text[m.end():]
    nxt = re.search(r"^##+\s", rest, re.M)
    scope = rest[:nxt.start()] if nxt else rest
    return [ln.strip()[2:].strip() for ln in scope.splitlines()
            if ln.strip().startswith("- ") and ln.strip()[2:].strip()]


def _asked_history(course: Path):
    """(recent, bank): what the last ASKED_RECENCY sessions asked, and
    every asset-bank item id ever used. Bank items are single-use for the
    whole course; free-text case signatures age out of the recent list."""
    logs = sorted((Path(course) / "log").glob("*.md"), reverse=True)
    recent, bank, seen, seen_bank = [], [], set(), set()
    for i, path in enumerate(logs):
        m = re.match(r"\d{4}-\d\d-\d\d-(.+)\.md$", path.name)
        tok = m.group(1) if m else path.stem
        for item in _asked_items(_read(path)):
            head = item.split()[0]
            if BANK_ID_RE.match(head) and head.casefold() not in seen_bank:
                seen_bank.add(head.casefold())
                bank.append(head)
            if i < ASKED_RECENCY and item.casefold() not in seen:
                seen.add(item.casefold())
                recent.append((tok, item))
    return recent, sorted(bank, key=str.casefold)


def _last_log(course: Path):
    """(path, token, date, open_question) for the newest session log."""
    logs = sorted((Path(course) / "log").glob("*.md"))
    if not logs:
        return None
    path = logs[-1]
    m = re.match(r"(\d{4}-\d\d-\d\d)-(.+)\.md$", path.name)
    date, token = (m.group(1), m.group(2)) if m else ("", "")
    text = _read(path)
    q = ""
    m = re.search(r"^##+\s*open question\s*$(.*?)(?=^##\s|\Z)",
                  text, re.M | re.I | re.S)
    if m:
        q = " ".join(m.group(1).split())
    return path, token, date, q


def cmd_begin(course: Path):
    """Everything before the first word to the user, in one call."""
    course = Path(course)
    # capture the abandoned session's age BEFORE recover clears the sentinel
    sentinel = course / SENTINEL
    abandoned_age = None
    if sentinel.exists():
        abandoned_age = _now() - dt.datetime.fromtimestamp(
            sentinel.stat().st_mtime)
    state = cmd_recover(course)
    if state == "locked":
        raise IntegrityError(
            "a session is already live (.session-inprogress is fresh) — "
            "send nothing and stop")
    cmd_check(course)
    d = dispatch(course)
    meta, _ = load_state(course)
    token = _next_token(d["index"], d["type"], meta["committed-sessions"])

    sentinel = course / SENTINEL
    try:
        fd = os.open(sentinel, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise IntegrityError("a session is already live — send nothing")
    with os.fdopen(fd, "w") as fh:
        fh.write(f"session: {token}\n")

    ids = cmd_queue(course, cap=d["cap"], terminal=d["terminal"])
    _, records = load_state(course)
    lines = [f"recover: {state}",
             f"course: {course_label(course)}",
             f"session: {token} of {d['size']}",
             f"type: {d['type']}  ({d['why']})"]
    if d.get("concept"):
        lines.append(f"concept: {d['concept']}")
    if d["unit"]:
        u = d["unit"]
        lines.append(f"unit: {u['num']} — {u['title']}")
        lines.append(f"assets: assets/unit-{u['num']:02d}.md")
        untaught = [c for c in u["concepts"]
                    if records[c]["status"] == "untaught"]
        lines.append(f"untaught here: {', '.join(untaught) or '-'}")
        if u["artifact"] and u["artifact"] != "none":
            lines.append(f"artifact-milestone: {u['artifact']}")
    lines.append(f"quiz these ({len(ids)}): {', '.join(ids) or '-'}")
    if d["author"]:
        lines.append(f"author-after-close: {d['author']}")

    # --- continuity: where the learner actually left off -------------
    last = _last_log(course)
    if last:
        _, tok, date, question = last
        gap = ""
        if date:
            try:
                days = (_today(course) - dt.date.fromisoformat(date)).days
                gap = ("today" if days == 0 else "yesterday" if days == 1
                       else f"{days} days ago")
            except ValueError:
                pass
        lines.append(f"last session: {tok} on {date}"
                     + (f" ({gap})" if gap else ""))
        if question:
            lines.append(f"open question: {question}")
    asked, bank = _asked_history(course)
    if asked:
        lines.append("asked recently (do not reuse — a new case means a "
                     "new decision and inference chain, not new names):")
        lines += [f"  [{tok}] {item}" for tok, item in asked]
    if bank:
        lines.append("bank items used (single-use, never repeat): "
                     + ", ".join(bank))
    if state == "reset" and abandoned_age is not None:
        hrs = int(abandoned_age.total_seconds() // 3600)
        lines.append(
            f"NOTE: a session was started ~{hrs}h ago and abandoned before "
            "it closed — nothing was recorded, so this session repeats it. "
            "They may remember part of it: open differently, and check what "
            "already landed before re-teaching it.")
    elif state == "replayed":
        lines.append(
            "NOTE: the previous session's close was recovered just now — "
            "its grades have only just been applied.")
    return "\n".join(lines)


def cmd_close(course: Path, logfile: Path):
    """Everything after the last word to the user, in one call: grades,
    plan.md, git, unlock. All the arithmetic the agent must not do."""
    course = Path(course)
    logfile = Path(logfile)
    if not logfile.is_absolute():
        logfile = course / logfile if not logfile.exists() else logfile
    session, _ = parse_log_grades(_read(logfile))

    sentinel = course / SENTINEL
    if sentinel.exists():
        fields = dict(line.partition(":")[::2] for line in
                      _read(sentinel).splitlines() if ":" in line)
        held = fields.get("session", "").strip()
        if held and held != session:
            raise IntegrityError(
                f"the live session is {held!r} but this log says {session!r} "
                "— refusing to close someone else's session")

    applied = cmd_commit_grades(course, logfile)
    header, units = parse_plan(course)
    idx = session_index(header)
    today = _today(course)

    updates = {"sessions-done": int(header["sessions-done"]) + 1,
               "last-attended": today.isoformat(),
               "re-entry-pending": "no"}
    # a repair session carries a fractional token; it must not move the counter
    advanced = not session.rstrip("0123456789").endswith("r")
    if advanced:
        updates["next-session"] = f"{idx + 1}/{course_size(header)}"
    write_plan_header(course, updates)

    here = next((u for u in units if u["start"] <= idx <= u["end"]), None)
    if here and advanced and here.get("num") is not None:
        write_unit_status(course, here["num"],
                          "taught" if idx >= here["end"] else "in-progress")

    cmd_queue(course)
    _commit(course, f"session {session}")
    if sentinel.exists():
        sentinel.unlink()
        _commit(course, f"session {session}: unlock")
    nxt = session_index(parse_plan(course)[0])
    return (f"closed session {session} ({applied})\n"
            f"next: {nxt}/{course_size(header)}")


# -------------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(prog="schedule.py", description=__doc__)
    ap.add_argument("--course", default=".", help="course directory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for verb in ("begin", "check", "queue", "report", "recover"):
        sub.add_parser(verb)
    p = sub.add_parser("close")
    p.add_argument("logfile")
    p = sub.add_parser("commit-grades")
    p.add_argument("logfile")
    p = sub.add_parser("seed")
    p.add_argument("id")
    p.add_argument("evidence", choices=sorted(SEED_INTERVAL))
    p = sub.add_parser("set-verify")
    p.add_argument("id")
    p.add_argument("mech", choices=sorted(VERIFIES))
    p = sub.add_parser("reprune")
    p.add_argument("ids", help="comma-separated concept ids")
    a = ap.parse_args(argv)
    course = Path(a.course)
    try:
        if a.cmd == "begin":
            print(cmd_begin(course))
        elif a.cmd == "close":
            print(cmd_close(course, a.logfile))
        elif a.cmd == "check":
            print(cmd_check(course))
        elif a.cmd == "queue":
            print("\n".join(cmd_queue(course)))
        elif a.cmd == "report":
            print(cmd_report(course))
        elif a.cmd == "recover":
            print(cmd_recover(course))
        elif a.cmd == "seed":
            cmd_seed(course, a.id, a.evidence)
        elif a.cmd == "commit-grades":
            print(cmd_commit_grades(course, Path(a.logfile)))
        elif a.cmd == "set-verify":
            cmd_set_verify(course, a.id, a.mech)
        elif a.cmd == "reprune":
            cmd_reprune(course, [s for s in a.ids.split(",") if s])
    except (FormatError, IntegrityError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:                      # never hand back a traceback
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
