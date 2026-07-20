#!/usr/bin/env python3
"""elenchus schedule.py — the deterministic core.

Owns everything the teaching agent must never improvise: date arithmetic,
the mastery transition table, status changes, queue generation, integrity
checks, and crash recovery. The agent's entire write surface is grade
lines in a session log; this script does the rest.

Stdlib only (python3 >= 3.9). Copied into every course directory at
bootstrap so a resurrected course is self-contained.

Verbs:
  check                       integrity pass (loud failure)
  queue                       regenerate review-queue.md
  seed <id> <band>            calibration upsert (idempotent)
  commit-grades <logfile>     apply a session's grade lines atomically
  set-verify <id> <mech>      adjudication verdicts
  reprune --drop a,b,c        shrink the course coherently
  report                      progress / due / plateaued summary
  recover                     sentinel + git three-way recovery

State ownership: knowledge-state.md is written ONLY by this script, via
atomic os.replace. Script-owned course flags (committed-sessions,
solid-pending, repair-pending) live in its header block so one atomic
write covers grades and flags together.

Test hooks: ELENCHUS_TODAY (YYYY-MM-DD) pins "today"; ELENCHUS_NOW pins
the recovery clock. Absent, the course timezone from domain-map.md rules.
"""

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

LADDER = [1, 3, 7, 16, 35, 90, 180]
BANDS = ["none", "exposed", "retrievable", "solid"]
STATUSES = {"untaught", "active", "plateaued", "dropped"}
VERIFIES = {"quiz", "use", "none"}
# 'solid' is deliberately NOT a writable result: the script derives it.
RESULTS = {"taught", "pass", "fail", "rubric-pass", "rubric-fail"}
RECORD_FIELDS = ["id", "verify", "ceiling", "mastery", "status", "last",
                 "next", "interval", "fails", "reprobe", "note"]
INT_FIELDS = {"interval", "fails"}
SENTINEL = ".session-inprogress"
QUEUE_CAP = 5
PLATEAU_FAILS = 3
STALE_HOURS = 2  # a sentinel younger than this means a session is LIVE


class FormatError(Exception):
    """A file or grade line does not match its grammar."""


class IntegrityError(Exception):
    """Cross-file state disagrees, or an operation would corrupt it."""


# --------------------------------------------------------------- clock

def _today(course: Path) -> dt.date:
    env = os.environ.get("ELENCHUS_TODAY")
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


def _now(course: Path) -> dt.datetime:
    env = os.environ.get("ELENCHUS_NOW")
    if env:
        return dt.datetime.fromisoformat(env)
    if os.environ.get("ELENCHUS_TODAY"):
        # deterministic tests: noon on the pinned day
        return dt.datetime.combine(_today(course), dt.time(12, 0))
    return dt.datetime.now()


# ------------------------------------------------- knowledge-state file

STATE_FILE = "knowledge-state.md"
HEADER_RE = re.compile(r"<!-- elenchus:state\n(.*?)\n-->\n?", re.S)


def parse_state(text: str):
    """Return (meta, records). Loud on any format violation."""
    m = HEADER_RE.search(text)
    if not m:
        raise FormatError("knowledge-state.md missing elenchus:state header")
    meta = {"committed-sessions": [], "solid-pending": "none",
            "repair-pending": "none"}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("format:"):
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key == "committed-sessions":
            meta[key] = [t for t in re.split(r"[,\s]+", val) if t]
        elif key in ("solid-pending", "repair-pending"):
            meta[key] = val or "none"
        else:
            raise FormatError(f"unknown state-header field: {key}")

    records = {}
    for raw in text[m.end():].splitlines():
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
            rec[key] = int(val) if key in INT_FIELDS else val.strip()
        missing = [f for f in RECORD_FIELDS if f not in rec]
        if missing:
            raise FormatError(f"record {rec.get('id')!r} missing {missing}")
        if rec["id"] in records:
            raise FormatError(f"duplicate concept id: {rec['id']}")
        records[rec["id"]] = rec
    return meta, records


