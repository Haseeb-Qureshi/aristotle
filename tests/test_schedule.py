"""Tests for scripts/schedule.py — the deterministic core of elenchus.

Written FIRST (TDD). These tests pin the interfaces that two critique
panels found missing from the prose spec:
  - the grade-line grammar and session-token grammar
  - the mastery transition table
  - queue semantics (cap, ordering, solid-pending prepend, exclusions)
  - commit-grades atomicity, idempotency guard, loud unknown-id errors
  - seed upsert idempotency, set-verify, reprune coherence
  - check integrity (DAG + errata merge, cross-file id agreement)
  - recover's three-way decision from structure alone

Run: python3 -m unittest discover -s tests -v
"""

import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "schedule", REPO / "scripts" / "schedule.py")
schedule = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(schedule)

TODAY = "2026-07-20"  # all tests pin "today" via ELENCHUS_TODAY


MAP_MD = """\
# Domain Map
topic: Testing
terminal-task: verify the deterministic core
timezone: America/Los_Angeles
sessions: 30

### alpha
def: first concept
prereqs: []
verify: quiz
ceiling: solid
threshold: yes
misconceptions:
  M1: confuses alpha with beta

### beta
def: second concept
prereqs: [alpha]
verify: quiz
ceiling: solid
threshold: no

### gamma
def: judgment concept
prereqs: []
verify: use
ceiling: retrievable
threshold: no

### delta
def: exposure only
prereqs: []
verify: none
ceiling: retrievable
threshold: no
"""

PLAN_MD = """\
course-status: active
next-session: 3/30
cadence: 3
sessions-done: 2

## Unit 1: Why alpha?
sessions: 2
concepts: [alpha, beta]
keystones: [alpha]
status: in-progress

## Unit 2: Why gamma?
sessions: 2
concepts: [gamma, delta]
keystones: [gamma]
status: untouched
"""

STATE_HEADER = """\
<!-- elenchus:state
committed-sessions:
solid-pending: none
repair-pending: none
-->
"""


def rec_line(id, verify="quiz", ceiling="solid", mastery="exposed",
             status="active", last="2026-07-19", next="2026-07-20",
             interval=1, fails=0, reprobe="-", note=""):
    return (f"- id: {id} | verify: {verify} | ceiling: {ceiling}"
            f" | mastery: {mastery} | status: {status} | last: {last}"
            f" | next: {next} | interval: {interval} | fails: {fails}"
            f" | reprobe: {reprobe} | note: {note}")


