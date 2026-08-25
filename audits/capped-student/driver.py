#!/usr/bin/env python3
"""Pedagogy audit driver.

Teacher: codex gpt-5.6-sol running the real Aristotle skill on the virgin
course copy (fresh thread per session — the tutor is stateless by design,
its continuity is the course directory).
Student: codex gpt-5.6-luna, ephemeral one-shots. Its continuity is the
full visible transcript, and it is hard-capped to that transcript: any
probe of a fact not present must be answered "you never taught me that".

The audit signal is the divergence between those two continuities.
"""
import json, subprocess, sys, time, traceback
from pathlib import Path

BASE = Path(__file__).parent
COURSE = BASE / "course"
TRANS = BASE / "transcripts"
RAW = BASE / "raw"
LEDGER = BASE / "ledger.md"
for d in (TRANS, RAW):
    d.mkdir(exist_ok=True)

SESSIONS = [("2026-08-25", 1), ("2026-08-26", 2), ("2026-08-28", 3),
            ("2026-08-30", 4), ("2026-09-01", 5)]
MAX_TURNS = 14
USAGE = {"sol_in": 0, "sol_out": 0, "luna_in": 0, "luna_out": 0}
# --ignore-user-config isolates from the user's personal codex setup (MCP
# servers, approvals). Codex's bwrap sandbox cannot start on this box
# (nested sandboxing), so codex runs unsandboxed INSIDE the externally
# sandboxed harness shell — the documented use of the bypass flag.
TEACHER_ARGS = ["--ignore-user-config",
                "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check"]


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)


def codex(args, prompt, timeout, tag, who):
    """Run codex exec, return (thread_id, joined agent message text)."""
    cmd = ["codex", "exec"] + args + ["--json", "-"]
    for attempt in (1, 2):
        try:
            r = subprocess.run(cmd, input=prompt, capture_output=True,
                               text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            log(f"  ! {tag} timeout (attempt {attempt})")
            continue
        (RAW / f"{tag}.jsonl").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr)
        tid, msgs = None, []
        for line in r.stdout.splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "thread.started":
                tid = ev.get("thread_id")
            elif ev.get("type") == "item.completed":
                item = ev.get("item", {})
                if item.get("type") == "agent_message":
                    msgs.append(item.get("text", ""))
            elif ev.get("type") == "turn.completed":
                u = ev.get("usage", {})
                USAGE[f"{who}_in"] += u.get("input_tokens", 0)
                USAGE[f"{who}_out"] += u.get("output_tokens", 0)
        if r.returncode == 0 and msgs:
            return tid, "\n\n".join(m for m in msgs if m.strip())
        log(f"  ! {tag} rc={r.returncode} msgs={len(msgs)} "
            f"(attempt {attempt}): {r.stderr.strip()[:200]}")
        time.sleep(15)
    raise RuntimeError(f"codex call failed twice: {tag}")


def teacher_open(date, n):
    prompt = f"""You are the tutor for today's scheduled session of the course in this directory (your working directory). Read SKILL.md here first and follow it exactly — it is authoritative.

Operational notes (from the operator, not the learner):
- Today's date for this course is {date}. The machine clock may disagree, so run every schedule.py command with the prefix ARISTOTLE_TODAY={date} (e.g. `ARISTOTLE_TODAY={date} python3 scripts/schedule.py --course . begin`).
- The learner ("H") chats from a phone. I relay messages between you. Everything you write in your reply is sent to H verbatim, so never include operator notes, tool output, file paths, or anything the SKILL says to keep silent.
- When it is time to end, do the close bookkeeping silently and make your final reply the goodnight message.

Start the session now."""
    return codex(TEACHER_ARGS + ["-C", str(COURSE), "-m", "gpt-5.6-sol",
                  "-c", 'model_reasoning_effort="high"'],
                 prompt, 900, f"s{n}-t01", "sol")


def teacher_turn(tid, n, turn, student_msg):
    return codex(["resume", tid] + TEACHER_ARGS, student_msg, 900,
                 f"s{n}-t{turn:02d}", "sol")