def serialize_state(meta, records) -> str:
    head = ["<!-- elenchus:state",
            "committed-sessions: " + ",".join(meta["committed-sessions"]),
            f"solid-pending: {meta['solid-pending']}",
            f"repair-pending: {meta['repair-pending']}",
            "-->"]
    lines = []
    for rec in records.values():
        rec = dict(rec)
        # '|' is the field delimiter; it may never appear inside a value
        rec["note"] = str(rec["note"]).replace("|", "/")
        lines.append("- " + " | ".join(
            f"{f}: {rec[f]}" for f in RECORD_FIELDS))
    return "\n".join(head) + "\n" + "\n".join(lines) + "\n"


def load_state(course: Path):
    return parse_state((Path(course) / STATE_FILE).read_text())


def save_state(course: Path, meta, records):
    """Single atomic write: grades and flags land together or not at all."""
    path = Path(course) / STATE_FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text(serialize_state(meta, records))
    os.replace(tmp, path)


# ----------------------------------------------------------- domain map

CONCEPT_RE = re.compile(r"^### (\S+)\s*$", re.M)
ERRATUM_RE = re.compile(
    r"^erratum [^:]*:\s*(remove-edge|add-edge)\s+(\S+)\s*->\s*(\S+)", re.M)


def _map_header(course: Path) -> dict:
    text = (Path(course) / "domain-map.md").read_text()
    head = text.split("###", 1)[0]
    out = {}
    for line in head.splitlines():
        k, sep, v = line.partition(":")
        if sep and " " not in k.strip():
            out[k.strip()] = v.strip()
    return out


def parse_map(course: Path):
    """Return {id: {prereqs, verify, ceiling, threshold}} with errata
    already merged over the frozen graph (ids stay immutable; edges heal)."""
    text = (Path(course) / "domain-map.md").read_text()
    ids = CONCEPT_RE.findall(text)
    blocks = CONCEPT_RE.split(text)[1:]  # id, body, id, body ...
    concepts = {}
    for cid, body in zip(blocks[0::2], blocks[1::2]):
        c = {"prereqs": [], "verify": "quiz", "ceiling": "solid",
             "threshold": "no"}
        for line in body.splitlines():
            k, sep, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k == "prereqs":
                c["prereqs"] = [p for p in
                                re.split(r"[,\s]+", v.strip("[]")) if p]
            elif k in ("verify", "ceiling", "threshold"):
                c[k] = v
        concepts[cid] = c
    for op, a, b in ERRATUM_RE.findall(text):
        if b in concepts:
            pre = concepts[b]["prereqs"]
            if op == "remove-edge" and a in pre:
                pre.remove(a)
            if op == "add-edge" and a not in pre:
                pre.append(a)
    return concepts


# ----------------------------------------------------------------- plan

UNIT_RE = re.compile(r"^## Unit (\d+):", re.M)


def parse_plan(course: Path):
    text = (Path(course) / "plan.md").read_text()
    header = {}
    for line in text.split("## ", 1)[0].splitlines():
        k, sep, v = line.partition(":")
        if sep:
            header[k.strip()] = v.strip()
    units = []
    for chunk in text.split("\n## ")[1:]:
        unit = {"title": chunk.splitlines()[0], "concepts": [],
                "keystones": [], "status": ""}
        for line in chunk.splitlines()[1:]:
            k, sep, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k in ("concepts", "keystones"):
                unit[k] = [p for p in
                           re.split(r"[,\s]+", v.strip("[]")) if p]
            elif k == "status":
                unit["status"] = v
        units.append(unit)
    return header, units


# ---------------------------------------------------------- grade lines

SESSION_TOKEN_RE = re.compile(r"^\d+(r\d*)?$")
GRADE_RE = re.compile(
    r"^- grade:\s*(\S+)\s*\|\s*result:\s*(\S+)\s*\|\s*note:\s*(.*)$")


def valid_session_token(tok: str) -> bool:
    return bool(SESSION_TOKEN_RE.match(tok))


