#!/usr/bin/env python3
"""Build a virgin copy of the ai-economics course for the pedagogy audit.

Resets all schedule state to pre-session-1. This is a scratch SIMULATION
copy — the never-hand-edit rule protects the live course, not this one.
"""
import re, shutil, subprocess, sys
from pathlib import Path

SRC = Path.home() / "projects/ai-economics"
DST = Path(__file__).parent / "course"

if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns(".git", "inbox", "__pycache__"))

# empty the per-session records
for f in (DST / "log").iterdir():
    f.unlink()
memo = DST / "artifact/coreweave-memo.md"
memo.write_text("# CoreWeave memo\n\n(Not started.)\n")

# knowledge-state.md -> every row virgin, empty committed-sessions
ks = DST / "knowledge-state.md"
lines_out = []
for line in ks.read_text().splitlines():
    if line.startswith("- id:"):
        cid = re.search(r"- id:\s*(\S+)", line).group(1)
        verify = re.search(r"verify:\s*(\S+)", line).group(1)
        lines_out.append(
            f"- id: {cid} | verify: {verify} | status: untaught | last: - "
            f"| next: - | interval: 0 | fails: 0 | note: ")
    elif line.startswith("committed-sessions:"):
        lines_out.append("committed-sessions: ")
    else:
        lines_out.append(line)
ks.write_text("\n".join(lines_out) + "\n")

# plan.md -> session 1, nothing attended, all units untouched
plan = DST / "plan.md"
t = plan.read_text()
t = re.sub(r"^next-session: \d+/(\d+)$", r"next-session: 1/\1", t, flags=re.M)
t = re.sub(r"^sessions-done: \d+$", "sessions-done: 0", t, flags=re.M)
t = re.sub(r"^last-attended: .*$", "last-attended: -", t, flags=re.M)
t = re.sub(r"^re-entry-pending: .*$", "re-entry-pending: no", t, flags=re.M)
t = re.sub(r"^status: (taught|in-progress)$", "status: untouched", t, flags=re.M)
plan.write_text(t)

(DST / "history.md").write_text(
    "# History\n\nCourse-level record. Graduation reads this back to "
    "show the delta.\n")

# placement routes to bootstrap.md, which lives in the skill, not the course
shutil.copy(Path.home() / "projects/aristotle/bootstrap.md", DST / "bootstrap.md")

sub = lambda *a: subprocess.run(a, cwd=DST, capture_output=True, text=True)
sub("git", "init", "-q")
sub("git", "add", "-A")
r = sub("git", "-c", "user.email=audit@local", "-c", "user.name=audit",
        "commit", "-qm", "virgin course for pedagogy audit")
if r.returncode:
    sys.exit("git commit failed: " + r.stderr)

# sanity: check + a dry begin on a throwaway clone
r = sub("python3", "scripts/schedule.py", "--course", ".", "check")
print("check:", r.stdout.strip() or r.stderr.strip())
throw = DST.parent / "throwaway"
if throw.exists():
    shutil.rmtree(throw)
shutil.copytree(DST, throw)
import os
env = dict(os.environ, ARISTOTLE_TODAY="2026-08-25")
r = subprocess.run(["python3", "scripts/schedule.py", "--course", ".", "begin"],
                   cwd=throw, capture_output=True, text=True, env=env)
print("--- dry begin ---")
print(r.stdout or r.stderr)
shutil.rmtree(throw)