def student_turn(transcript, tutor_msg, n, turn):
    prompt = f"""You are simulating a human student, "H", taking a phone-based tutoring course on AI economics. Reply with H's next chat message ONLY — no tools, no file access, no meta-commentary.

Rules that define H:
1. KNOWLEDGE CAP — the single most important rule. H knows ONLY what the tutor has said in the transcript below. H has NO outside knowledge of AI economics, chips, GPUs, datacenters, cloud pricing, or markets. General business common sense is fine; domain facts, names, numbers, and terms are not.
2. If the tutor's question requires recalling or using a fact, term, name, or number that does NOT appear anywhere in the transcript, do NOT guess it from world knowledge and do NOT bluff. Say plainly that it wasn't taught, e.g. "I don't think you've taught me what X is" or "you never gave me that number."
3. When the material IS in the transcript, answer in your own words — usually correctly, occasionally with a small honest imperfection (H is a good but human student).
4. SIDE QUESTS: once or twice per session, before answering, H asks a curious tangential question sparked by something the tutor just said. H follows the tutor's lead if redirected.
5. Style: a busy person typing on a phone. 1-4 sentences. No headers, no bullet lists.
6. H never volunteers to end the session; H keeps engaging until the tutor wraps up. After the tutor's goodnight, H just says thanks/goodbye.

FULL TRANSCRIPT SO FAR (every session to date):
{transcript}

The tutor just said:
{tutor_msg}

H's reply:"""
    _, msg = codex(["--ignore-user-config", "-c", 'approval_policy="never"',
                    "--ephemeral", "-s", "read-only", "-C", str(BASE),
                    "-m", "gpt-5.6-luna", "-c", 'model_reasoning_effort="low"',
                    "--skip-git-repo-check"], prompt, 600,
                   f"s{n}-h{turn:02d}", "luna")
    return msg


def append(path, text):
    with open(path, "a") as f:
        f.write(text)


def close_ok(date, n):
    lock = (COURSE / ".session-inprogress").exists()
    logf = (COURSE / f"log/{date}-{n}.md").exists()
    return (not lock) and logf


def run():
    for date, n in SESSIONS:
        log(f"=== session {n} ({date}) ===")
        sf = TRANS / f"session-{n}.md"
        append(sf, f"# Session {n} — {date}\n\n")
        append(LEDGER, f"\n\n===== SESSION of {date} =====\n\n")
        transcript = LEDGER.read_text() if LEDGER.exists() else ""

        tid, tmsg = teacher_open(date, n)
        turn = 1
        while True:
            log(f"  tutor turn {turn}: {tmsg[:90].replace(chr(10),' ')}")
            append(sf, f"**TUTOR:** {tmsg}\n\n")
            append(LEDGER, f"TUTOR: {tmsg}\n\n")
            transcript = LEDGER.read_text()
            if "Next time (" in tmsg:
                log("  goodnight detected")
                break
            if turn >= MAX_TURNS:
                log("  ! MAX_TURNS hit without close — nudging (finding)")
                append(sf, "*(operator: max turns hit; close nudged)*\n\n")
                _, tmsg = teacher_turn(
                    tid, n, turn + 1,
                    "(operator note — the learner has left the chat. If the "
                    "session is not yet closed per SKILL.md section 4, close "
                    "it now: write the log file and run close. Reply with "
                    "only the word: done)")
                break
            hmsg = student_turn(transcript, tmsg, n, turn)
            log(f"  H turn {turn}: {hmsg[:90].replace(chr(10),' ')}")
            append(sf, f"**H:** {hmsg}\n\n")
            append(LEDGER, f"H: {hmsg}\n\n")
            turn += 1
            _, tmsg = teacher_turn(tid, n, turn, hmsg)

        if not close_ok(date, n):
            log("  ! session not closed after goodnight — nudging (finding)")
            append(sf, "*(operator: close missing after goodnight; nudged)*\n\n")
            codex(["resume", tid] + TEACHER_ARGS,
                  "(operator note — the learner is gone and the session is "
                  "not closed: no log file / lock still present. Close per "
                  "SKILL.md section 4 now. Reply with only the word: done)",
                  900, f"s{n}-close", "sol")
        log(f"  closed ok: {close_ok(date, n)}")
        head = subprocess.run(["git", "-C", str(COURSE), "log", "--oneline",
                               "-1"], capture_output=True, text=True).stdout
        nxt = [l for l in (COURSE / "plan.md").read_text().splitlines()
               if l.startswith("next-session")]
        log(f"  git: {head.strip()}  plan: {nxt}")
        log(f"  usage so far: {USAGE}")


if __name__ == "__main__":
    try:
        run()
        log(f"DONE. usage: {USAGE}")
    except Exception:
        traceback.print_exc()
        log(f"ABORTED. usage: {USAGE}")
        sys.exit(1)