def parse_log_grades(text: str):
    """Return (session_token, grades). Any line that LOOKS like a grade
    but doesn't parse is a loud error — silence is how mastery dies."""
    session = None
    grades = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("session:"):
            session = line.split(":", 1)[1].strip()
        elif line.startswith("- grade:"):
            m = GRADE_RE.match(line)
            if not m:
                raise FormatError(f"malformed grade line: {line!r}")
            cid, result, note = m.groups()
            if result not in RESULTS:
                raise FormatError(
                    f"invalid result {result!r} (allowed: "
                    f"{sorted(RESULTS)}; 'solid' is never writable — "
                    "the script derives it)")
            grades.append({"id": cid, "result": result,
                           "note": note.strip()})
    if session is None:
        raise FormatError("log has no 'session:' line")
    if not valid_session_token(session):
        raise FormatError(f"bad session token {session!r} "
                          "(grammar: digits, optional r-suffix e.g. 17r)")
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


def _band_cap(band: str, ceiling: str) -> str:
    if BANDS.index(band) > BANDS.index(ceiling):
        return ceiling
    return band


def _apply_grade(rec, grade, meta, today: dt.date, next_unit_needs):
    """The transition table. One grade, one record, pure and total."""
    result = grade["result"]
    iso = today.isoformat()

    if result == "taught":
        rec["status"] = "active" if rec["status"] == "untaught" \
            else rec["status"]
        if rec["mastery"] == "none":
            rec["mastery"] = _band_cap("exposed", rec["ceiling"])
        rec["interval"] = 1
        rec["last"], rec["next"] = iso, (today + dt.timedelta(1)).isoformat()

    elif result == "pass":
        prev = rec["interval"]
        rec["fails"] = 0
        if rec["mastery"] == "exposed":
            rec["mastery"] = _band_cap("retrievable", rec["ceiling"])
        if rec["reprobe"] == "pending":
            rec["reprobe"] = "done"
            if meta["solid-pending"] == rec["id"]:
                meta["solid-pending"] = "none"
        # solid needs BOTH the delayed re-probe AND surviving the 35-day
        # interval (successive relearning: one delayed pass isn't storage)
        if rec["reprobe"] == "done" and prev >= 35:
            rec["mastery"] = _band_cap("solid", rec["ceiling"])
        rec["interval"] = ladder_up(prev)
        rec["last"], rec["next"] = iso, \
            (today + dt.timedelta(rec["interval"])).isoformat()

    elif result == "fail":
        # step back one rung, never to zero: a lapse is not amnesia
        rec["interval"] = ladder_down(rec["interval"])
        rec["fails"] += 1
        if rec["fails"] >= PLATEAU_FAILS:
            rec["status"] = "plateaued"
        rec["last"], rec["next"] = iso, \
            (today + dt.timedelta(rec["interval"])).isoformat()

    elif result == "rubric-pass":
        # teach-back success: schedule the delayed re-probe for tomorrow
        meta["solid-pending"] = rec["id"]
        rec["reprobe"] = "pending"
        rec["last"], rec["next"] = iso, (today + dt.timedelta(1)).isoformat()

    elif result == "rubric-fail":
        rec["last"] = iso
        # only a failed hard prerequisite of the NEXT unit triggers repair
        if rec["id"] in next_unit_needs:
            meta["repair-pending"] = rec["id"]


def _next_unit_prereq_ids(course: Path):
    """Concept ids that the next untouched unit hard-depends on."""
    concepts = parse_map(course)
    _, units = parse_plan(course)
    for unit in units:
        if unit["status"] == "untouched":
            needed = set()
            for cid in unit["concepts"]:
                needed.update(concepts.get(cid, {}).get("prereqs", []))
            return needed
    return set()


def cmd_commit_grades(course: Path, logfile: Path):
    course = Path(course)
    session, grades = parse_log_grades(Path(logfile).read_text())
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

def build_queue(course: Path):
    course = Path(course)
    meta, records = load_state(course)
    today = _today(course).isoformat()
    due = [r for r in records.values()
           if r["status"] == "active" and r["verify"] != "none"
           and r["next"] not in ("-", "") and r["next"] <= today]
    pending = meta["solid-pending"]
    head = []
    if pending != "none" and pending in records:
        head = [pending]  # the promotion re-probe rides OUTSIDE the cap
        due = [r for r in due if r["id"] != pending]
    due.sort(key=lambda r: r["next"])
    return head + [r["id"] for r in due[:QUEUE_CAP]]


