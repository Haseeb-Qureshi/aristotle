"""SCHEDULER simulation, not a learning simulation: drives N sessions of a
course through the real engine with a scripted tutor that follows every
brief, misses ~15% of review items and ~1 in 5 teach-backs, and logs its
questions. It tests queue dynamics, dispatch and bookkeeping; it says
nothing about whether anyone learns (use the capped-student harness for
that). One row per session; exits 1 if any session fails."""
import datetime as dt, hashlib, os, re, subprocess, sys
from pathlib import Path
course = Path(sys.argv[1]); n = int(sys.argv[2]); day = dt.date.fromisoformat(sys.argv[3])
E = ["python3", "scripts/schedule.py", "--course", "."]
failures = 0
for i in range(n):
    env = dict(os.environ, ARISTOTLE_TODAY=day.isoformat())
    r = subprocess.run(E + ["begin"], cwd=course, env=env, capture_output=True, text=True)
    if r.returncode:
        print("BEGIN FAILED", r.stderr); failures += 1; break
    b = r.stdout
    g = lambda k: (re.search(rf"^{k}: (.*)$", b, re.M) or [None, "-"])[1]
    if re.search(r"^type: (graduation|lifecycle|dormant)", b, re.M):
        print(f"{day} {g('type')} — no session to run (checkpoint.md); stop")
        break
    token = g("session").split()[0]; typ = g("type").split()[0]
    quiz = [q for q in g(r"quiz these \(\d+\)").split(", ") if q != "-"]
    teach = re.search(r"^teach: (\S+)", b, re.M); back = re.search(r"^teach-back: (\S+)", b, re.M)
    owed = re.findall(r"^owed: (\S+) — ", b, re.M)
    taught, grades = [], []
    if teach and typ in ("standard", "catch-up"):
        taught.append(f"- {teach.group(1)}: worked example presented")
        grades.append(f"- grade: {teach.group(1)} | result: taught | note: sim")
    if back:
        hb = int(hashlib.sha256(f"{token}|back".encode()).hexdigest()[:4], 16)
        rb = "rubric-fail" if hb % 5 == 0 else "rubric-pass"
        grades.append(f"- grade: {back.group(1)} | result: {rb} | note: sim")
    for q in quiz:
        # deterministic ~15% misses, so queue dynamics under fails get tested
        h = int(hashlib.sha256(f"{token}|{q}".encode()).hexdigest()[:4], 16)
        res = "fail" if h % 7 == 0 else "pass"
        grades.append(f"- grade: {q} | result: {res} | note: sim")
    for c in owed:
        if not any(t.startswith(f"- {c}:") for t in taught):
            taught.append(f"- {c}: owed: repaid in a correction")
    if not grades:
        # nothing was graded: the learner "went quiet" — decline the
        # session the documented way (delete the lock, close nothing)
        (course / ".session-inprogress").unlink()
        print(f"{day} {token:>5} {typ:<12} declined: nothing to grade")
        day += dt.timedelta(days=2)
        continue
    asked = "".join(f"- sim case for {q} on {day}\n" for q in quiz)
    log = course / g("log file")
    text = log.read_text()
    text = text.replace("## taught\n", "## taught\n" + "".join(x + "\n" for x in taught))
    text = text.replace("## grades\n", "## grades\n" + "".join(x + "\n" for x in grades))
    text = text.replace("## asked\n", "## asked\n" + asked)
    text = text.replace("## open question\n", "## open question\nsim question\n")
    log.write_text(text)
    c = subprocess.run(E + ["close", str(log.relative_to(course))], cwd=course, env=env, capture_output=True, text=True)
    status = "ok" if c.returncode == 0 else "CLOSE FAILED: " + c.stderr.strip()[:120]
    failures += c.returncode != 0
    warn = " WARN" if "warn:" in c.stdout else ""
    rev = (re.search(r"^review: (.*?)(?: —|$)", b, re.M) or [None, "-"])[1]
    tgt = (back and "teach-back " + back.group(1)) or (teach and teach.group(1)) or "-"
    print(f"{day} {token:>5} {typ:<12} {tgt:<38} review[{rev:<22}] quiz={','.join(quiz) or '-':<45} owed={','.join(owed) or '-'} {status}{warn}")
    day += dt.timedelta(days=2)
sys.exit(1 if failures else 0)