class CourseCase(unittest.TestCase):
    """Base: builds a temp course dir and pins today's date."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="elenchus-test-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        os.environ["ELENCHUS_TODAY"] = TODAY
        self.addCleanup(os.environ.pop, "ELENCHUS_TODAY", None)
        (self.dir / "log").mkdir()
        self.write("domain-map.md", MAP_MD)
        self.write("plan.md", PLAN_MD)
        self.write_state([
            rec_line("alpha"),
            rec_line("beta", mastery="none", status="untaught",
                     last="-", next="-", interval=0),
            rec_line("gamma", verify="use", ceiling="retrievable"),
            rec_line("delta", verify="none", mastery="none",
                     status="untaught", last="-", next="-", interval=0),
        ])

    def write(self, name, text):
        (self.dir / name).write_text(text)

    def write_state(self, lines, header=STATE_HEADER):
        self.write("knowledge-state.md", header + "\n".join(lines) + "\n")

    def state(self):
        return schedule.load_state(self.dir)

    def record(self, cid):
        _, recs = self.state()
        return recs[cid]


# ---------------------------------------------------------------- parsing

class TestStateParsing(CourseCase):

    def test_roundtrip(self):
        meta, recs = self.state()
        self.assertEqual(set(recs), {"alpha", "beta", "gamma", "delta"})
        self.assertEqual(recs["alpha"]["interval"], 1)
        out = schedule.serialize_state(meta, recs)
        meta2, recs2 = schedule.parse_state(out)
        self.assertEqual(recs, recs2)
        self.assertEqual(meta, meta2)

    def test_duplicate_id_rejected(self):
        self.write_state([rec_line("alpha"), rec_line("alpha")])
        with self.assertRaises(schedule.FormatError):
            self.state()

    def test_label_not_positional(self):
        # field order permuted -> still parses by label
        line = ("- verify: quiz | id: omega | mastery: exposed"
                " | ceiling: solid | status: active | last: 2026-07-19"
                " | next: 2026-07-20 | fails: 0 | interval: 1"
                " | reprobe: - | note: hi")
        self.write_state([line])
        self.assertEqual(self.record("omega")["note"], "hi")

    def test_pipe_stripped_from_note_on_write(self):
        meta, recs = self.state()
        recs["alpha"]["note"] = "bad | pipe"
        text = schedule.serialize_state(meta, recs)
        _, recs2 = schedule.parse_state(text)
        self.assertNotIn("|", recs2["alpha"]["note"])

    def test_unknown_label_rejected(self):
        self.write_state([rec_line("alpha") + " | bogus: x"])
        with self.assertRaises(schedule.FormatError):
            self.state()


class TestGradeParsing(unittest.TestCase):

    def parse(self, text):
        return schedule.parse_log_grades(text)

    def test_grammar(self):
        tok, grades = self.parse(
            "session: 17r\n"
            "- grade: alpha | result: pass | note: clean\n"
            "- grade: beta | result: taught | note: \n")
        self.assertEqual(tok, "17r")
        self.assertEqual(grades[0], {"id": "alpha", "result": "pass",
                                     "note": "clean"})
        self.assertEqual(grades[1]["result"], "taught")

    def test_bad_grade_line_is_loud(self):
        with self.assertRaises(schedule.FormatError):
            self.parse("session: 3\n- grade: alpha passed fine\n")

    def test_bad_result_token(self):
        with self.assertRaises(schedule.FormatError):
            self.parse("session: 3\n- grade: a | result: aced | note:\n")

    def test_solid_is_not_writable(self):
        # the agent may never hand the script a 'solid' grade
        with self.assertRaises(schedule.FormatError):
            self.parse("session: 3\n- grade: a | result: solid | note:\n")

    def test_missing_session_line(self):
        with self.assertRaises(schedule.FormatError):
            self.parse("- grade: alpha | result: pass | note:\n")

    def test_session_token_grammar(self):
        for good in ("1", "17", "17r", "17r2"):
            self.assertTrue(schedule.valid_session_token(good), good)
        for bad in ("17x", "r17", "", "17.5", "17R"):
            self.assertFalse(schedule.valid_session_token(bad), bad)


# ------------------------------------------------------- transition table

class TestTransitions(CourseCase):

    def grades(self, *lines, session="3"):
        body = f"session: {session}\n" + "\n".join(lines) + "\n"
        p = self.dir / "log" / f"2026-07-20-{session}.md"
        p.write_text(body)
        return schedule.cmd_commit_grades(self.dir, p)

    def test_ladder(self):
        self.assertEqual(schedule.LADDER, [1, 3, 7, 16, 35, 90, 180])
        self.assertEqual(schedule.ladder_up(1), 3)
        self.assertEqual(schedule.ladder_up(180), 180)
        self.assertEqual(schedule.ladder_down(35), 16)
        self.assertEqual(schedule.ladder_down(1), 1)

    def test_taught(self):
        self.grades("- grade: beta | result: taught | note: intro")
        r = self.record("beta")
        self.assertEqual((r["status"], r["mastery"]), ("active", "exposed"))
        self.assertEqual(r["interval"], 1)
        self.assertEqual(r["next"], "2026-07-21")

    def test_pass_promotes_exposed_to_retrievable(self):
        self.grades("- grade: alpha | result: pass | note: ok")
        r = self.record("alpha")
        self.assertEqual(r["mastery"], "retrievable")
        self.assertEqual(r["interval"], 3)
        self.assertEqual(r["next"], "2026-07-23")
        self.assertEqual(r["fails"], 0)

    def test_fail_steps_back_one_never_to_zero(self):
        self.write_state([rec_line("alpha", mastery="retrievable",
                                   interval=16)])
        self.grades("- grade: alpha | result: fail | note: hit M1")
        r = self.record("alpha")
        self.assertEqual(r["interval"], 7)   # 16 -> 7, not 1
        self.assertEqual(r["fails"], 1)
        self.assertEqual(r["mastery"], "retrievable")  # band survives a lapse

    def test_three_fails_plateaus(self):
        self.write_state([rec_line("alpha", fails=2)])
        self.grades("- grade: alpha | result: fail | note: third miss")
        self.assertEqual(self.record("alpha")["status"], "plateaued")

    def test_pass_resets_fail_counter(self):
        self.write_state([rec_line("alpha", fails=2)])
        self.grades("- grade: alpha | result: pass | note: recovered")
        self.assertEqual(self.record("alpha")["fails"], 0)

    def test_ceiling_caps_band(self):
        self.write_state([rec_line("gamma", verify="use",
                                   ceiling="retrievable",
                                   mastery="retrievable", interval=35,
                                   reprobe="done")])
        self.grades("- grade: gamma | result: pass | note: applied well")
        self.assertEqual(self.record("gamma")["mastery"], "retrievable")

    def test_rubric_pass_sets_solid_pending_and_due_tomorrow(self):
        self.grades("- grade: alpha | result: rubric-pass | note: taught it")
        meta, _ = self.state()
        self.assertEqual(meta["solid-pending"], "alpha")
        r = self.record("alpha")
        self.assertEqual(r["reprobe"], "pending")
        self.assertEqual(r["next"], "2026-07-21")

    def test_reprobe_pass_completes_but_solid_needs_35(self):
        self.write_state([rec_line("alpha", mastery="retrievable",
                                   interval=3, reprobe="pending")],
                         header=STATE_HEADER.replace(
                             "solid-pending: none",
                             "solid-pending: alpha"))
        self.grades("- grade: alpha | result: pass | note: re-probe")
        meta, _ = self.state()
        r = self.record("alpha")
        self.assertEqual(r["reprobe"], "done")
        self.assertEqual(meta["solid-pending"], "none")
        self.assertEqual(r["mastery"], "retrievable")  # not yet solid

    def test_solid_awarded_at_35_pass_with_reprobe_done(self):
        self.write_state([rec_line("alpha", mastery="retrievable",
                                   interval=35, reprobe="done")])
        self.grades("- grade: alpha | result: pass | note: long-run")
        r = self.record("alpha")
        self.assertEqual(r["mastery"], "solid")
        self.assertEqual(r["interval"], 90)

    def test_no_solid_without_reprobe(self):
        self.write_state([rec_line("alpha", mastery="retrievable",
                                   interval=35, reprobe="-")])
        self.grades("- grade: alpha | result: pass | note: long-run")
        self.assertEqual(self.record("alpha")["mastery"], "retrievable")

    def test_rubric_fail_sets_repair_when_prereq_of_next_unit(self):
        # alpha is prereq of beta (same unit) — not next-unit: no repair.
        self.grades("- grade: alpha | result: rubric-fail | note: shaky")
        meta, _ = self.state()
        self.assertEqual(meta["repair-pending"], "none")
        # make gamma (unit 2) depend on alpha -> now repair fires
        self.write("domain-map.md",
                   MAP_MD.replace("### gamma\ndef: judgment concept\n"
                                  "prereqs: []",
                                  "### gamma\ndef: judgment concept\n"
                                  "prereqs: [alpha]"))
        self.grades("- grade: alpha | result: rubric-fail | note: shaky",
                    session="4")
        meta, _ = self.state()
        self.assertEqual(meta["repair-pending"], "alpha")


# --------------------------------------------------------- commit-grades

class TestCommitGrades(CourseCase):

    def logfile(self, body, name="2026-07-20-3.md"):
        p = self.dir / "log" / name
        p.write_text(body)
        return p

    def test_replay_is_noop(self):
        p = self.logfile("session: 3\n- grade: alpha | result: pass | note:\n")
        schedule.cmd_commit_grades(self.dir, p)
        first = self.record("alpha").copy()
        schedule.cmd_commit_grades(self.dir, p)  # replay
        self.assertEqual(self.record("alpha"), first)
        meta, _ = self.state()
        self.assertEqual(meta["committed-sessions"], ["3"])

    def test_fractional_sessions_are_distinct(self):
        p1 = self.logfile("session: 17r\n"
                          "- grade: alpha | result: pass | note:\n",
                          "2026-07-20-17r.md")
        schedule.cmd_commit_grades(self.dir, p1)
        p2 = self.logfile("session: 17\n"
                          "- grade: beta | result: taught | note:\n",
                          "2026-07-20-17.md")
        schedule.cmd_commit_grades(self.dir, p2)  # must NOT be blocked
        meta, _ = self.state()
        self.assertEqual(set(meta["committed-sessions"]), {"17", "17r"})
        self.assertEqual(self.record("beta")["status"], "active")

    def test_unknown_id_is_loud_and_nothing_applies(self):
        p = self.logfile("session: 3\n"
                         "- grade: alpha | result: pass | note:\n"
                         "- grade: nosuch | result: pass | note:\n")
        before = self.record("alpha").copy()
        with self.assertRaises(schedule.IntegrityError):
            schedule.cmd_commit_grades(self.dir, p)
        self.assertEqual(self.record("alpha"), before)  # all-or-nothing

    def test_guard_and_grades_written_atomically(self):
        p = self.logfile("session: 3\n- grade: alpha | result: pass | note:\n")
        schedule.cmd_commit_grades(self.dir, p)
        meta, recs = self.state()
        self.assertIn("3", meta["committed-sessions"])
        self.assertEqual(recs["alpha"]["interval"], 3)


# ------------------------------------------------------------------ queue

class TestQueue(CourseCase):

    def test_cap_oldest_first_and_exclusions(self):
        lines = [rec_line(f"c{i}", next=f"2026-07-{10+i:02d}")
                 for i in range(7)]                      # 7 due, oldest c0
        lines += [
            rec_line("later", next="2026-08-01"),        # not due
            rec_line("plat", status="plateaued"),        # excluded
            rec_line("gone", status="dropped"),          # excluded
            rec_line("raw", status="untaught", mastery="none",
                     last="-", next="-", interval=0),    # excluded
            rec_line("bg", verify="none"),               # excluded
        ]
        self.write_state(lines)
        ids = schedule.build_queue(self.dir)
        self.assertEqual(ids, [f"c{i}" for i in range(5)])

    def test_solid_pending_prepended_outside_cap(self):
        lines = [rec_line(f"c{i}", next=f"2026-07-{10+i:02d}")
                 for i in range(5)]
        lines.append(rec_line("key", next="2026-07-20", reprobe="pending"))
        self.write_state(lines, header=STATE_HEADER.replace(
            "solid-pending: none", "solid-pending: key"))
        ids = schedule.build_queue(self.dir)
        self.assertEqual(ids[0], "key")
        self.assertEqual(len(ids), 6)      # 1 pending + full cap of 5

    def test_queue_file_written(self):
        schedule.cmd_queue(self.dir)
        text = (self.dir / "review-queue.md").read_text()
        self.assertIn("alpha", text)
        self.assertIn("GENERATED", text)


# ----------------------------------------------- seed / set-verify / misc

class TestSeedAndVerbs(CourseCase):

    def test_seed_upserts_idempotently(self):
        schedule.cmd_seed(self.dir, "beta", "retrievable")
        schedule.cmd_seed(self.dir, "beta", "retrievable")  # no dup, no drift
        _, recs = self.state()
        self.assertEqual(len([r for r in recs if r == "beta"]), 1)
        r = recs["beta"]
        self.assertEqual((r["mastery"], r["status"]),
                         ("retrievable", "active"))
        self.assertEqual(r["next"], "2026-07-21")

    def test_seed_rejects_unknown_concept(self):
        with self.assertRaises(schedule.IntegrityError):
            schedule.cmd_seed(self.dir, "nosuch", "exposed")

    def test_set_verify(self):
        schedule.cmd_set_verify(self.dir, "alpha", "none")
        self.assertEqual(self.record("alpha")["verify"], "none")
        self.assertNotIn("alpha", schedule.build_queue(self.dir))


# ---------------------------------------------------------------- reprune

class TestReprune(CourseCase):

    def test_drop_updates_state_and_plan(self):
        schedule.cmd_reprune(self.dir, drop=["beta"])
        self.assertEqual(self.record("beta")["status"], "dropped")
        self.assertNotIn("beta", (self.dir / "plan.md").read_text())
        self.assertNotIn("beta", schedule.build_queue(self.dir))

    def test_refuses_to_drop_prereq_of_kept(self):
        with self.assertRaises(schedule.IntegrityError):
            schedule.cmd_reprune(self.dir, drop=["alpha"])  # beta needs it


# ------------------------------------------------------------------ check

class TestCheck(CourseCase):

    def test_clean_course_passes(self):
        schedule.cmd_check(self.dir)  # no raise

    def test_cycle_detected(self):
        self.write("domain-map.md", MAP_MD.replace(
            "### alpha\ndef: first concept\nprereqs: []",
            "### alpha\ndef: first concept\nprereqs: [beta]"))
        with self.assertRaises(schedule.IntegrityError):
            schedule.cmd_check(self.dir)

    def test_erratum_remove_edge_heals_cycle(self):
        broken = MAP_MD.replace(
            "### alpha\ndef: first concept\nprereqs: []",
            "### alpha\ndef: first concept\nprereqs: [beta]")
        broken += "\nerratum 2026-07-20: remove-edge beta -> alpha\n"
        self.write("domain-map.md", broken)
        schedule.cmd_check(self.dir)  # healed, no raise

    def test_state_missing_concept_detected(self):
        self.write_state([rec_line("alpha")])   # beta/gamma/delta missing
        with self.assertRaises(schedule.IntegrityError):
            schedule.cmd_check(self.dir)

    def test_plan_referencing_unknown_id_detected(self):
        self.write("plan.md", PLAN_MD.replace("[alpha, beta]",
                                              "[alpha, beta, ghost]"))
        with self.assertRaises(schedule.IntegrityError):
            schedule.cmd_check(self.dir)

    def test_dropped_is_allowed_asymmetry(self):
        schedule.cmd_reprune(self.dir, drop=["beta"])
        schedule.cmd_check(self.dir)  # dropped-in-state, absent-in-plan: OK


# ----------------------------------------------------------------- report

class TestReport(CourseCase):

    def test_report_mentions_plateaued_and_due(self):
        self.write_state([
            rec_line("alpha"),
            rec_line("beta", status="plateaued"),
            rec_line("gamma", verify="use", ceiling="retrievable",
                     next="2026-07-01"),
            rec_line("delta", verify="none", mastery="none",
                     status="untaught", last="-", next="-", interval=0),
        ])
        out = schedule.cmd_report(self.dir)
        self.assertIn("plateaued", out)
        self.assertIn("beta", out)
        self.assertIn("due", out)


# ---------------------------------------------------------------- recover

def git(*args, cwd):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                    *args], cwd=cwd, check=True, capture_output=True)


class TestRecover(CourseCase):

    def setUp(self):
        super().setUp()
        git("init", "-q", cwd=self.dir)
        git("add", "-A", cwd=self.dir)
        git("commit", "-qm", "base", cwd=self.dir)

    def sentinel(self, session="3", age_hours=0):
        import datetime as dt
        ts = (dt.datetime(2026, 7, 20, 12, 0)
              - dt.timedelta(hours=age_hours)).isoformat()
        (self.dir / ".session-inprogress").write_text(
            f"session: {session}\nstarted: {ts}\n")

    def test_clean_tree_no_sentinel_is_ok(self):
        self.assertEqual(schedule.cmd_recover(self.dir), "ok")

    def test_fresh_sentinel_means_locked_never_reset(self):
        self.sentinel(age_hours=0)
        (self.dir / "plan.md").write_text("dirty")
        self.assertEqual(schedule.cmd_recover(self.dir), "locked")
        # nothing was destroyed
        self.assertEqual((self.dir / "plan.md").read_text(), "dirty")

    def test_stale_sentinel_with_grade_log_replays_and_commits(self):
        # a completed-but-uncommitted close: grades log exists
        (self.dir / "log" / "2026-07-20-3.md").write_text(
            "session: 3\n- grade: alpha | result: pass | note:\n")
        self.sentinel(session="3", age_hours=6)
        self.assertEqual(schedule.cmd_recover(self.dir), "replayed")
        self.assertFalse((self.dir / ".session-inprogress").exists())
        # grades applied and committed
        self.assertEqual(self.record("alpha")["interval"], 3)
        out = subprocess.run(["git", "status", "--porcelain"],
                             cwd=self.dir, capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "")

    def test_stale_sentinel_without_log_resets(self):
        self.sentinel(session="3", age_hours=6)
        (self.dir / "plan.md").write_text("half-written garbage")
        self.assertEqual(schedule.cmd_recover(self.dir), "reset")
        self.assertIn("course-status: active",
                      (self.dir / "plan.md").read_text())
        self.assertFalse((self.dir / ".session-inprogress").exists())


if __name__ == "__main__":
    unittest.main()