def cmd_queue(course: Path):
    course = Path(course)
    ids = build_queue(course)
    meta, records = load_state(course)
    today = _today(course).isoformat()
    total_due = sum(1 for r in records.values()
                    if r["status"] == "active" and r["verify"] != "none"
                    and r["next"] not in ("-", "") and r["next"] <= today)
    rolled = max(0, total_due - len(ids))
    lines = ["<!-- GENERATED by schedule.py — never hand-edit -->",
             f"<!-- date: {today} | rolled-forward: {rolled} -->"]
    lines += [f"- {i}" for i in ids]
    (course / "review-queue.md").write_text("\n".join(lines) + "\n")
    return ids


# ------------------------------------------------- seed / verify / prune

def cmd_seed(course: Path, cid: str, band: str):
    course = Path(course)
    if band not in BANDS:
        raise FormatError(f"unknown band {band!r}")
    concepts = parse_map(course)
    if cid not in concepts:
        raise IntegrityError(f"seed: {cid!r} is not in the domain map")
    meta, records = load_state(course)
    today = _today(course)
    c = concepts[cid]
    records[cid] = {   # upsert: rerunning session 1 cannot duplicate rows
        "id": cid, "verify": c["verify"], "ceiling": c["ceiling"],
        "mastery": _band_cap(band, c["ceiling"]),
        "status": "active" if band != "none" else "untaught",
        "last": today.isoformat(),
        "next": (today + dt.timedelta(1)).isoformat(),
        "interval": 1, "fails": 0, "reprobe": "-", "note": "seeded",
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
    save_state(course, meta, records)


def cmd_reprune(course: Path, drop):
    """Shrink the course coherently: state + plan in one operation.
    Refuses to orphan a kept concept's prerequisite."""
    course = Path(course)
    concepts = parse_map(course)
    meta, records = load_state(course)
    dropset = set(drop)
    kept = {cid for cid, r in records.items()
            if cid not in dropset and r["status"] != "dropped"}
    for cid in kept:
        broken = dropset & set(concepts.get(cid, {}).get("prereqs", []))
        if broken:
            raise IntegrityError(
                f"cannot drop {sorted(broken)}: prerequisite(s) of kept "
                f"concept {cid!r}")
    for cid in dropset:
        if cid not in records:
            raise IntegrityError(f"reprune: unknown concept {cid!r}")
        records[cid]["status"] = "dropped"
    save_state(course, meta, records)
    # plan.md: remove dropped ids from concepts/keystones lists in place
    plan_path = course / "plan.md"
    text = plan_path.read_text()

    def strip_ids(m):
        ids = [p for p in re.split(r"[,\s]+", m.group(2).strip("[]"))
               if p and p not in dropset]
        return f"{m.group(1)}: [{', '.join(ids)}]"
    text = re.sub(r"^(concepts|keystones):\s*(\[[^\]]*\])",
                  strip_ids, text, flags=re.M)
    tmp = plan_path.with_suffix(".tmp")
    tmp.write_text(text)
    os.replace(tmp, plan_path)


# ------------------------------------------------------------------ check

def cmd_check(course: Path):
    course = Path(course)
    concepts = parse_map(course)          # errata already merged
    meta, records = load_state(course)    # FormatError on dup/multiline
    _, units = parse_plan(course)

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

    # cross-file id agreement (asymmetric: dropped may vanish from plan)
    missing = set(concepts) - set(records)
    if missing:
        raise IntegrityError(
            f"map concepts with no knowledge-state row: {sorted(missing)}")
    orphans = set(records) - set(concepts)
    if orphans:
        raise IntegrityError(
            f"knowledge-state rows not in map: {sorted(orphans)}")
    for unit in units:
        for cid in unit["concepts"] + unit["keystones"]:
            if cid not in concepts:
                raise IntegrityError(
                    f"plan references unknown concept {cid!r} "
                    f"in {unit['title']!r}")
    return "ok"


# ----------------------------------------------------------------- report

def cmd_report(course: Path):
    course = Path(course)
    meta, records = load_state(course)
    today = _today(course).isoformat()
    active = [r for r in records.values() if r["status"] == "active"]
    due = [r["id"] for r in active
           if r["verify"] != "none" and r["next"] not in ("-", "")
           and r["next"] <= today]
    plateaued = [r["id"] for r in records.values()
                 if r["status"] == "plateaued"]
    bands = {b: sum(1 for r in records.values() if r["mastery"] == b)
             for b in BANDS}
    lines = [
        f"concepts: {len(records)} "
        + " ".join(f"{b}={n}" for b, n in bands.items()),
        f"due today: {len(due)} ({', '.join(due) or '-'})",
        f"plateaued: {len(plateaued)} ({', '.join(plateaued) or '-'})",
        f"solid-pending: {meta['solid-pending']}"
        f" | repair-pending: {meta['repair-pending']}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- recover

def _git(course, *args, check=True):
    return subprocess.run(
        ["git", "-c", "user.name=elenchus", "-c",
         "user.email=elenchus@localhost", *args],
        cwd=course, check=check, capture_output=True, text=True)


def _dirty(course) -> bool:
    out = _git(course, "status", "--porcelain").stdout
    return bool(out.strip())


def cmd_recover(course: Path):
    """Three-way recovery, decidable from structure alone.

    fresh sentinel        -> a session is LIVE: lock, touch nothing
    stale + grades log    -> close finished but never committed: replay
                             (commit-grades is idempotent) and commit
    stale + no grades log -> genuine mid-flight crash: reset hard, clean
    """
    course = Path(course)
    sentinel = course / SENTINEL
    if not sentinel.exists():
        if _dirty(course):
            cmd_check(course)  # validate BEFORE blessing dirt into history
            _git(course, "add", "-A")
            _git(course, "commit", "-m", "recover: commit-as-is")
            return "committed"
        return "ok"

    fields = dict(
        line.partition(":")[::2] for line in
        sentinel.read_text().splitlines() if ":" in line)
    session = fields.get("session", "").strip()
    started = fields.get("started", "").strip()
    try:
        age = _now(course) - dt.datetime.fromisoformat(started)
    except ValueError:
        age = dt.timedelta(hours=STALE_HOURS + 1)  # unreadable = stale
    if age < dt.timedelta(hours=STALE_HOURS):
        return "locked"  # NEVER reset a signature a live session presents

    logs = sorted((course / "log").glob(f"*-{session}.md"))
    if logs:
        try:
            parse_log_grades(logs[-1].read_text())
            cmd_commit_grades(course, logs[-1])  # no-op if already applied
            sentinel.unlink()
            _git(course, "add", "-A")
            if _dirty(course):
                _git(course, "commit", "-m",
                     f"recover: replayed session {session}")
            return "replayed"
        except FormatError:
            pass  # unparseable draft: treat as mid-flight crash

    _git(course, "reset", "--hard", "-q")
    _git(course, "clean", "-fdq")
    if sentinel.exists():
        sentinel.unlink()
    return "reset"


# -------------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(prog="schedule.py", description=__doc__)
    ap.add_argument("--course", default=".", help="course directory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sub.add_parser("queue")
    sub.add_parser("report")
    sub.add_parser("recover")
    p = sub.add_parser("seed")
    p.add_argument("id"), p.add_argument("band", choices=BANDS)
    p = sub.add_parser("commit-grades")
    p.add_argument("logfile")
    p = sub.add_parser("set-verify")
    p.add_argument("id"), p.add_argument("mech", choices=sorted(VERIFIES))
    p = sub.add_parser("reprune")
    p.add_argument("--drop", required=True,
                   help="comma-separated concept ids")
    a = ap.parse_args(argv)
    course = Path(a.course)
    try:
        if a.cmd == "check":
            print(cmd_check(course))
        elif a.cmd == "queue":
            print("\n".join(cmd_queue(course)))
        elif a.cmd == "report":
            print(cmd_report(course))
        elif a.cmd == "recover":
            print(cmd_recover(course))
        elif a.cmd == "seed":
            cmd_seed(course, a.id, a.band)
        elif a.cmd == "commit-grades":
            print(cmd_commit_grades(course, Path(a.logfile)))
        elif a.cmd == "set-verify":
            cmd_set_verify(course, a.id, a.mech)
        elif a.cmd == "reprune":
            cmd_reprune(course, [s for s in a.drop.split(",") if s])
    except (FormatError, IntegrityError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
