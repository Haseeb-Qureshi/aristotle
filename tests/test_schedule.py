"""Tests for the Aristotle deterministic core.

Every defect the round-3 review panel proved by execution has a test here.
Tests assert BEHAVIOUR — what a course does — rather than parser internals:
a change that alters what a learner experiences must fail something.
"""

import datetime as dt
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import schedule as S  # noqa: E402

TODAY = "2026-07-21"
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "schedule.py"

MAP_MD = """\
topic: testing
terminal-task: ship a course that survives a stranger
research: no
timezone: America/Los_Angeles
sessions: 10

### alpha
def: the first thing
prereqs: []
verify: quiz
threshold: no
misconceptions:
  M1: the common wrong model
  M2: the other one

### beta
def: the second thing
prereqs: [alpha]
verify: quiz
threshold: no

### gamma
def: the third thing
prereqs: [alpha]
verify: use
threshold: yes
misconceptions:
  M1: gamma's wrong model

### delta
def: the fourth thing
prereqs: [beta]
verify: quiz
threshold: no

## Controversies
Some schools say prereqs: [nonsense] and verify: garbage.

## Sources
- something

## Errata
"""

PLAN_MD = """\
course-status: active
next-session: 2/10
cadence: 3
sessions-done: 1
last-attended: 2026-07-20
re-entry-pending: no

## Unit 1: Why does alpha matter?
sessions: 3
concepts: [alpha, beta]
keystones: [alpha]
artifact-milestone: none
status: in-progress

## Unit 2: What is gamma for?
sessions: 3
concepts: [gamma, delta]
keystones: [gamma]
artifact-milestone: draft the thing
status: untouched
"""

STATE_MD = """\
<!-- aristotle:state
committed-sessions: 1
repair-pending: none
-->
<!-- a format comment in the body must be tolerated -->
- id: alpha | verify: quiz | status: active | last: 2026-07-20 | \
next: 2026-07-21 | interval: 1 | fails: 0 | note: taught session 1
- id: beta | verify: quiz | status: untaught | last: - | next: - | \
interval: 0 | fails: 0 | note:
- id: gamma | verify: use | status: untaught | last: - | next: - | \
interval: 0 | fails: 0 | note:
- id: delta | verify: quiz | status: untaught | last: - | next: - | \
interval: 0 | fails: 0 | note:
"""

ASSETS_U1 = """\
<!-- aristotle:assets unit: 01 -->

## concept: alpha
- quiz: What does alpha name? | a: the first thing | distractor: M1
- example: worked | Given x, alpha yields y, because the rule says so.
- apply: point at an alpha in this transcript

## concept: beta
- quiz: What does beta name? | a: the second thing | distractor: people mix it with alpha

## rubric: alpha
- claim: alpha comes before beta
- avoid: M1

## interleaved
- problem: which of the two applies here, and why? | concepts: alpha, beta
"""

ASSETS_U2 = """\
<!-- aristotle:assets unit: 02 -->

## concept: gamma
- apply: use gamma on the case below

## concept: delta
- quiz: What does delta name? | a: the fourth thing

## rubric: gamma
- claim: gamma is applied, never recited
- avoid: M1

## interleaved
- problem: first mixed problem | concepts: alpha, gamma
- problem: second mixed problem | concepts: beta, delta
"""


def log_text(session, *grades, extra="", taught=None):
    """A well-formed session log. Every 'taught' grade gets its coverage
    line under '## taught' — close refuses the log without one. Pass
    `taught` to write that section by hand (or leave it old-format)."""
    body = "\n".join(
        f"- grade: {cid} | result: {res} | note: {note}"
        for cid, res, note in grades)
    if taught is None:
        taught = "\n".join(f"- {cid}: presented the core of {cid}"
                           for cid, res, _ in grades if res == "taught")
    return (f"session: {session}\n\n## taught\n{taught or 'stuff'}\n\n"
            f"## grades\n{body}\n\n## open question\n{extra}\n")


class CourseCase(unittest.TestCase):
    """A valid mid-flight course in a temp dir."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="aristotle-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        (self.dir / "domain-map.md").write_text(MAP_MD, encoding="utf-8")
        (self.dir / "plan.md").write_text(PLAN_MD, encoding="utf-8")
        (self.dir / "knowledge-state.md").write_text(STATE_MD,
                                                     encoding="utf-8")
        (self.dir / "assets").mkdir()
        (self.dir / "assets" / "unit-01.md").write_text(ASSETS_U1,
                                                        encoding="utf-8")
        (self.dir / "log").mkdir()
        os.environ["ARISTOTLE_TODAY"] = TODAY
        self.addCleanup(os.environ.pop, "ARISTOTLE_TODAY", None)
        os.environ["ARISTOTLE_REVIEW_PLAN"] = "open:2"
        self.addCleanup(os.environ.pop, "ARISTOTLE_REVIEW_PLAN", None)
        self.addCleanup(os.environ.pop, "ARISTOTLE_NOW", None)

    # helpers -----------------------------------------------------------
    def state(self):
        return S.load_state(self.dir)

    def rec(self, cid):
        return self.state()[1][cid]

    def write_log(self, name, text):
        p = self.dir / "log" / name
        p.write_text(text, encoding="utf-8")
        return p

    def set_record(self, cid, **kw):
        meta, recs = self.state()
        recs[cid].update(kw)
        S.save_state(self.dir, meta, recs)

    def set_meta(self, **kw):
        meta, recs = self.state()
        meta.update(kw)
        S.save_state(self.dir, meta, recs)

    def add_u2_assets(self):
        (self.dir / "assets" / "unit-02.md").write_text(ASSETS_U2,
                                                        encoding="utf-8")

    def git_init(self):
        S._ensure_repo(self.dir)

    def settle(self, *keystones):
        """Make every concept taught and give each named keystone a
        committed teach-back, so an ended unit owes nothing and dispatch
        reaches the slot type the test is about (not a catch-up)."""
        for cid in ("alpha", "beta", "gamma", "delta"):
            if self.rec(cid)["status"] == "untaught":
                self.set_record(cid, status="active", next="2026-08-30")
        for k in keystones:
            self.write_log(f"2026-07-19-{k}.md",
                           log_text("1", (k, "rubric-pass", "x")))

    def cli(self, *args, env=None):
        e = dict(os.environ)
        e.update(env or {})
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--course", str(self.dir), *args],
            capture_output=True, text=True, cwd=self.dir, env=e)


# ======================================================== state parsing

class TestStateParsing(CourseCase):

    def test_roundtrip_is_stable(self):
        meta, recs = self.state()
        S.save_state(self.dir, meta, recs)
        meta2, recs2 = self.state()
        self.assertEqual(recs, recs2)
        self.assertEqual(meta["committed-sessions"],
                         meta2["committed-sessions"])

    def test_body_comments_are_tolerated(self):
        self.assertIn("alpha", self.state()[1])

    def test_missing_header_is_loud(self):
        (self.dir / "knowledge-state.md").write_text("- id: a\n",
                                                     encoding="utf-8")
        with self.assertRaises(S.FormatError):
            self.state()

    def test_duplicate_id_is_loud(self):
        p = self.dir / "knowledge-state.md"
        dup = [ln for ln in STATE_MD.splitlines() if ln.startswith("- id: beta")]
        p.write_text(p.read_text(encoding="utf-8") + dup[0] + "\n",
                     encoding="utf-8")
        with self.assertRaisesRegex(S.FormatError, "duplicate"):
            self.state()

    def test_bad_status_value_is_rejected_on_load(self):
        p = self.dir / "knowledge-state.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "status: active", "status: Active"), encoding="utf-8")
        with self.assertRaisesRegex(S.FormatError, "status"):
            self.state()

    def test_bad_verify_value_is_rejected_on_load(self):
        p = self.dir / "knowledge-state.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "verify: quiz", "verify: Quiz", 1), encoding="utf-8")
        with self.assertRaisesRegex(S.FormatError, "verify"):
            self.state()

    def test_bad_date_is_rejected_on_load(self):
        p = self.dir / "knowledge-state.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "next: 2026-07-21", "next: 2026-7-21"), encoding="utf-8")
        with self.assertRaisesRegex(S.FormatError, "YYYY-MM-DD"):
            self.state()

    def test_negative_int_is_rejected_on_load(self):
        p = self.dir / "knowledge-state.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "fails: 0", "fails: -5", 1), encoding="utf-8")
        with self.assertRaises(S.FormatError):
            self.state()

    def test_pipe_in_note_is_scrubbed_not_corrupting(self):
        self.set_record("alpha", note="said a | b")
        self.assertNotIn("|", self.rec("alpha")["note"])

    def test_save_is_atomic(self):
        """A crash mid-serialize must leave the old file byte-identical."""
        before = (self.dir / "knowledge-state.md").read_bytes()
        meta, recs = self.state()
        real = S.serialize_state

        def boom(*a, **k):
            raise RuntimeError("crash")
        S.serialize_state = boom
        try:
            with self.assertRaises(RuntimeError):
                S.save_state(self.dir, meta, recs)
        finally:
            S.serialize_state = real
        self.assertEqual(before,
                         (self.dir / "knowledge-state.md").read_bytes())
        self.assertFalse(list(self.dir.glob("*.tmp")))

    def test_utf8_survives_a_c_locale(self):
        self.git_init()
        self.write_log("2026-07-21-2.md",
                       log_text("2", ("alpha", "pass", "said yes — hit M1")))
        r = self.cli("commit-grades", "log/2026-07-21-2.md",
                     env={"LC_ALL": "C", "LANG": "C"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("—", self.rec("alpha")["note"])


# ======================================================== grade parsing

class TestGradeParsing(CourseCase):

    def test_basic(self):
        tok, g = S.parse_log_grades(log_text("4", ("alpha", "pass", "clean")))
        self.assertEqual(tok, "4")
        self.assertEqual(g, [{"id": "alpha", "result": "pass",
                              "note": "clean"}])

    def test_malformed_is_loud(self):
        with self.assertRaises(S.FormatError):
            S.parse_log_grades("session: 4\n## grades\n- grade: alpha pass\n")

    def test_bold_grade_line_is_loud_not_silent(self):
        with self.assertRaises(S.FormatError):
            S.parse_log_grades(
                "session: 4\n## grades\n- **grade:** alpha | result: pass\n")

    def test_endash_bullet_is_loud_not_silent(self):
        with self.assertRaises(S.FormatError):
            S.parse_log_grades(
                "session: 4\n## grades\n"
                "– grade: alpha | result: pass | note: x\n")

    def test_invalid_result_is_loud(self):
        with self.assertRaises(S.FormatError):
            S.parse_log_grades(log_text("4", ("alpha", "solid", "nope")))

    def test_duplicate_grade_for_one_concept_is_rejected(self):
        """The same-session re-probe must not silently erase the fail."""
        with self.assertRaisesRegex(S.FormatError, "two grade lines"):
            S.parse_log_grades(log_text(
                "4", ("alpha", "fail", "missed"), ("alpha", "pass", "got it")))

    def test_grade_line_in_prose_does_not_count(self):
        text = log_text("4", ("alpha", "pass", "ok"),
                        extra="for example: - grade: beta | result: fail "
                              "| note: sample")
        _, g = S.parse_log_grades(text)
        self.assertEqual([x["id"] for x in g], ["alpha"])

    def test_no_session_line_is_loud(self):
        with self.assertRaises(S.FormatError):
            S.parse_log_grades("## grades\n- grade: a | result: pass | note: x")

    def test_bad_token_is_loud(self):
        with self.assertRaises(S.FormatError):
            S.parse_log_grades(log_text("2/10", ("alpha", "pass", "x")))

    def test_crlf(self):
        tok, g = S.parse_log_grades(
            log_text("4", ("alpha", "pass", "x")).replace("\n", "\r\n"))
        self.assertEqual((tok, len(g)), ("4", 1))

    def test_tokens_are_string_keyed(self):
        for t in ("17", "17r", "17r2"):
            self.assertTrue(S.valid_session_token(t))
        for t in ("2/10", "03x", "r4", ""):
            self.assertFalse(S.valid_session_token(t))


# ==================================================== transition table

class TestTransitions(CourseCase):

    def grade(self, cid, result, needs=frozenset()):
        meta, recs = self.state()
        S._apply_grade(recs[cid], {"id": cid, "result": result, "note": ""},
                       meta, dt.date.fromisoformat(TODAY), needs)
        S.save_state(self.dir, meta, recs)
        return meta, recs

    def test_taught_activates_and_schedules_tomorrow(self):
        self.grade("beta", "taught")
        r = self.rec("beta")
        self.assertEqual((r["status"], r["interval"], r["next"]),
                         ("active", 1, "2026-07-22"))

    def grade_on(self, cid, result, day, needs=frozenset()):
        meta, recs = self.state()
        S._apply_grade(recs[cid], {"id": cid, "result": result, "note": ""},
                       meta, dt.date.fromisoformat(day), needs)
        S.save_state(self.dir, meta, recs)

    def test_pass_climbs_the_ladder(self):
        self.grade("alpha", "pass")
        self.assertEqual(self.rec("alpha")["interval"], 3)

    def test_an_early_pass_keeps_the_rung_and_restarts_the_clock(self):
        """The pilot climbed 7->16->35 on probes 5 and 1 days apart. A
        pass may climb only when the elapsed gap DEMONSTRATED the current
        rung; early success is a clock restart, not evidence."""
        self.set_record("alpha", interval=16, last="2026-07-20")
        self.grade("alpha", "pass")               # 1 day after last
        r = self.rec("alpha")
        self.assertEqual(r["interval"], 16)       # rung kept, not 35
        self.assertEqual(r["next"], "2026-08-06")  # clock restarted

    def test_an_on_time_pass_still_climbs(self):
        self.set_record("alpha", interval=16, last="2026-07-05")
        self.grade("alpha", "pass")               # exactly 16 days later
        self.assertEqual(self.rec("alpha")["interval"], 35)

    def test_a_late_pass_climbs_one_rung_only(self):
        self.set_record("alpha", interval=7, last="2026-06-01")
        self.grade("alpha", "pass")               # 50 days: still one rung
        self.assertEqual(self.rec("alpha")["interval"], 16)

    def test_an_early_fail_still_steps_down(self):
        """The asymmetry is deliberate: failing one day after the last
        retrieval is WORSE news than failing on schedule."""
        self.set_record("alpha", interval=16, last="2026-07-20")
        self.grade("alpha", "fail")
        self.assertEqual(self.rec("alpha")["interval"], 7)

    def test_back_to_back_reviews_cannot_inflate_the_ladder(self):
        """Replay of the pilot's terminal pair: two passes on consecutive
        days must leave the rung where the last EARNED climb put it."""
        self.set_record("alpha", interval=7, last="2026-07-14")
        self.grade_on("alpha", "pass", "2026-07-19")   # 5 of 7 days: early
        self.grade_on("alpha", "pass", "2026-07-20")   # next day: early
        r = self.rec("alpha")
        self.assertEqual(r["interval"], 7)
        self.assertEqual(r["next"], "2026-07-27")

    def test_fail_steps_back_one_not_to_zero(self):
        self.set_record("alpha", interval=16)
        self.grade("alpha", "fail")
        self.assertEqual(self.rec("alpha")["interval"], 7)
        self.set_record("alpha", interval=1)
        self.grade("alpha", "fail")
        self.assertEqual(self.rec("alpha")["interval"], 1)

    def test_pass_resets_the_fail_counter(self):
        self.set_record("alpha", fails=2)
        self.grade("alpha", "pass")
        self.assertEqual(self.rec("alpha")["fails"], 0)

    def test_three_fails_plateaus(self):
        for _ in range(3):
            self.grade("alpha", "fail")
        self.assertEqual(self.rec("alpha")["status"], "plateaued")

    def test_plateau_has_an_exit_via_taught(self):
        """checkpoint.md's 'keep trying' verdict must really re-enter it."""
        for _ in range(3):
            self.grade("alpha", "fail")
        self.assertNotIn("alpha", S.build_queue(self.dir))
        self.grade("alpha", "taught")
        r = self.rec("alpha")
        self.assertEqual((r["status"], r["fails"]), ("active", 0))
        self.set_record("alpha", next=TODAY)   # when its day comes round
        self.assertIn("alpha", S.build_queue(self.dir))

    def test_plateau_has_an_exit_via_pass(self):
        """checkpoint.md's 'count it' verdict must really count it."""
        for _ in range(3):
            self.grade("alpha", "fail")
        self.grade("alpha", "pass")
        self.assertEqual(self.rec("alpha")["status"], "active")

    def test_pass_on_an_untaught_row_makes_it_visible(self):
        """A pass is evidence of contact; the row must not stay a ghost."""
        self.grade("beta", "pass")
        r = self.rec("beta")
        self.assertEqual((r["status"], r["interval"]), ("active", 1))
        self.set_record("beta", next=TODAY)
        self.assertIn("beta", S.build_queue(self.dir))

    def test_fail_on_an_untaught_row_activates_it(self):
        self.grade("beta", "fail")
        self.assertEqual(self.rec("beta")["status"], "active")

    def test_rubric_pass_behaves_as_a_pass(self):
        self.grade("alpha", "rubric-pass")
        self.assertEqual(self.rec("alpha")["interval"], 3)

    def test_rubric_fail_actually_reschedules(self):
        """The hardest assessment failing must change the schedule."""
        self.set_record("alpha", interval=16)
        self.grade("alpha", "rubric-fail")
        r = self.rec("alpha")
        self.assertEqual((r["interval"], r["fails"], r["next"]),
                         (7, 1, "2026-07-28"))

    def test_rubric_fail_sets_repair_only_for_next_unit_prereqs(self):
        meta, _ = self.grade("alpha", "rubric-fail", needs={"alpha"})
        self.assertEqual(meta["repair-pending"], "alpha")
        self.set_meta(**{"repair-pending": "none"})
        meta, _ = self.grade("beta", "rubric-fail", needs={"alpha"})
        self.assertEqual(meta["repair-pending"], "none")

    def test_repair_flag_is_cleared_by_a_pass(self):
        self.set_meta(**{"repair-pending": "alpha"})
        meta, _ = self.grade("alpha", "pass")
        self.assertEqual(meta["repair-pending"], "none")

    def test_repair_flag_is_cleared_by_a_fail_which_plateaus(self):
        self.set_meta(**{"repair-pending": "alpha"})
        meta, _ = self.grade("alpha", "fail")
        self.assertEqual(meta["repair-pending"], "none")
        self.assertEqual(self.rec("alpha")["status"], "plateaued")

    def test_a_repair_never_re_arms_itself(self):
        self.set_meta(**{"repair-pending": "alpha"})
        meta, _ = self.grade("alpha", "rubric-fail", needs={"alpha"})
        self.assertEqual(meta["repair-pending"], "none")

    def test_ladder_bounds(self):
        self.assertEqual(S.ladder_up(180), 180)
        self.assertEqual(S.ladder_down(1), 1)
        self.assertEqual(S.ladder_up(0), 1)

    def test_band_is_derived_not_stored(self):
        self.assertNotIn("mastery", S.RECORD_FIELDS)
        self.set_record("alpha", interval=35, fails=0)
        self.assertEqual(S.band(self.rec("alpha")), "solid")
        self.set_record("alpha", interval=7)
        self.assertEqual(S.band(self.rec("alpha")), "retrievable")
        self.set_record("alpha", interval=1)
        self.assertEqual(S.band(self.rec("alpha")), "exposed")


# ====================================================== commit-grades

class TestCommitGrades(CourseCase):

    def test_applies_and_records_the_token(self):
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "pass", "clean")))
        self.assertEqual(S.cmd_commit_grades(self.dir, p), "applied")
        self.assertIn("2", self.state()[0]["committed-sessions"])

    def test_replay_is_a_noop(self):
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "pass", "clean")))
        S.cmd_commit_grades(self.dir, p)
        iv = self.rec("alpha")["interval"]
        self.assertEqual(S.cmd_commit_grades(self.dir, p), "noop")
        self.assertEqual(self.rec("alpha")["interval"], iv)

    def test_unknown_id_applies_nothing(self):
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "pass", "x"),
                                    ("nope", "pass", "y")))
        with self.assertRaises(S.IntegrityError):
            S.cmd_commit_grades(self.dir, p)
        self.assertEqual(self.rec("alpha")["interval"], 1)
        self.assertNotIn("2", self.state()[0]["committed-sessions"])

    def test_note_is_stored(self):
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "fail", "hit M1")))
        S.cmd_commit_grades(self.dir, p)
        self.assertEqual(self.rec("alpha")["note"], "hit M1")

    def test_fractional_tokens_are_distinct(self):
        a = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "pass", "x")))
        b = self.write_log("2026-07-21-2r.md",
                           log_text("2r", ("beta", "taught", "y")))
        self.assertEqual(S.cmd_commit_grades(self.dir, a), "applied")
        self.assertEqual(S.cmd_commit_grades(self.dir, b), "applied")
        self.assertEqual(self.rec("beta")["status"], "active")


# ================================================================ queue

class TestQueue(CourseCase):

    def due(self, cid, days_ago=1, **kw):
        d = (dt.date.fromisoformat(TODAY) - dt.timedelta(days_ago)).isoformat()
        self.set_record(cid, status="active", next=d, **kw)

    def test_untaught_is_excluded(self):
        self.due("beta")
        self.set_record("beta", status="untaught")
        self.assertNotIn("beta", S.build_queue(self.dir))

    def test_verify_none_is_excluded(self):
        self.due("beta")
        self.set_record("beta", verify="none")
        self.assertNotIn("beta", S.build_queue(self.dir))

    def test_dropped_is_excluded(self):
        self.due("beta")
        self.set_record("beta", status="dropped")
        self.assertNotIn("beta", S.build_queue(self.dir))

    def test_plateaued_is_excluded(self):
        self.due("beta")
        self.set_record("beta", status="plateaued")
        self.assertNotIn("beta", S.build_queue(self.dir))

    def test_not_yet_due_is_excluded(self):
        self.set_record("beta", status="active", next="2099-01-01")
        self.assertNotIn("beta", S.build_queue(self.dir))

    def test_due_and_active_is_included(self):
        self.due("beta")
        self.assertIn("beta", S.build_queue(self.dir))

    def test_cap_is_respected(self):
        for cid in ("beta", "gamma", "delta"):
            self.due(cid)
        self.assertEqual(len(S.build_queue(self.dir, cap=2)), 2)

    def test_fresh_material_outranks_a_stale_backlog(self):
        """A concept taught yesterday must not be crowded out by an
        old, long-interval item that merely came due earlier."""
        self.due("beta", days_ago=40, interval=35)
        self.due("delta", days_ago=1, interval=1)
        self.assertEqual(S.build_queue(self.dir, cap=1), ["delta"])

    def test_terminal_queue_ignores_due_dates_and_favours_the_weakest(self):
        self.set_record("beta", status="active", next="2099-01-01",
                        interval=35, fails=0)
        self.set_record("gamma", status="active", next="2099-01-01",
                        interval=1, fails=2)
        q = S.build_queue(self.dir, cap=5, terminal=True)
        self.assertEqual(q[0], "gamma")
        self.assertIn("beta", q)

    def test_queue_file_records_the_rolled_forward_count(self):
        for cid in ("beta", "gamma", "delta"):
            self.due(cid)
        S.cmd_queue(self.dir, cap=1)
        text = (self.dir / "review-queue.md").read_text(encoding="utf-8")
        self.assertIn("rolled-forward: 3", text)


# ======================================================= seed / verify

class TestSeedAndVerbs(CourseCase):

    def test_seed_is_idempotent(self):
        S.cmd_seed(self.dir, "beta", "exposed")
        S.cmd_seed(self.dir, "beta", "exposed")
        self.assertEqual(len(self.state()[1]), 4)

    def test_seed_carries_placement_evidence_into_the_schedule(self):
        """Something they already retrieve must not be reviewed tomorrow."""
        S.cmd_seed(self.dir, "beta", "retrievable")
        r = self.rec("beta")
        self.assertEqual((r["interval"], r["next"]), (7, "2026-07-28"))

    def test_seed_none_leaves_it_untaught(self):
        S.cmd_seed(self.dir, "delta", "none")
        self.assertEqual(self.rec("delta")["status"], "untaught")

    def test_seed_rejects_unknown_concept(self):
        with self.assertRaises(S.IntegrityError):
            S.cmd_seed(self.dir, "nope", "exposed")

    def test_set_verify_none_drops_it_from_the_stuck_list(self):
        self.set_record("alpha", status="plateaued")
        S.cmd_set_verify(self.dir, "alpha", "none")
        self.assertEqual(self.rec("alpha")["status"], "dropped")
        self.assertNotIn("alpha", S.cmd_report(self.dir).split("stuck")[1])


# ============================================================== reprune

class TestReprune(CourseCase):

    def test_drops_and_excludes_from_queue(self):
        self.set_record("delta", status="active", next="2026-07-01")
        S.cmd_reprune(self.dir, ["delta"])
        self.assertEqual(self.rec("delta")["status"], "dropped")
        self.assertNotIn("delta", S.build_queue(self.dir))

    def test_refuses_to_orphan_a_prerequisite(self):
        with self.assertRaisesRegex(S.IntegrityError, "prerequisite"):
            S.cmd_reprune(self.dir, ["alpha"])

    def test_refuses_to_drop_a_threshold_concept(self):
        with self.assertRaisesRegex(S.IntegrityError, "threshold"):
            S.cmd_reprune(self.dir, ["gamma"])

    def test_strips_the_id_from_plan_lists(self):
        S.cmd_reprune(self.dir, ["delta"])
        self.assertNotIn("delta",
                         (self.dir / "plan.md").read_text(encoding="utf-8"))

    def test_clears_a_repair_pointing_at_a_dropped_concept(self):
        self.set_meta(**{"repair-pending": "delta"})
        S.cmd_reprune(self.dir, ["delta"])
        self.assertEqual(self.state()[0]["repair-pending"], "none")

    def test_unknown_id_is_loud(self):
        with self.assertRaises(S.IntegrityError):
            S.cmd_reprune(self.dir, ["nope"])


# =============================================================== assets

class TestAssets(CourseCase):

    def check_assets(self, text, unit_num=1):
        _, units = S.parse_plan(self.dir)
        unit = [u for u in units if u["num"] == unit_num][0]
        S.validate_assets(unit, S.parse_assets(text), S.parse_map(self.dir),
                          where="t", first_unit=(unit_num == 1))

    def test_good_assets_pass(self):
        self.check_assets(ASSETS_U1)

    def test_all_todo_assets_are_rejected(self):
        """SKILL.md claims check rejects placeholder work. Make it true."""
        junk = textwrap.dedent("""\
            ## concept: alpha
            - quiz: TODO | a: TODO | distractor: M1
            - example: worked | TODO
            ## concept: beta
            - quiz: TODO | a: TODO
            ## rubric: alpha
            - claim: TODO
            - avoid: M1
            ## interleaved
            - problem: TODO | concepts: alpha
            - problem: TODO | concepts: beta
            """)
        with self.assertRaises(S.IntegrityError):
            self.check_assets(junk)

    def test_empty_fields_are_rejected(self):
        junk = textwrap.dedent("""\
            ## concept: alpha
            - quiz:  | a:
            - example: worked
            ## concept: beta
            - quiz: ? | a: .
            ## rubric: alpha
            - claim:
            - avoid: M1
            ## interleaved
            - problem:
            - problem:
            - problem:
            """)
        with self.assertRaises((S.IntegrityError, S.FormatError)):
            self.check_assets(junk)

    def test_interleaved_must_name_concepts(self):
        text = ASSETS_U1.replace(
            "- problem: which of the two applies here, and why? | "
            "concepts: alpha, beta",
            "- problem: a real problem with no concept list")
        with self.assertRaisesRegex(S.IntegrityError, "interleaved"):
            self.check_assets(text)

    def test_interleaved_concepts_must_exist(self):
        text = ASSETS_U1.replace("concepts: alpha, beta",
                                 "concepts: alpha, kumquat")
        with self.assertRaisesRegex(S.IntegrityError, "unknown concept"):
            self.check_assets(text)

    def test_keystone_without_map_misconceptions_needs_no_avoid(self):
        """The rule that made the bundled example unauthorable."""
        p = self.dir / "domain-map.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "threshold: yes\nmisconceptions:\n  M1: gamma's wrong model",
            "threshold: yes"), encoding="utf-8")
        text = textwrap.dedent("""\
            ## concept: gamma
            - apply: use gamma here on a real case
            ## concept: delta
            - quiz: what does delta name? | a: the fourth thing
            ## rubric: gamma
            - claim: gamma is applied, not recited
            ## interleaved
            - problem: a real one | concepts: alpha
            - problem: another real one | concepts: beta
            """)
        self.check_assets(text, unit_num=2)

    def test_mn_shaped_distractor_must_resolve(self):
        text = ASSETS_U1.replace("distractor: M1", "distractor: M9")
        with self.assertRaisesRegex(S.IntegrityError, "M9"):
            self.check_assets(text)

    def test_free_text_distractor_is_allowed(self):
        text = ASSETS_U1.replace("distractor: M1",
                                 "distractor: thinks it is a synonym")
        self.check_assets(text)

    def test_wrapped_values_are_joined_not_truncated(self):
        text = ASSETS_U1.replace(
            "- example: worked | Given x, alpha yields y, because the rule "
            "says so.",
            "- example: worked | Given x, alpha yields y,\n"
            "  because the rule says so and the second line matters.")
        parsed = S.parse_assets(text)
        self.assertIn("second line matters",
                      parsed["concepts"]["alpha"]["example"]["worked"])
        self.check_assets(text)

    def test_wrapped_quiz_answer_does_not_hard_fail(self):
        text = ASSETS_U1.replace(
            "- quiz: What does alpha name? | a: the first thing | "
            "distractor: M1",
            "- quiz: What does alpha name? | a: the first thing,\n"
            "  spelled out at length | distractor: M1")
        self.check_assets(text)

    def test_verify_use_needs_an_apply_prompt(self):
        text = ASSETS_U2.replace("- apply: use gamma on the case below", "")
        with self.assertRaisesRegex(S.IntegrityError, "apply"):
            self.check_assets(text, unit_num=2)

    def test_quiz_concept_does_not_require_a_worked_example(self):
        """A definitional concept has no procedure to work through."""
        text = textwrap.dedent("""\
            ## concept: alpha
            - quiz: What does alpha name? | a: the first thing
            ## concept: beta
            - quiz: What does beta name? | a: the second thing
            ## rubric: alpha
            - claim: alpha comes before beta
            - avoid: M1
            ## interleaved
            - problem: a real mixed problem | concepts: alpha, beta
            """)
        self.check_assets(text)

    def test_html_comments_do_not_break_sections(self):
        self.check_assets("<!-- ## notes: not a section -->\n" + ASSETS_U1)

    def test_unknown_section_is_loud(self):
        with self.assertRaises(S.FormatError):
            S.parse_assets("## notes: hello\n- quiz: a | a: b\n")

    def test_a_typod_field_is_loud_not_silently_dropped(self):
        for bad in ("## concept: alpha\n- quizz: a | a: b\n",
                    "## rubric: alpha\n- clam: a\n",
                    "## interleaved\n- problems: a | concepts: alpha\n"):
            with self.assertRaisesRegex(S.FormatError, "unknown field"):
                S.parse_assets(bad)

    def test_missing_concept_block_is_loud(self):
        text = ASSETS_U1.replace(
            "## concept: beta\n- quiz: What does beta name? | a: the second "
            "thing | distractor: people mix it with alpha\n", "")
        with self.assertRaisesRegex(S.IntegrityError, "beta"):
            self.check_assets(text)

    def test_later_units_need_two_interleaved(self):
        text = ASSETS_U2.replace(
            "- problem: second mixed problem | concepts: beta, delta", "")
        with self.assertRaisesRegex(S.IntegrityError, ">=2"):
            self.check_assets(text, unit_num=2)


# ================================================================ check

class TestCheck(CourseCase):

    def test_valid_course_passes(self):
        self.assertEqual(S.cmd_check(self.dir), "ok")

    def test_map_trailing_sections_do_not_pollute_the_last_concept(self):
        """## Controversies / ## Sources must not rewrite delta's fields."""
        concepts = S.parse_map(self.dir)
        self.assertEqual(concepts["delta"]["prereqs"], ["beta"])
        self.assertEqual(concepts["delta"]["verify"], "quiz")

    def test_unknown_prereq_is_loud(self):
        p = self.dir / "domain-map.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "prereqs: [beta]", "prereqs: [ghost]"), encoding="utf-8")
        with self.assertRaisesRegex(S.IntegrityError, "ghost"):
            S.cmd_check(self.dir)

    def test_cycle_is_loud(self):
        p = self.dir / "domain-map.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "### alpha\ndef: the first thing\nprereqs: []",
            "### alpha\ndef: the first thing\nprereqs: [delta]"),
            encoding="utf-8")
        with self.assertRaisesRegex(S.IntegrityError, "cycle"):
            S.cmd_check(self.dir)

    def test_errata_heal_an_edge_in_several_spellings(self):
        base = (self.dir / "domain-map.md").read_text(
            encoding="utf-8").replace(
            "### alpha\ndef: the first thing\nprereqs: []",
            "### alpha\ndef: the first thing\nprereqs: [delta]")
        for form in ("erratum 2026-07-21: remove-edge delta -> alpha",
                     "- erratum 2026-07-21: remove-edge delta -> alpha",
                     "  Erratum 2026-07-21: remove-edge delta -> alpha"):
            (self.dir / "domain-map.md").write_text(
                base + "\n" + form + "\n", encoding="utf-8")
            self.assertEqual(S.cmd_check(self.dir), "ok", form)

    def test_orphan_state_row_is_loud(self):
        meta, recs = self.state()
        recs["ghost"] = dict(recs["alpha"], id="ghost")
        S.save_state(self.dir, meta, recs)
        with self.assertRaisesRegex(S.IntegrityError, "ghost"):
            S.cmd_check(self.dir)

    def test_missing_state_row_is_loud(self):
        meta, recs = self.state()
        del recs["delta"]
        S.save_state(self.dir, meta, recs)
        with self.assertRaisesRegex(S.IntegrityError, "delta"):
            S.cmd_check(self.dir)

    def test_verify_disagreement_with_the_map_is_loud(self):
        self.set_record("alpha", verify="use")
        with self.assertRaisesRegex(S.IntegrityError, "verify"):
            S.cmd_check(self.dir)

    def test_keystone_must_be_one_of_the_units_concepts(self):
        p = self.dir / "plan.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "keystones: [alpha]", "keystones: [delta]"), encoding="utf-8")
        with self.assertRaisesRegex(S.IntegrityError, "keystone"):
            S.cmd_check(self.dir)

    def test_unit_too_short_for_its_concepts_is_loud(self):
        """The arithmetic that silently abandoned two of three concepts."""
        p = self.dir / "plan.md"
        p.write_text(PLAN_MD.replace(
            "sessions: 3\nconcepts: [alpha, beta]",
            "sessions: 2\nconcepts: [alpha, beta]"), encoding="utf-8")
        with self.assertRaisesRegex(S.IntegrityError, "needs >=3"):
            S.cmd_check(self.dir)

    def test_course_without_room_for_synthesis_is_loud(self):
        p = self.dir / "plan.md"
        p.write_text(PLAN_MD.replace("next-session: 2/10",
                                     "next-session: 2/6"), encoding="utf-8")
        with self.assertRaisesRegex(S.IntegrityError, "synthesis"):
            S.cmd_check(self.dir)

    def test_bad_plan_header_values_are_loud(self):
        for good, bad in (("course-status: active", "course-status: banana"),
                          ("next-session: 2/10", "next-session: potato"),
                          ("re-entry-pending: no", "re-entry-pending: maybe"),
                          ("sessions-done: 1", "sessions-done: many")):
            (self.dir / "plan.md").write_text(PLAN_MD.replace(good, bad),
                                              encoding="utf-8")
            with self.assertRaises(S.FormatError):
                S.cmd_check(self.dir)

    def test_bad_unit_status_is_loud(self):
        (self.dir / "plan.md").write_text(
            PLAN_MD.replace("status: untouched", "status: bananas"),
            encoding="utf-8")
        with self.assertRaises(S.FormatError):
            S.cmd_check(self.dir)

    def test_started_unit_without_assets_is_loud(self):
        (self.dir / "assets" / "unit-01.md").unlink()
        with self.assertRaisesRegex(S.IntegrityError, "unit-01"):
            S.cmd_check(self.dir)

    def test_plan_comments_do_not_become_concepts(self):
        (self.dir / "plan.md").write_text(
            PLAN_MD + "\n<!-- keystones: the 1-2 that matter -->\n",
            encoding="utf-8")
        self.assertEqual(S.cmd_check(self.dir), "ok")

    def test_a_non_unit_section_is_not_a_unit(self):
        (self.dir / "plan.md").write_text(PLAN_MD + "\n## Notes\nprose\n",
                                          encoding="utf-8")
        _, units = S.parse_plan(self.dir)
        self.assertEqual([u["num"] for u in units], [1, 2])


# ============================================================= dispatch

class TestDispatch(CourseCase):

    def hdr(self, **kw):
        S.write_plan_header(self.dir, kw)

    def test_standard_midway_through_a_unit(self):
        d = S.dispatch(self.dir)
        self.assertEqual(d["type"], "standard")
        self.assertEqual(d["unit"]["num"], 1)
        self.assertEqual(d["cap"], S.TEACHING_CAP)

    def test_teach_back_on_the_units_last_session(self):
        self.settle()
        self.hdr(**{"next-session": "3/10"})
        d = S.dispatch(self.dir)
        self.assertEqual(d["type"], "teach-back")
        self.assertEqual(d["cap"], S.QUEUE_CAP)

    def test_placement_on_session_one(self):
        self.hdr(**{"next-session": "1/10"})
        self.assertEqual(S.dispatch(self.dir)["type"], "placement")

    def test_lifecycle_when_not_active(self):
        self.hdr(**{"course-status": "paused"})
        self.assertEqual(S.dispatch(self.dir)["type"], "lifecycle")

    def test_dormant_after_a_fortnight_of_silence(self):
        """The pause rule must be reachable without a checkpoint."""
        self.hdr(**{"last-attended": "2026-07-01"})
        self.assertEqual(S.dispatch(self.dir)["type"], "dormant")

    def test_re_entry_beats_a_standard_session(self):
        self.hdr(**{"re-entry-pending": "yes"})
        self.assertEqual(S.dispatch(self.dir)["type"], "re-entry")

    def test_repair_beats_a_standard_session(self):
        self.set_meta(**{"repair-pending": "alpha"})
        d = S.dispatch(self.dir)
        self.assertEqual((d["type"], d["concept"]), ("repair", "alpha"))

    def test_consolidation_after_the_last_unit(self):
        self.settle("alpha", "gamma")
        self.hdr(**{"next-session": "8/10"})
        d = S.dispatch(self.dir)
        self.assertEqual(d["type"], "consolidation")
        self.assertTrue(d["terminal"])

    def test_graduation_when_the_counter_is_exhausted(self):
        """The state that used to serve standard sessions forever."""
        self.hdr(**{"next-session": "11/10"})
        self.assertEqual(S.dispatch(self.dir)["type"], "graduation")

    def test_missing_assets_are_flagged_for_authoring(self):
        self.hdr(**{"next-session": "3/10"})
        self.assertEqual(S.dispatch(self.dir)["author"], "unit-02.md")
        self.add_u2_assets()
        self.assertIsNone(S.dispatch(self.dir)["author"])


# ========================================================= begin / close

class TestBeginClose(CourseCase):

    def test_begin_locks_checks_and_dispatches(self):
        out = S.cmd_begin(self.dir)
        self.assertIn("type: standard", out)
        self.assertIn("session: 2 of 10", out)
        self.assertIn("quiz these", out)
        self.assertTrue((self.dir / S.SENTINEL).exists())

    def test_course_label_disambiguates_courses_in_one_chat(self):
        """Two courses sharing a chat must produce different bookend
        labels, or reconciliation attributes lessons to the wrong one."""
        self.assertIn("aristotle test", S.course_label(self.dir))
        p = self.dir / "domain-map.md"
        p.write_text("name: AI economics\n" + p.read_text(encoding="utf-8"),
                     encoding="utf-8")
        self.assertEqual(S.course_label(self.dir), "AI economics")
        self.assertIn("course: AI economics", S.cmd_begin(self.dir))

    def test_begin_surfaces_the_last_open_question(self):
        """Continuity: the hook the previous close wrote must reach the
        next session without the tutor having to go find it."""
        S.cmd_begin(self.dir)
        self.write_log("2026-07-21-2.md",
                       log_text("2", ("alpha", "pass", "x"),
                                extra="why does the cheap one win?"))
        S.cmd_close(self.dir, self.dir / "log" / "2026-07-21-2.md")
        out = S.cmd_begin(self.dir)
        self.assertIn("last session: 2 on 2026-07-21", out)
        self.assertIn("why does the cheap one win?", out)

    def test_begin_flags_an_abandoned_session(self):
        """A mid-teach abandonment must not look identical to a clean
        finish — the tutor would re-open with the same hook."""
        S.cmd_begin(self.dir)                      # writes the sentinel
        p = self.dir / S.SENTINEL
        old = (dt.datetime.now() - dt.timedelta(hours=5)).timestamp()
        os.utime(p, (old, old))
        out = S.cmd_begin(self.dir)                # recover -> reset
        self.assertIn("abandoned before it closed", out)
        self.assertIn("~5h ago", out)

    def test_begin_is_quiet_when_nothing_was_abandoned(self):
        out = S.cmd_begin(self.dir)
        self.assertNotIn("abandoned", out)

    def test_begin_refuses_when_a_session_is_live(self):
        S.cmd_begin(self.dir)
        with self.assertRaisesRegex(S.IntegrityError, "live"):
            S.cmd_begin(self.dir)

    def test_begin_fails_loudly_on_a_broken_course(self):
        (self.dir / "assets" / "unit-01.md").write_text(
            "## concept: alpha\n- quiz: TODO | a: TODO\n", encoding="utf-8")
        with self.assertRaises(S.IntegrityError):
            S.cmd_begin(self.dir)

    def test_begin_caps_the_queue_by_session_type(self):
        """A teaching session quizzes at most TEACHING_CAP due items —
        4 due, cap 2 (since 2026-08-24): the rest roll forward."""
        for cid in ("beta", "gamma", "delta"):
            self.set_record(cid, status="active", next="2026-07-01")
        self.assertIn(f"quiz these ({S.TEACHING_CAP})", S.cmd_begin(self.dir))
        self.assertEqual(S.TEACHING_CAP, 2)

    def test_begin_issues_a_fractional_token_for_a_repair(self):
        self.set_meta(**{"repair-pending": "alpha"})
        self.assertIn("session: 2r of 10", S.cmd_begin(self.dir))

    def test_a_second_repair_gets_a_distinct_token(self):
        self.set_meta(**{"repair-pending": "alpha"})
        meta, recs = self.state()
        meta["committed-sessions"].append("2r")
        S.save_state(self.dir, meta, recs)
        self.assertIn("session: 2r2 of 10", S.cmd_begin(self.dir))

    def test_close_advances_everything(self):
        S.cmd_begin(self.dir)
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("beta", "taught", "intro"),
                                    ("alpha", "pass", "clean")))
        S.cmd_close(self.dir, p)
        header, _ = S.parse_plan(self.dir)
        self.assertEqual(header["next-session"], "3/10")
        self.assertEqual(header["sessions-done"], "2")
        self.assertEqual(header["last-attended"], TODAY)
        self.assertEqual(self.rec("beta")["status"], "active")
        self.assertFalse((self.dir / S.SENTINEL).exists())

    def test_close_marks_the_unit_taught_on_its_last_session(self):
        self.settle()
        S.write_plan_header(self.dir, {"next-session": "3/10"})
        self.add_u2_assets()
        S.cmd_begin(self.dir)
        p = self.write_log("2026-07-21-3.md",
                           log_text("3", ("alpha", "rubric-pass", "clean")))
        S.cmd_close(self.dir, p)
        _, units = S.parse_plan(self.dir)
        self.assertEqual(units[0]["status"], "taught")

    def test_a_repair_close_does_not_advance_the_counter(self):
        self.set_meta(**{"repair-pending": "alpha"})
        S.cmd_begin(self.dir)
        p = self.write_log("2026-07-21-2r.md",
                           log_text("2r", ("alpha", "pass", "repaired")))
        S.cmd_close(self.dir, p)
        header, _ = S.parse_plan(self.dir)
        self.assertEqual(header["next-session"], "2/10")
        self.assertEqual(header["sessions-done"], "2")
        self.assertEqual(self.state()[0]["repair-pending"], "none")

    def test_close_refuses_a_log_from_a_different_session(self):
        S.cmd_begin(self.dir)
        p = self.write_log("2026-07-21-9.md",
                           log_text("9", ("alpha", "pass", "x")))
        with self.assertRaisesRegex(S.IntegrityError, "refusing"):
            S.cmd_close(self.dir, p)

    def test_close_commits_and_leaves_a_clean_tree(self):
        S.cmd_begin(self.dir)
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "pass", "clean")))
        S.cmd_close(self.dir, p)
        self.assertFalse(S._dirty(self.dir))

    def test_close_clears_re_entry(self):
        S.write_plan_header(self.dir, {"re-entry-pending": "yes"})
        S.cmd_begin(self.dir)
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "pass", "x")))
        S.cmd_close(self.dir, p)
        self.assertEqual(S.parse_plan(self.dir)[0]["re-entry-pending"], "no")

    def test_two_sessions_in_a_row(self):
        """State written by one close must be consumable by the next begin."""
        S.cmd_begin(self.dir)
        S.cmd_close(self.dir, self.write_log(
            "2026-07-21-2.md", log_text("2", ("beta", "taught", "x"))))
        self.add_u2_assets()
        self.assertIn("type: teach-back", S.cmd_begin(self.dir))
        S.cmd_close(self.dir, self.write_log(
            "2026-07-21-3.md", log_text("3", ("alpha", "rubric-pass", "y"))))
        self.assertEqual(S.parse_plan(self.dir)[0]["next-session"], "4/10")


# ============================================================== recover

class TestRecover(CourseCase):

    def stale(self, token="2"):
        p = self.dir / S.SENTINEL
        p.write_text(f"session: {token}\n", encoding="utf-8")
        old = (dt.datetime.now() - dt.timedelta(hours=5)).timestamp()
        os.utime(p, (old, old))
        return p

    def test_no_repo_is_initialised_not_a_traceback(self):
        self.assertEqual(S.cmd_recover(self.dir), "initialized")
        self.assertTrue((self.dir / ".git").exists())
        self.assertTrue((self.dir / ".gitignore").exists())

    def test_clean_tree_is_ok(self):
        self.git_init()
        self.assertEqual(S.cmd_recover(self.dir), "ok")

    def test_fresh_sentinel_locks(self):
        self.git_init()
        (self.dir / S.SENTINEL).write_text("session: 2\n", encoding="utf-8")
        self.assertEqual(S.cmd_recover(self.dir), "locked")

    def test_age_comes_from_mtime_not_an_agent_timestamp(self):
        """No clock, timezone, or agent-written string may enter this."""
        self.git_init()
        (self.dir / S.SENTINEL).write_text(
            "session: 2\nstarted: nonsense-not-a-date\n", encoding="utf-8")
        self.assertEqual(S.cmd_recover(self.dir), "locked")

    def test_stale_with_a_log_replays(self):
        self.git_init()
        self.write_log("2026-07-21-2.md",
                       log_text("2", ("alpha", "pass", "clean")))
        self.stale("2")
        self.assertEqual(S.cmd_recover(self.dir), "replayed")
        self.assertEqual(self.rec("alpha")["interval"], 3)
        self.assertFalse((self.dir / S.SENTINEL).exists())

    def test_replay_of_an_already_committed_log_is_harmless(self):
        self.git_init()
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "pass", "clean")))
        S.cmd_commit_grades(self.dir, p)
        iv = self.rec("alpha")["interval"]
        self.stale("2")
        self.assertEqual(S.cmd_recover(self.dir), "replayed")
        self.assertEqual(self.rec("alpha")["interval"], iv)

    def test_stale_with_no_log_resets(self):
        """Reset discards session debris (untracked logs, engine-owned
        state), never other work in the course."""
        self.git_init()
        (self.dir / "log" / "scratch.md").write_text("debris",
                                                     encoding="utf-8")
        (self.dir / "notes.md").write_text("mine", encoding="utf-8")
        self.stale("2")
        self.assertEqual(S.cmd_recover(self.dir), "reset")
        self.assertFalse((self.dir / "log" / "scratch.md").exists())
        self.assertTrue((self.dir / "notes.md").exists())

    def test_recovery_stubs_a_missing_taught_line_rather_than_reset(self):
        """A live tutor gets the hard error and fixes its own log;
        recovery has nobody around to fix anything, so it stubs the
        coverage line conservatively instead of discarding a whole
        session's grades."""
        self.git_init()
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("beta", "taught", "intro"),
                                    taught=""))
        self.stale("2")
        self.assertEqual(S.cmd_recover(self.dir), "replayed")
        self.assertEqual(self.rec("beta")["interval"], 1)
        self.assertIn("- beta: (unrecorded", p.read_text(encoding="utf-8"))

    def test_an_unusable_log_falls_back_to_reset(self):
        self.git_init()
        self.write_log("2026-07-21-2.md",
                       log_text("2", ("ghost", "pass", "unknown id")))
        self.stale("2")
        self.assertEqual(S.cmd_recover(self.dir), "reset")
        self.assertFalse((self.dir / S.SENTINEL).exists())

    def test_an_unparseable_token_never_destroys_anything(self):
        """'2/10' used to glob nothing and reset a finished session away."""
        self.git_init()
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "pass", "clean")))
        self.stale("2/10")
        self.assertEqual(S.cmd_recover(self.dir), "locked")
        self.assertTrue(p.exists())

    def test_recovery_never_touches_a_parent_repo(self):
        """reset --hard used to revert the whole enclosing repository."""
        parent = Path(tempfile.mkdtemp(prefix="aristotle-parent-"))
        self.addCleanup(shutil.rmtree, parent, ignore_errors=True)
        subprocess.run(["git", "init", "-q"], cwd=parent, check=True)
        thesis = parent / "thesis.md"
        thesis.write_text("v1 committed\n", encoding="utf-8")
        course = parent / "course"
        shutil.copytree(self.dir, course)
        S._git(parent, "add", "-A")
        S._git(parent, "commit", "-q", "-m", "base")
        thesis.write_text("v2 THREE HOURS OF UNCOMMITTED EDITS\n",
                          encoding="utf-8")
        p = course / S.SENTINEL
        p.write_text("session: 2\n", encoding="utf-8")
        old = (dt.datetime.now() - dt.timedelta(hours=5)).timestamp()
        os.utime(p, (old, old))
        self.assertEqual(S.cmd_recover(course), "reset")
        self.assertIn("THREE HOURS", thesis.read_text(encoding="utf-8"))

    def test_commits_are_scoped_to_the_course_subtree(self):
        parent = Path(tempfile.mkdtemp(prefix="aristotle-parent2-"))
        self.addCleanup(shutil.rmtree, parent, ignore_errors=True)
        subprocess.run(["git", "init", "-q"], cwd=parent, check=True)
        (parent / "unrelated.md").write_text("mine\n", encoding="utf-8")
        course = parent / "course"
        shutil.copytree(self.dir, course)
        S._git(parent, "add", "-A")
        S._git(parent, "commit", "-q", "-m", "base")
        (parent / "unrelated.md").write_text("edited, not staged\n",
                                             encoding="utf-8")
        S.cmd_begin(course)
        log = course / "log" / "2026-07-21-2.md"
        log.write_text(log_text("2", ("alpha", "pass", "x")),
                       encoding="utf-8")
        S.cmd_close(course, log)
        self.assertIn("unrelated.md",
                      S._git(parent, "status", "--porcelain").stdout)


# ================================================================== CLI

class TestCLI(CourseCase):

    def test_check_prints_ok(self):
        """Contract: exit 0 and 'ok' on line one. Design warnings may
        follow — they are advice, never a failure."""
        r = self.cli("check")
        lines = r.stdout.strip().splitlines()
        self.assertEqual((r.returncode, lines[0]), (0, "ok"))
        self.assertTrue(all(l.startswith("warn: ") for l in lines[1:]),
                        r.stdout)

    def test_integrity_error_is_exit_2_with_no_traceback(self):
        self.set_record("alpha", verify="use")
        r = self.cli("check")
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stderr.startswith("ERROR:"))
        self.assertNotIn("Traceback", r.stderr)

    def test_missing_file_is_exit_2_with_no_traceback(self):
        (self.dir / "plan.md").unlink()
        r = self.cli("check")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)

    def test_missing_logfile_is_exit_2_with_no_traceback(self):
        r = self.cli("close", "log/nope.md")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)

    def test_recover_off_repo_is_exit_0_not_a_traceback(self):
        r = self.cli("recover")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "initialized")

    def test_begin_and_close_round_trip_through_the_cli(self):
        self.assertEqual(self.cli("begin").returncode, 0)
        self.write_log("2026-07-21-2.md",
                       log_text("2", ("alpha", "pass", "clean")))
        r = self.cli("close", "log/2026-07-21-2.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("next: 3/10", r.stdout)

    def test_close_accepts_an_absolute_log_path(self):
        self.cli("begin")
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "pass", "clean")))
        self.assertEqual(self.cli("close", str(p)).returncode, 0)

    def test_report_never_crashes(self):
        r = self.cli("report")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("due today", r.stdout)


# ========================================================== asked ledger

class TestAskedLedger(CourseCase):
    """The pilot's worst failure: two stateless tutors, same state, same
    policy — same questions. The fix is state the next tutor SEES, not a
    stronger exhortation: every question asked lands in the log, and
    `begin` replays the recent ones."""

    def asked_log(self, name, session, *items):
        lines = "\n".join(f"- {i}" for i in items)
        return self.write_log(name, (
            f"session: {session}\n\n## taught\nx\n\n## grades\n"
            f"- grade: alpha | result: pass | note: ok\n\n"
            f"## asked\n{lines}\n\n## open question\nnext hook\n"))

    def test_begin_surfaces_recently_asked_items(self):
        self.asked_log("2026-07-18-2.md", "2", "alpha.q1",
                       "the sticker-vs-blended case")
        self.asked_log("2026-07-19-3.md", "3", "beta.q1")
        out = S.cmd_begin(self.dir)
        self.assertIn("asked recently", out)
        self.assertIn("[2] the sticker-vs-blended case", out)
        self.assertIn("[3] beta.q1", out)

    def test_recency_window_is_three_logs_but_bank_use_is_forever(self):
        """A bank item burned five sessions ago must STAY burned — the
        repetition the pilot hit was invisible precisely because nothing
        outlived the previous session."""
        self.asked_log("2026-07-15-2.md", "2", "alpha.q1",
                       "an old free-text case")
        self.asked_log("2026-07-16-3.md", "3", "beta.q1")
        self.asked_log("2026-07-17-4.md", "4", "alpha.q2")
        self.asked_log("2026-07-18-5.md", "5", "delta.q1")
        out = S.cmd_begin(self.dir)
        self.assertNotIn("an old free-text case", out)   # aged out
        self.assertIn("bank items used", out)
        self.assertIn("alpha.q1", out)                    # burned forever

    def test_asked_matching_is_case_insensitive(self):
        """Tutors capitalize inconsistently ('AI Econ' vs 'AI economics');
        a ledger that treats Alpha.Q1 and alpha.q1 as different items
        silently un-burns them."""
        self.write_log("2026-07-18-2.md", (
            "session: 2\n\n## taught\nx\n\n## grades\n\n"
            "## Asked\n- Alpha.Q1\n"))
        self.asked_log("2026-07-19-3.md", "3", "alpha.q1")
        out = S.cmd_begin(self.dir)
        self.assertEqual(out.lower().count("alpha.q1"), 2)  # 1 recent + 1 bank
        self.assertIn("bank items used", out)

    def test_begin_is_quiet_without_asked_history(self):
        self.write_log("2026-07-18-2.md",
                       log_text("2", ("alpha", "pass", "x"), extra="hook"))
        out = S.cmd_begin(self.dir)
        self.assertNotIn("asked recently", out)
        self.assertNotIn("bank items used", out)


# ======================================================== taught ledger

class TestTaughtLedger(CourseCase):
    """A stored bank item is an implicit claim: 'the facts in my answer
    key were presented to this learner.' Nothing recorded fact-level
    coverage, so a session could open cold on a case the teaching session
    had elided — and grade the miss a fail (audit 2026-08-25, F1).
    '## taught' is now the coverage record, and `begin` replays it."""

    def taught_log(self, name, session, taught, grade=None, asked=""):
        cid, res, note = grade or ("alpha", "pass", "ok")
        return self.write_log(name, (
            f"session: {session}\n\n## taught\n{taught}\n\n"
            f"## grades\n- grade: {cid} | result: {res} | note: {note}\n\n"
            f"## asked\n{asked}\n\n## open question\nhook\n"))

    def test_a_taught_line_parses_with_and_without_its_clause(self):
        self.taught_log("2026-07-19-2.md", "2",
                        "- alpha: cache pricing; session reuse | without: the "
                        "ProjectDiscovery case\n"
                        "- beta: paid writes vs discounted reads")
        h = S._taught_history(self.dir)
        self.assertEqual(h["alpha"], [("2", "cache pricing; session reuse",
                                       "the ProjectDiscovery case")])
        self.assertEqual(h["beta"],
                         [("2", "paid writes vs discounted reads", "")])

    def test_a_pipe_in_the_presented_text_does_not_split_the_clause(self):
        """The presented text is free prose; only the LAST separator is
        the without-clause."""
        self.taught_log("2026-07-19-2.md", "2",
                        "- alpha: writes | reads | reuse | without: the case")
        entry = S._taught_history(self.dir)["alpha"][0]
        self.assertEqual(entry[1:], ("writes | reads | reuse", "the case"))

    def test_legacy_prose_under_taught_is_ignored_not_fatal(self):
        self.taught_log("2026-07-19-2.md", "2",
                        "covered cache economics and the pricing table")
        self.assertEqual(S._taught_history(self.dir), {})

    def test_ids_match_case_insensitively(self):
        self.taught_log("2026-07-19-2.md", "2", "- Alpha: the pricing table")
        self.assertIn("alpha", S._taught_history(self.dir))

    def test_every_session_that_presented_it_is_kept_in_order(self):
        self.taught_log("2026-07-18-2.md", "2", "- alpha: the pricing table")
        self.taught_log("2026-07-19-3.md", "3", "- alpha: writes vs reads")
        self.assertEqual([e[0] for e in S._taught_history(self.dir)["alpha"]],
                         ["2", "3"])

    def test_begin_replays_the_record_for_every_queued_concept(self):
        self.taught_log("2026-07-19-2.md", "2",
                        "- alpha: the pricing table | without: the PD case")
        out = S.cmd_begin(self.dir)
        self.assertIn("presented (grade only against this; anything absent "
                      "goes INTO the question):", out)
        self.assertIn("  alpha [2]: the pricing table | without: the PD case",
                      out)

    def test_a_queued_concept_with_no_record_says_so(self):
        out = S.cmd_begin(self.dir)
        self.assertIn("  alpha: (nothing recorded as presented — supply all "
                      "facts in any probe)", out)

    def test_only_queued_concepts_are_replayed(self):
        """beta was taught but is not due — replaying it would invite a
        probe the scheduler did not ask for."""
        self.taught_log("2026-07-19-2.md", "2", "- beta: the second thing")
        out = S.cmd_begin(self.dir)
        self.assertIn("alpha:", out)
        self.assertNotIn("beta [2]", out)

    def test_an_empty_quiz_queue_prints_neither_block(self):
        self.set_record("alpha", next="2099-01-01")
        out = S.cmd_begin(self.dir)
        self.assertIn("quiz these (0)", out)
        self.assertNotIn("presented (", out)
        self.assertNotIn("banks spendable", out)

    def test_close_refuses_a_taught_grade_with_no_taught_line(self):
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("beta", "taught", "intro"),
                                    taught="a prose summary of the session"))
        with self.assertRaisesRegex(S.IntegrityError, "graded taught"):
            S.cmd_commit_grades(self.dir, p)
        # a failed close leaves the course untouched
        self.assertEqual(self.rec("beta")["status"], "untaught")
        self.assertNotIn("2", self.state()[0]["committed-sessions"])

    def test_close_accepts_a_taught_grade_with_its_line(self):
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("beta", "taught", "intro"),
                                    taught="- beta: the definition | "
                                           "without: the worked example"))
        S.cmd_commit_grades(self.dir, p)
        self.assertEqual(self.rec("beta")["status"], "active")

    def test_the_taught_line_may_be_capitalised_differently(self):
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("beta", "taught", "intro"),
                                    taught="- Beta: the definition"))
        S.cmd_commit_grades(self.dir, p)
        self.assertEqual(self.rec("beta")["status"], "active")

    def test_a_non_taught_grade_needs_no_line(self):
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "pass", "clean")))
        self.assertEqual(S.cmd_commit_grades(self.dir, p), "applied")

    def test_old_format_logs_never_break_begin_or_close(self):
        """Every log written before the grammar existed carries one prose
        line under '## taught'. They must stay readable forever."""
        self.taught_log("2026-07-18-2.md", "2", "stuff we did")
        S.cmd_begin(self.dir)
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "pass", "clean")))
        S.cmd_close(self.dir, p)
        self.assertEqual(S.parse_plan(self.dir)[0]["next-session"], "3/10")


# =========================================================== bank fence

class TestBankFence(CourseCase):
    """Two audit sessions spent unit-6 bank items to quiz a concept that
    was never taught (F2). Bank items are single-use for the whole
    course, so unit 6 would have arrived with its best items dead and the
    ledger forbidding them. `begin` names the spendable banks; `close`
    says so out loud when a far-future one was burned."""

    def asked_log(self, name, session, *items):
        lines = "\n".join(f"- {i}" for i in items)
        return self.write_log(name, (
            f"session: {session}\n\n## taught\nstuff\n\n## grades\n"
            f"- grade: alpha | result: pass | note: ok\n\n"
            f"## asked\n{lines}\n\n## open question\nhook\n"))

    def use_plan(self, text):
        (self.dir / "plan.md").write_text(text, encoding="utf-8")

    def test_only_a_reached_units_bank_is_spendable(self):
        self.add_u2_assets()
        self.assertIn("banks spendable: assets/unit-01.md — items from "
                      "unreached units are off-limits", S.cmd_begin(self.dir))

    def test_a_started_unit_joins_the_spendable_list(self):
        self.add_u2_assets()
        self.use_plan(PLAN_MD.replace("artifact-milestone: draft the thing\n"
                                      "status: untouched",
                                      "artifact-milestone: draft the thing\n"
                                      "status: in-progress"))
        self.assertIn("banks spendable: assets/unit-01.md, assets/unit-02.md",
                      S.cmd_begin(self.dir))

    def test_the_current_unit_is_reached_while_still_untouched(self):
        """Session 4 sits inside unit 2; its status only moves at close."""
        S.write_plan_header(self.dir, {"next-session": "4/10"})
        self.add_u2_assets()
        self.assertIn("assets/unit-02.md", S.cmd_begin(self.dir))

    def test_an_unwritten_bank_is_not_listed(self):
        out = S.cmd_begin(self.dir)
        self.assertIn("banks spendable: assets/unit-01.md", out)
        self.assertNotIn("unit-02.md", out)

    def test_close_warns_when_an_unreached_units_item_was_spent(self):
        S.cmd_begin(self.dir)
        out = S.cmd_close(self.dir, self.asked_log(
            "2026-07-21-2.md", "2", "gamma.q1"))
        self.assertIn("warn: asked item 'gamma.q1' belongs to unit 2, which "
                      "is unreached — that bank item is now spent for the "
                      "whole course.", out)

    def test_a_reached_item_free_text_and_unknown_ids_never_warn(self):
        S.cmd_begin(self.dir)
        out = S.cmd_close(self.dir, self.asked_log(
            "2026-07-21-2.md", "2", "alpha.q1", "the sticker-vs-blended case",
            "ghost.q7"))
        self.assertNotIn("warn:", out)

    def test_the_warning_never_fails_the_close(self):
        self.cli("begin")
        self.asked_log("2026-07-21-2.md", "2", "delta.q1")
        r = self.cli("close", "log/2026-07-21-2.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("warn: asked item 'delta.q1'", r.stdout)
        self.assertEqual(S.parse_plan(self.dir)[0]["next-session"], "3/10")


# ============================================================ seed fence

class TestSeedFence(CourseCase):
    """Placement seeded a unit-6 concept 'exposed' from one answer, which
    put it in the retrieval queue of nearly every session that followed —
    months before its unit, with no spendable bank and no presented facts
    to probe (F3). Calibration evidence is not retrieval evidence."""

    def test_a_reached_units_seed_still_activates(self):
        S.cmd_seed(self.dir, "beta", "retrievable")
        r = self.rec("beta")
        self.assertEqual((r["status"], r["interval"], r["next"]),
                         ("active", 7, "2026-07-28"))

    def test_the_current_units_seed_activates_before_it_is_taught(self):
        S.write_plan_header(self.dir, {"next-session": "4/10"})
        S.cmd_seed(self.dir, "delta", "exposed")
        self.assertEqual(self.rec("delta")["status"], "active")

    def test_a_future_units_seed_is_a_note_and_nothing_else(self):
        S.cmd_seed(self.dir, "delta", "retrievable")
        r = self.rec("delta")
        self.assertEqual((r["status"], r["next"], r["interval"], r["note"]),
                         ("untaught", "-", 0, "placement: retrievable"))
        self.assertNotIn("delta", S.build_queue(self.dir))

    def test_a_future_seed_never_reaches_a_begin_queue(self):
        S.cmd_seed(self.dir, "delta", "exposed")
        self.assertNotIn("delta", S.cmd_begin(self.dir))

    def test_a_concept_no_unit_teaches_is_not_fenced(self):
        """Nothing will ever 'open' for it, so fencing would strand the
        only evidence the course has."""
        p = self.dir / "plan.md"
        p.write_text(PLAN_MD.replace("concepts: [gamma, delta]",
                                     "concepts: [gamma]"), encoding="utf-8")
        S.cmd_seed(self.dir, "delta", "exposed")
        self.assertEqual(self.rec("delta")["status"], "active")

    def test_a_future_seed_is_idempotent(self):
        S.cmd_seed(self.dir, "delta", "exposed")
        S.cmd_seed(self.dir, "delta", "exposed")
        self.assertEqual(len(self.state()[1]), 4)

    def test_the_concept_still_teaches_normally_when_its_unit_opens(self):
        S.cmd_seed(self.dir, "delta", "retrievable")
        S.cmd_commit_grades(self.dir, self.write_log(
            "2026-07-21-2.md", log_text("2", ("delta", "taught", "opened"))))
        r = self.rec("delta")
        self.assertEqual((r["status"], r["interval"], r["next"]),
                         ("active", 1, "2026-07-22"))


# ========================================================= review blocks

REVIEW_PLAN_MD = """\
course-status: active
next-session: 4/10
cadence: 3
sessions-done: 3
last-attended: 2026-07-20
re-entry-pending: no

## Unit 1: Why does alpha matter?
sessions: 3
concepts: [alpha, beta]
keystones: [alpha]
artifact-milestone: none
status: taught

## Review: mixed review over unit 1
sessions: 1

## Unit 2: What is gamma for?
sessions: 3
concepts: [gamma, delta]
keystones: [gamma]
artifact-milestone: draft the thing
status: untouched
"""


class TestReviewBlocks(CourseCase):
    """Rolling review between units, replacing the pilot's back-to-back
    terminal consolidation pair. A review block occupies sessions like a
    unit but teaches nothing and owns no assets."""

    def setUp(self):
        super().setUp()
        (self.dir / "plan.md").write_text(REVIEW_PLAN_MD, encoding="utf-8")
        self.settle("alpha")

    def test_review_block_dispatches_as_mixed_review(self):
        S.cmd_check(self.dir)                     # no assets, no floor demand
        d = S.dispatch(self.dir)
        self.assertEqual(d["type"], "review")
        self.assertEqual(d["cap"], S.QUEUE_CAP)
        self.assertFalse(d["terminal"])

    def test_review_block_is_an_authoring_slot_for_the_next_unit(self):
        self.assertEqual(S.dispatch(self.dir)["author"], "unit-02.md")
        self.add_u2_assets()
        self.assertIsNone(S.dispatch(self.dir)["author"])

    def test_review_never_masks_the_next_units_prereqs(self):
        """repair-pending triggers on the NEXT unit's prereqs; an
        untouched-looking review block must not swallow that lookup."""
        self.assertEqual(S._next_unit_prereq_ids(self.dir),
                         {"alpha", "beta"})

    def test_closing_a_review_session_moves_only_the_counter(self):
        S.cmd_begin(self.dir)
        p = self.write_log("2026-07-21-4.md",
                           log_text("4", ("alpha", "pass", "clean")))
        S.cmd_close(self.dir, p)
        header, units = S.parse_plan(self.dir)
        self.assertEqual(header["next-session"], "5/10")
        self.assertEqual([u["status"] for u in units if u.get("num")],
                         ["taught", "untouched"])


class TestSequenceGuard(CourseCase):
    """A log's session token must match where the course actually is.
    Observed 2026-08-31: a context-scrambled tutor wrote 'session: 19'
    while the course was at 18; commit accepted it and the review block
    at index 18 was silently skipped forever."""

    def test_commit_rejects_a_token_ahead_of_the_course(self):
        p = self.write_log("2026-07-21-3.md",
                           log_text("3", ("alpha", "pass", "clean")))
        with self.assertRaises(S.IntegrityError) as cm:
            S.cmd_commit_grades(self.dir, p)
        self.assertIn("session '3'", str(cm.exception))
        self.assertIn("at session 2", str(cm.exception))

    def test_a_committed_token_replays_as_noop_never_a_second_apply(self):
        iv = self.rec("alpha")["interval"]
        p = self.write_log("2026-07-19-1.md",
                           log_text("1", ("alpha", "pass", "clean")))
        self.assertEqual(S.cmd_commit_grades(self.dir, p), "noop")
        self.assertEqual(self.rec("alpha")["interval"], iv)

    def test_repair_tokens_share_the_current_index(self):
        p = self.write_log("2026-07-21-2r.md",
                           log_text("2r", ("alpha", "pass", "clean")))
        S.cmd_commit_grades(self.dir, p)  # must not raise
        self.assertEqual(self.rec("alpha")["interval"], 3)

    def test_commit_rejects_an_evidence_free_log(self):
        """A draft with no grades must never advance the course — this is
        what recovery finds after a session that never really happened."""
        p = self.write_log("2026-07-21-2.md", log_text("2"))
        with self.assertRaises(S.IntegrityError):
            S.cmd_commit_grades(self.dir, p)


class TestDraftLog(CourseCase):
    """begin creates the session's log file itself, pinning the token
    mechanically — a tutor whose context is later lost reads the draft
    instead of improvising, and evidence appended mid-session survives."""

    def test_begin_writes_the_draft_with_the_pinned_token(self):
        self.git_init()
        S.cmd_begin(self.dir)
        draft = self.dir / "log" / f"{TODAY}-2.md"
        self.assertTrue(draft.exists())
        text = draft.read_text(encoding="utf-8")
        self.assertIn("session: 2", text)
        for head in ("## taught", "## grades", "## asked",
                     "## open question"):
            self.assertIn(head, text)

    def test_begin_sweeps_wholly_empty_drafts_of_other_sessions(self):
        self.git_init()
        empty = self.dir / "log" / "2026-07-20-2b.md"
        empty.write_text("session: 2b\n\n## taught\n\n## grades\n\n"
                         "## asked\n\n## open question\n", encoding="utf-8")
        asked = self.dir / "log" / "2026-07-20-2b2.md"
        asked.write_text("session: 2b2\n\n## asked\n- a posed case\n",
                         encoding="utf-8")
        S.cmd_begin(self.dir)
        self.assertFalse(empty.exists())
        self.assertTrue(asked.exists())  # a posed question is ledger evidence

    def test_begin_never_clobbers_an_existing_log(self):
        self.git_init()
        p = self.dir / "log" / f"{TODAY}-2.md"
        p.write_text("session: 2\n\n## grades\n- grade: alpha | "
                     "result: pass | note: mine\n", encoding="utf-8")
        S.cmd_begin(self.dir)
        self.assertIn("note: mine", p.read_text(encoding="utf-8"))

    def test_recovery_discards_an_evidence_free_draft(self):
        self.git_init()
        S.cmd_begin(self.dir)
        self.stale("2")
        self.assertEqual(S.cmd_recover(self.dir), "reset")
        self.assertFalse((self.dir / "log" / f"{TODAY}-2.md").exists())

    def test_recovery_replays_a_partial_draft(self):
        """A mid-session crash with one grade already appended commits
        that grade instead of losing the whole session."""
        self.git_init()
        S.cmd_begin(self.dir)
        draft = self.dir / "log" / f"{TODAY}-2.md"
        text = draft.read_text(encoding="utf-8").replace(
            "## grades\n",
            "## grades\n- grade: alpha | result: pass | note: landed\n")
        draft.write_text(text, encoding="utf-8")
        self.stale("2")
        self.assertEqual(S.cmd_recover(self.dir), "replayed")
        self.assertEqual(self.rec("alpha")["interval"], 3)

    def test_recovery_resets_a_wrong_token_draft(self):
        self.git_init()
        self.write_log("2026-07-21-3.md",
                       log_text("3", ("alpha", "pass", "clean")))
        self.stale("3")
        self.assertEqual(S.cmd_recover(self.dir), "reset")

    def stale(self, token):
        p = self.dir / S.SENTINEL
        p.write_text(f"session: {token}\n", encoding="utf-8")
        old = (dt.datetime.now() - dt.timedelta(hours=5)).timestamp()
        os.utime(p, (old, old))


class TestUntaughtMeansUntaught(CourseCase):
    """A tutor whose chat thread persists across days 'remembers' teasers
    and abandoned openers as teaching (2026-09-03: 'what stuck from
    yesterday's five-queue framing?' on a concept never taught). The
    brief says so at the exact moment the confusion forms."""

    def test_begin_disclaims_memory_for_untaught_concepts(self):
        out = S.cmd_begin(self.dir)
        self.assertIn("untaught here: beta", out)
        self.assertIn("untaught means untaught", out)

    def test_no_disclaimer_when_nothing_is_untaught(self):
        self.set_record("beta", status="active", next="2026-08-01")
        out = S.cmd_begin(self.dir)
        self.assertIn("untaught here: -", out)
        self.assertNotIn("untaught means untaught", out)


class TestReplayNeverAdvances(CourseCase):
    """Replaying an abandoned draft used to apply its grades but leave the
    counter alone, so the next begin re-issued the SAME token and that
    session's close was a silent no-op: its grades were thrown away
    (sessions 21, 24, 25, 33 of the live course, 2026-09/10). Now a replay
    banks the draft's grades and attendance, and the slot re-runs under a
    distinct token whose close applies and advances exactly once."""

    def stale(self, token):
        p = self.dir / S.SENTINEL
        p.write_text(f"session: {token}\n", encoding="utf-8")
        old = (dt.datetime.now() - dt.timedelta(hours=5)).timestamp()
        os.utime(p, (old, old))

    def abandon_with_grades(self):
        self.git_init()
        S.cmd_begin(self.dir)
        self.write_log(f"{TODAY}-2.md",
                       log_text("2", ("alpha", "pass", "landed")))
        self.stale("2")

    def header(self):
        return S.parse_plan(self.dir)[0]

    def test_replay_banks_grades_but_the_slot_reruns(self):
        self.abandon_with_grades()
        out = S.cmd_begin(self.dir)
        self.assertIn("session: 2b of", out)
        self.assertEqual(self.rec("alpha")["interval"], 3)
        self.assertEqual(self.header()["next-session"], "2/10")

    def test_replay_counts_the_attendance(self):
        self.abandon_with_grades()
        S.cmd_begin(self.dir)
        self.assertEqual(self.header()["last-attended"], TODAY)
        self.assertEqual(int(self.header()["sessions-done"]), 2)

    def test_the_rerun_close_applies_its_grades_and_advances(self):
        self.abandon_with_grades()
        S.cmd_begin(self.dir)
        p = self.write_log(f"{TODAY}-2b.md",
                           log_text("2b", ("beta", "taught", "intro")))
        out = S.cmd_close(self.dir, p)
        self.assertIn("(applied)", out)
        self.assertEqual(self.rec("beta")["status"], "active")
        self.assertEqual(self.header()["next-session"], "3/10")

    def test_close_never_advances_twice(self):
        """A crash after the counter moved but before the unlock must not
        let a second close (or a replay) skip a slot."""
        self.git_init()
        p = self.write_log(f"{TODAY}-2.md",
                           log_text("2", ("alpha", "pass", "x")))
        S.cmd_close(self.dir, p)
        self.assertEqual(self.header()["next-session"], "3/10")
        (self.dir / S.SENTINEL).write_text("session: 2\n", encoding="utf-8")
        S.cmd_close(self.dir, p)
        self.assertEqual(self.header()["next-session"], "3/10")

    def test_replay_note_says_the_slot_reruns(self):
        self.abandon_with_grades()
        out = S.cmd_begin(self.dir)
        self.assertIn("re-runs", out)
        self.assertNotIn("Nothing to do", out)

    def test_open_question_survives_an_abandoned_draft(self):
        self.git_init()
        self.write_log("2026-07-20-1.md",
                       log_text("1", ("alpha", "pass", "x"),
                                extra="why does alpha precede beta?"))
        S.cmd_begin(self.dir)  # creates an empty session-2 draft
        (self.dir / S.SENTINEL).unlink()
        self.assertIn("open question: why does alpha precede beta?",
                      S.cmd_begin(self.dir))

    def test_begin_never_issues_a_committed_token(self):
        self.set_meta(**{"committed-sessions": ["1", "2"]})
        self.assertIn("session: 2b of", S.cmd_begin(self.dir))
        self.set_meta(**{"committed-sessions": ["1", "2", "2b"]})
        (self.dir / S.SENTINEL).unlink()
        self.assertIn("session: 2b2 of", S.cmd_begin(self.dir))


class TestCoverageIsAUnitCondition(CourseCase):
    """A unit used to be 'taught' when its last slot passed, whatever was
    covered. Unit 4 of the live course ended with neocloud-model never
    taught, and units 2-4 ended without a graded teach-back; nothing ever
    noticed. Now unit status follows content, the unit-end slot yields to
    an untaught concept, and an ended unit's leftovers are owed: taught in
    catch-up sessions that never consume a plan slot."""

    def at(self, n):
        S.write_plan_header(self.dir, {"next-session": f"{n}/10"})

    def rubric_log(self):
        # session 1 is committed in the fixture; this is its teach-back
        self.write_log("2026-07-19-1.md",
                       log_text("1", ("alpha", "rubric-pass", "x")))

    def test_unit_end_slot_yields_to_an_untaught_unit_concept(self):
        self.at(3)
        out = S.cmd_begin(self.dir)
        self.assertIn("type: standard", out)
        self.assertIn("teach: beta", out)

    def test_unit_with_an_untaught_concept_stays_in_progress(self):
        self.git_init()
        self.at(3)
        p = self.write_log(f"{TODAY}-3.md",
                           log_text("3", ("alpha", "pass", "x")))
        S.cmd_close(self.dir, p)
        unit1 = S.parse_plan(self.dir)[1][0]
        self.assertEqual(unit1["status"], "in-progress")

    def test_stranded_concept_gets_a_catch_up_session(self):
        self.rubric_log()
        self.at(4)
        out = S.cmd_begin(self.dir)
        self.assertIn("type: catch-up", out)
        self.assertIn("session: 4r of", out)
        self.assertIn("teach: beta", out)
        self.assertIn("the second thing", out)  # the concept's def line

    def test_catch_up_never_advances_and_clears_its_debt(self):
        self.git_init()
        self.rubric_log()
        self.at(4)
        S.cmd_begin(self.dir)
        p = self.write_log(f"{TODAY}-4r.md",
                           log_text("4r", ("beta", "taught", "intro")))
        S.cmd_close(self.dir, p)
        self.assertEqual(S.parse_plan(self.dir)[0]["next-session"], "4/10")
        self.assertEqual(S.parse_plan(self.dir)[1][0]["status"], "taught")
        self.assertIn("type: standard", S.cmd_begin(self.dir))

    def test_ended_unit_without_a_teach_back_owes_one(self):
        self.set_record("beta", status="active", next="2026-08-01")
        self.at(4)
        out = S.cmd_begin(self.dir)
        self.assertIn("type: catch-up", out)
        self.assertIn("teach-back: alpha", out)

    def test_any_rubric_grade_settles_the_teach_back(self):
        self.set_record("beta", status="active", next="2026-08-01")
        self.rubric_log()
        self.at(4)
        self.assertIn("type: standard", S.cmd_begin(self.dir))

    def test_whole_concepts_are_owed_before_teach_backs(self):
        self.at(4)  # beta untaught AND alpha never teach-backed
        self.assertIn("teach: beta", S.cmd_begin(self.dir))


class TestVariedReview(CourseCase):
    """Every teaching session used to open with exactly two review items,
    always the freshest concepts: predictable, and units 1-3 of the live
    course went unreviewed for six weeks while 19 of 23 concepts sat
    overdue. Now the shape is drawn per session (deterministically from
    the token, so two agents agree) and the queue alternates fresh and
    most-overdue items."""

    def setUp(self):
        super().setUp()
        os.environ.pop("ARISTOTLE_REVIEW_PLAN", None)

    def test_a_teach_back_brief_names_its_keystone_and_draws_a_shape(self):
        self.settle()
        self.set_record("beta", status="active", next="2026-07-01")
        os.environ["ARISTOTLE_REVIEW_PLAN"] = "exit:1"
        S.write_plan_header(self.dir, {"next-session": "3/10"})
        out = S.cmd_begin(self.dir)
        self.assertIn("type: teach-back", out)
        self.assertIn("teach-back: alpha", out)
        self.assertIn("quiz these (1)", out)

    def test_plan_is_deterministic_per_token(self):
        self.assertEqual(S.review_plan(self.dir, "17", None),
                         S.review_plan(self.dir, "17", None))

    def test_plans_vary_and_none_is_occasional(self):
        shapes = [S.review_plan(self.dir, str(n), None) for n in range(400)]
        self.assertGreaterEqual(len(set(shapes)), 5)
        nones = sum(1 for s in shapes if s[0] == "none") / len(shapes)
        self.assertTrue(0.05 < nones < 0.2, nones)
        mean = sum(s[1] for s in shapes) / len(shapes)
        self.assertTrue(1.1 < mean < 1.5, mean)

    def test_none_never_twice_in_a_row(self):
        for n in range(400):
            self.assertNotEqual(S.review_plan(self.dir, str(n), "none")[0],
                                "none")

    def test_brief_states_the_shape_and_queues_that_many(self):
        os.environ["ARISTOTLE_REVIEW_PLAN"] = "exit:1"
        self.set_record("beta", status="active", next="2026-07-01")
        out = S.cmd_begin(self.dir)
        self.assertIn("review: 1 · as an exit ticket", out)
        self.assertIn("quiz these (1)", out)

    def test_a_none_session_queues_nothing(self):
        os.environ["ARISTOTLE_REVIEW_PLAN"] = "none"
        out = S.cmd_begin(self.dir)
        self.assertIn("review: none", out)
        self.assertIn("quiz these (0)", out)

    def test_the_previous_plan_comes_from_the_last_brief(self):
        os.environ["ARISTOTLE_REVIEW_PLAN"] = "none"
        S.cmd_begin(self.dir)
        self.assertEqual(S._previous_review(self.dir), "none")

    def test_queue_alternates_fresh_and_most_overdue(self):
        self.set_record("alpha", status="active", interval=1,
                        last="2026-07-20", next="2026-07-21")
        self.set_record("beta", status="active", interval=7,
                        last="2026-07-04", next="2026-07-11")  # 10d late
        self.set_record("gamma", status="active", interval=16,
                        last="2026-06-30", next="2026-07-16")  # 5d late
        self.set_record("delta", status="active", interval=1,
                        last="2026-07-19", next="2026-07-20")
        q = S.build_queue(self.dir, cap=2, lead="fresh")
        self.assertEqual(q[0] in ("alpha", "delta"), True)
        self.assertEqual(q[1], "beta")
        self.assertEqual(S.build_queue(self.dir, cap=1, lead="backlog"),
                         ["beta"])

    def test_off_queue_grade_warns_at_close(self):
        self.git_init()
        os.environ["ARISTOTLE_REVIEW_PLAN"] = "open:1"
        self.set_record("beta", status="active", next="2026-07-01")
        S.cmd_begin(self.dir)
        draft = self.dir / "log" / f"{TODAY}-2.md"
        text = draft.read_text(encoding="utf-8").replace(
            "## grades\n", "## grades\n- grade: alpha | result: pass | "
            "note: off the brief\n- grade: beta | result: pass | note: ok\n")
        draft.write_text(text, encoding="utf-8")
        out = S.cmd_close(self.dir, draft)
        self.assertIn("warn:", out)
        self.assertIn("alpha", out.split("warn:")[1])


class TestOwedMaterial(CourseCase):
    """Sessions rightly skip material (`without:`), but 58 such skips in
    the live course were never repaid — the same omission re-recorded up
    to seven times. owed.md is the course author's repayment agenda; the
    brief offers one open item per concept the session touches, and close
    ticks it only when that concept got a coverage line."""

    def owe(self, *lines):
        (self.dir / "owed.md").write_text(
            "# owed\n" + "".join(f"- [ ] {l}\n" for l in lines),
            encoding="utf-8")

    def test_the_brief_offers_one_item_for_a_queued_concept(self):
        self.owe("alpha | the second-order case", "alpha | the third case")
        out = S.cmd_begin(self.dir)  # alpha is due in the fixture
        self.assertIn("owed: alpha — the second-order case", out)
        self.assertNotIn("the third case", out)

    def test_close_ticks_an_offered_item_that_got_coverage(self):
        self.git_init()
        self.owe("alpha | the second-order case")
        S.cmd_begin(self.dir)
        draft = self.dir / "log" / f"{TODAY}-2.md"
        text = draft.read_text(encoding="utf-8")
        text = text.replace("## taught\n",
                            "## taught\n- alpha: owed: the second-order case\n")
        text = text.replace("## grades\n",
                            "## grades\n- grade: alpha | result: pass | note: x\n")
        draft.write_text(text, encoding="utf-8")
        S.cmd_close(self.dir, draft)
        self.assertIn("- [x] alpha", (self.dir / "owed.md").read_text())

    def test_unoffered_items_are_never_ticked(self):
        self.git_init()
        self.owe("delta | not offered today")
        S.cmd_begin(self.dir)
        p = self.write_log(f"{TODAY}-2.md",
                           log_text("2", ("beta", "taught", "intro")))
        S.cmd_close(self.dir, p)
        self.assertIn("- [ ] delta", (self.dir / "owed.md").read_text())

    def test_owe_validates_the_concept_and_appends(self):
        S.cmd_owe(self.dir, "beta", "the cost walk")
        self.assertIn("- [ ] beta | the cost walk",
                      (self.dir / "owed.md").read_text())
        with self.assertRaises(S.IntegrityError):
            S.cmd_owe(self.dir, "nope", "x")


class TestSecondReview(CourseCase):
    """Findings of the 2026-10-20 whole-system review, pinned."""

    def stale(self, token):
        p = self.dir / S.SENTINEL
        p.write_text(f"session: {token}\n", encoding="utf-8")
        old = (dt.datetime.now() - dt.timedelta(hours=5)).timestamp()
        os.utime(p, (old, old))

    def at(self, n):
        S.write_plan_header(self.dir, {"next-session": f"{n}/10"})

    # 1. review density follows the backlog
    def test_a_big_backlog_draws_heavier_but_still_varied(self):
        os.environ.pop("ARISTOTLE_REVIEW_PLAN", None)
        heavy = [S.review_plan(self.dir, str(n), None, due=12)
                 for n in range(400)]
        mean = sum(n for _, n in heavy) / len(heavy)
        self.assertTrue(1.6 < mean < 1.9, mean)
        self.assertIn(("none", 0), heavy)      # variety survives
        light = [S.review_plan(self.dir, str(n), None, due=1)
                 for n in range(400)]
        self.assertLess(sum(n for _, n in light) / 400, mean)

    # 2. a graded draft orphaned by the went-quiet path is not lost
    def test_begin_banks_an_unclosed_graded_draft_with_no_lock(self):
        self.git_init()
        S.cmd_begin(self.dir)
        draft = self.dir / "log" / f"{TODAY}-2.md"
        draft.write_text(draft.read_text(encoding="utf-8").replace(
            "## grades\n", "## grades\n- grade: alpha | result: pass | "
            "note: landed\n"), encoding="utf-8")
        (self.dir / S.SENTINEL).unlink()       # "went quiet" path
        out = S.cmd_begin(self.dir)
        self.assertEqual(self.rec("alpha")["interval"], 3)
        self.assertIn("session: 2b of", out)

    # 3. teach-back debt: dropped keystones, and the wrong grade warns
    def test_a_dropped_keystone_owes_no_teach_back(self):
        self.set_record("beta", status="active", next="2026-08-30")
        self.set_record("alpha", status="dropped")
        self.at(4)
        self.assertNotIn("catch-up", S.cmd_begin(self.dir))

    def test_a_briefed_teach_back_left_ungraded_warns(self):
        """A wrong grade is refused (TestThirdReview); a teach-back that
        never got graded at all still closes, with a warning."""
        self.git_init()
        self.set_record("beta", status="active", next="2026-07-01")
        self.at(4)
        os.environ["ARISTOTLE_REVIEW_PLAN"] = "open:1"
        S.cmd_begin(self.dir)
        p = self.dir / "log" / f"{TODAY}-4r.md"   # keep begin's brief
        p.write_text(p.read_text(encoding="utf-8").replace(
            "## grades\n", "## grades\n- grade: beta | result: pass | "
            "note: review only\n"), encoding="utf-8")
        out = S.cmd_close(self.dir, p)
        self.assertIn("teach-back", out.split("warn:", 1)[-1])

    # 4. "asked recently" spans sessions, not files
    def test_recent_asks_span_three_sessions_not_three_files(self):
        for name, tok, item in [("2026-07-15-1", "1", "case one"),
                                ("2026-07-16-2", "2", "case two"),
                                ("2026-07-17-3", "3", "case three a"),
                                ("2026-07-18-3b", "3b", "case three b"),
                                ("2026-07-19-3b2", "3b2", "case three c")]:
            self.write_log(f"{name}.md", f"session: {tok}\n\n## asked\n"
                           f"- {item}\n")
        recent, _ = S._asked_history(self.dir)
        items = [i for _, i in recent]
        self.assertIn("case one", items)

    # 5. only an explicitly marked line repays an owed item
    def test_a_plain_coverage_line_does_not_tick_owed(self):
        self.git_init()
        (self.dir / "owed.md").write_text("- [ ] alpha | the case\n",
                                          encoding="utf-8")
        S.cmd_begin(self.dir)
        draft = self.dir / "log" / f"{TODAY}-2.md"
        text = draft.read_text(encoding="utf-8").replace(
            "## taught\n", "## taught\n- alpha: some other correction\n"
        ).replace("## grades\n",
                  "## grades\n- grade: alpha | result: pass | note: x\n")
        draft.write_text(text, encoding="utf-8")
        S.cmd_close(self.dir, draft)
        self.assertIn("- [ ] alpha", (self.dir / "owed.md").read_text())

    # 6. a requires: clause must not hide an invalid distractor
    def test_requires_is_parsed_off_the_distractor(self):
        a = S.parse_assets("## concept: alpha\n- quiz: q | a: k | "
                           "distractor: M1 | requires: the case\n")
        self.assertEqual(a["concepts"]["alpha"]["quiz"][0]["distractor"],
                         "M1")

    # 7. replaying a catch-up says so
    def test_replayed_catch_up_note_does_not_promise_a_rerun(self):
        self.git_init()
        self.set_record("beta", status="active", next="2026-08-30")
        self.at(4)
        S.cmd_begin(self.dir)
        self.write_log(f"{TODAY}-4r.md",
                       log_text("4r", ("beta", "pass", "x")))
        self.stale("4r")
        out = S.cmd_begin(self.dir)
        self.assertIn("catch-up", out.split("NOTE:", 1)[-1])

    # 8. a review session does not reset the never-none-twice guard
    def test_previous_review_skips_non_teaching_briefs(self):
        for name, rev in [("2026-07-18-1.md", "none"),
                          ("2026-07-19-1b.md", "-")]:
            self.write_log(name, f"session: 1\n<!-- brief: review={rev} "
                           "quiz=- teach=- owed=- -->\n")
        self.assertEqual(S._previous_review(self.dir), "none")

    # 9. reset recovery discards session debris only
    def test_reset_keeps_work_outside_the_session(self):
        self.git_init()
        S._commit(self.dir, "base")
        new = self.dir / "assets" / "unit-03.md"
        new.write_text("draft unit\n", encoding="utf-8")
        a1 = self.dir / "assets" / "unit-01.md"
        a1.write_text(a1.read_text(encoding="utf-8") + "\n<!-- edit -->\n",
                      encoding="utf-8")
        self.stale("2")
        self.assertEqual(S.cmd_recover(self.dir), "reset")
        self.assertTrue(new.exists())
        self.assertIn("<!-- edit -->", a1.read_text(encoding="utf-8"))

    # 10. the final session is never pre-empted by catch-up
    def test_owed_items_never_preempt_the_final_session(self):
        self.at(10)
        self.assertNotEqual(S.dispatch(self.dir)["type"], "catch-up")

    # 11. the presented block shows recent coverage, not all of it
    def test_presented_block_is_capped(self):
        for i in range(5):
            self.write_log(f"2026-07-1{i}-x{i}.md",
                           f"session: 1\n\n## taught\n- alpha: entry {i}\n")
        out = S.cmd_begin(self.dir)
        self.assertIn("entry 4", out)
        self.assertNotIn("entry 0", out)
        self.assertIn("older", out)

    # 13. a session's own teach-back target is never also a review item
    def test_teach_back_keystone_is_not_queued_for_review(self):
        self.settle()
        self.set_record("alpha", status="active", next="2026-07-01")
        os.environ["ARISTOTLE_REVIEW_PLAN"] = "open:2"
        self.at(3)
        out = S.cmd_begin(self.dir)
        quiz = [l for l in out.splitlines() if l.startswith("quiz these")][0]
        self.assertNotIn("alpha", quiz)

    # 12. review sessions build fresh cases: no bank line
    def test_review_session_brief_has_no_bank_line(self):
        (self.dir / "plan.md").write_text(REVIEW_PLAN_MD, encoding="utf-8")
        self.settle("alpha")
        self.assertNotIn("banks spendable", S.cmd_begin(self.dir))


class TestThirdReview(CourseCase):
    """Findings of the fresh 2026-10-20 review, pinned."""

    def stale(self, token):
        p = self.dir / S.SENTINEL
        p.write_text(f"session: {token}\n", encoding="utf-8")
        old = (dt.datetime.now() - dt.timedelta(hours=5)).timestamp()
        os.utime(p, (old, old))

    def at(self, n):
        S.write_plan_header(self.dir, {"next-session": f"{n}/10"})

    def hdr(self):
        return S.parse_plan(self.dir)[0]

    # 1. blocker: a briefed teach-back must be graded with a rubric result
    def test_close_refuses_a_non_rubric_grade_on_a_briefed_teach_back(self):
        self.git_init()
        self.set_record("beta", status="active", next="2026-08-30")
        self.at(4)
        S.cmd_begin(self.dir)
        draft = self.dir / "log" / f"{TODAY}-4r.md"
        draft.write_text(draft.read_text(encoding="utf-8").replace(
            "## grades\n", "## grades\n- grade: alpha | result: pass | "
            "note: x\n"), encoding="utf-8")
        with self.assertRaises(S.IntegrityError) as cm:
            S.cmd_close(self.dir, draft)
        self.assertIn("rubric", str(cm.exception))
        self.assertEqual(self.rec("alpha")["interval"], 1)  # nothing applied

    # 4. closing an already-replayed log never skips the re-run slot
    def test_closing_a_replayed_log_does_not_advance(self):
        self.git_init()
        S.cmd_begin(self.dir)
        draft = self.dir / "log" / f"{TODAY}-2.md"
        draft.write_text(draft.read_text(encoding="utf-8").replace(
            "## grades\n", "## grades\n- grade: alpha | result: pass | "
            "note: x\n"), encoding="utf-8")
        self.stale("2")
        self.assertEqual(S.cmd_recover(self.dir), "replayed")
        S.cmd_close(self.dir, draft)
        self.assertEqual(self.hdr()["next-session"], "2/10")

    # 5. recovery paths repay owed items and refresh status like close
    def test_banked_draft_ticks_its_owed_item(self):
        self.git_init()
        (self.dir / "owed.md").write_text("- [ ] alpha | the case\n",
                                          encoding="utf-8")
        S.cmd_begin(self.dir)
        draft = self.dir / "log" / f"{TODAY}-2.md"
        draft.write_text(draft.read_text(encoding="utf-8").replace(
            "## taught\n", "## taught\n- alpha: owed: the case\n").replace(
            "## grades\n", "## grades\n- grade: alpha | result: pass | "
            "note: x\n"), encoding="utf-8")
        (self.dir / S.SENTINEL).unlink()
        S.cmd_begin(self.dir)
        self.assertIn("- [x] alpha", (self.dir / "owed.md").read_text())

    # 13. a replayed session is dated by its log, not the recovery day
    def test_replay_dates_attendance_by_the_log(self):
        self.git_init()
        self.write_log("2026-07-19-2.md",
                       log_text("2", ("alpha", "pass", "x")))
        self.stale("2")
        S.cmd_recover(self.dir)
        self.assertEqual(self.hdr()["last-attended"], "2026-07-19")

    # 2/3. lifecycle has engine paths
    def test_re_entry_wins_over_a_dormant_gap(self):
        S.write_plan_header(self.dir, {"last-attended": "2026-06-01",
                                       "re-entry-pending": "yes"})
        self.assertEqual(S.dispatch(self.dir)["type"], "re-entry")

    def test_status_verb_resumes_with_re_entry(self):
        self.git_init()
        S.cmd_status(self.dir, "paused")
        self.assertEqual(self.hdr()["course-status"], "paused")
        S.cmd_status(self.dir, "active")
        self.assertEqual(self.hdr()["course-status"], "active")
        self.assertEqual(self.hdr()["re-entry-pending"], "yes")
        with self.assertRaises(S.IntegrityError):
            S.cmd_status(self.dir, "bogus")

    def test_graduation_begin_neither_locks_nor_queues(self):
        self.git_init()
        self.at(11)
        out = S.cmd_begin(self.dir)
        self.assertIn("type: graduation", out)
        self.assertNotIn("quiz these", out)
        self.assertFalse((self.dir / S.SENTINEL).exists())
        self.assertIn("left untaught", out)      # named, not hidden

    def test_maintenance_runs_non_advancing_review(self):
        self.git_init()
        S.write_plan_header(self.dir, {"course-status": "maintenance",
                                       "next-session": "11/10"})
        out = S.cmd_begin(self.dir)
        self.assertIn("type: maintenance", out)
        self.assertIn("session: 11r of", out)

    # 7. the final synthesis reviews what has faded, not what is fresh
    def test_terminal_queue_prefers_the_most_faded(self):
        self.set_record("alpha", status="active", interval=1,
                        last="2026-07-20", next="2026-07-21")
        self.set_record("beta", status="active", interval=7,
                        last="2026-05-01", next="2026-05-08")
        q = S.build_queue(self.dir, cap=1, terminal=True)
        self.assertEqual(q, ["beta"])

    # 8. catch-ups say where they are in the run
    def test_catch_up_brief_carries_a_bookend_label(self):
        self.at(4)   # beta untaught + alpha never teach-backed: 2 owed
        out = S.cmd_begin(self.dir)
        self.assertIn("bookend: Session 4 · catch-up 1 of 2", out)

    # 9. the checkpoint is surfaced, not left to arithmetic
    def test_checkpoint_due_is_printed(self):
        S.write_plan_header(self.dir, {"sessions-done": "6"})
        self.assertIn("checkpoint: due at this close", S.cmd_begin(self.dir))

    # 10. the brief points at the sections to read, not whole files
    def test_brief_names_asset_sections_to_read(self):
        out = S.cmd_begin(self.dir)
        self.assertRegex(out, r"read: assets/unit-01\.md lines \d+-\d+ "
                              r"\(beta\)")

    # 12. a deterministic pointer for the cron
    def test_pointer_prints_session_and_open_question(self):
        self.write_log("2026-07-20-1.md",
                       log_text("1", ("alpha", "pass", "x"), extra="why?"))
        out = S.cmd_pointer(self.dir)
        self.assertIn("session: 2/10", out)
        self.assertIn("open-question: why?", out)


class TestFourthReview(CourseCase):
    """Findings of the gpt-6-astra review (2026-10-20), pinned."""

    def stale(self, token):
        p = self.dir / S.SENTINEL
        p.write_text(f"session: {token}\n", encoding="utf-8")
        old = (dt.datetime.now() - dt.timedelta(hours=5)).timestamp()
        os.utime(p, (old, old))

    def at(self, n):
        S.write_plan_header(self.dir, {"next-session": f"{n}/10"})

    def hdr(self):
        return S.parse_plan(self.dir)[0]

    # recovery keeps the ledger: a posed question survives a reset
    def test_reset_keeps_a_draft_that_posed_questions(self):
        self.git_init()
        d = self.dir / "log" / f"{TODAY}-2.md"
        d.write_text("session: 2\n\n## asked\n- alpha.q1\n",
                     encoding="utf-8")
        self.stale("2")
        self.assertEqual(S.cmd_recover(self.dir), "reset")
        self.assertTrue(d.exists())

    # a close interrupted after its grades landed is finished, exactly once
    def test_an_interrupted_close_is_finished_by_recovery(self):
        self.git_init()
        (self.dir / "owed.md").write_text("- [ ] alpha | the case\n",
                                          encoding="utf-8")
        S.cmd_begin(self.dir)
        draft = self.dir / "log" / f"{TODAY}-2.md"
        draft.write_text(draft.read_text(encoding="utf-8").replace(
            "## taught\n", "## taught\n- alpha: owed: the case\n").replace(
            "## grades\n", "## grades\n- grade: alpha | result: pass | "
            "note: x\n"), encoding="utf-8")
        # crash: the journal is written and grades applied, nothing else
        (self.dir / S.CLOSE_JOURNAL).write_text(
            f"session: 2\nlog: log/{draft.name}\n", encoding="utf-8")
        S.cmd_commit_grades(self.dir, draft)
        self.stale("2")
        S.cmd_recover(self.dir)
        self.assertEqual(self.hdr()["next-session"], "3/10")
        self.assertIn("- [x] alpha", (self.dir / "owed.md").read_text())
        self.assertFalse((self.dir / S.CLOSE_JOURNAL).exists())
        self.assertFalse((self.dir / S.SENTINEL).exists())

    # evidence is dated by the lesson, not the recovery
    def test_replayed_grades_carry_the_lesson_date(self):
        self.git_init()
        self.write_log("2026-07-19-2.md",
                       log_text("2", ("alpha", "pass", "x")))
        self.stale("2")
        S.cmd_recover(self.dir)
        self.assertEqual(self.rec("alpha")["last"], "2026-07-19")

    # the teach-back brief carries its rubric and its coverage
    def test_teach_back_brief_reads_the_rubric_and_shows_coverage(self):
        self.set_record("beta", status="active", next="2026-08-30")
        self.write_log("2026-07-18-1.md", "session: 1\n\n## taught\n"
                       "- alpha: the first thing shown\n")
        self.at(4)
        out = S.cmd_begin(self.dir)
        self.assertRegex(out, r"read: assets/unit-01\.md lines \d+-\d+ "
                              r"\(rubric alpha\)")
        self.assertIn("alpha [1]: the first thing shown", out)

    def test_standard_brief_points_at_the_interleaved_set(self):
        out = S.cmd_begin(self.dir)
        self.assertRegex(out, r"read: assets/unit-01\.md lines \d+-\d+ "
                              r"\(interleaved\)")

    # the brief survives a context loss
    def test_resume_reprints_the_live_brief(self):
        self.git_init()
        out = S.cmd_begin(self.dir)
        self.assertEqual(S.cmd_resume(self.dir), out)
        p = self.write_log(f"{TODAY}-2.md",
                           log_text("2", ("beta", "taught", "x")))
        S.cmd_close(self.dir, p)
        with self.assertRaises(S.IntegrityError):
            S.cmd_resume(self.dir)

    # the cron sees what dispatch sees
    def test_pointer_reports_the_effective_session_type(self):
        S.write_plan_header(self.dir, {"last-attended": "2026-06-01"})
        self.assertIn("type: dormant", S.cmd_pointer(self.dir))

    # neglect is bounded
    def test_a_neglected_item_takes_the_first_review_slot(self):
        self.set_record("alpha", status="active", interval=1,
                        last="2026-07-20", next="2026-07-21")
        self.set_record("beta", status="active", interval=7,
                        last="2026-06-01", next="2026-06-08")
        self.assertEqual(S.build_queue(self.dir, cap=1, lead="fresh"),
                         ["beta"])

    def test_no_none_session_while_something_is_neglected(self):
        self.set_record("beta", status="active", interval=7,
                        last="2026-06-01", next="2026-06-08")
        os.environ.pop("ARISTOTLE_REVIEW_PLAN", None)
        shapes = {S.review_plan(self.dir, str(n), None, due=1,
                                neglected=True) for n in range(300)}
        self.assertNotIn(("none", 0), shapes)

    # graduation names unpaid owed material too
    def test_graduation_lists_unpaid_owed_material(self):
        self.git_init()
        (self.dir / "owed.md").write_text("- [ ] alpha | the deep case\n",
                                          encoding="utf-8")
        self.at(11)
        self.assertIn("the deep case", S.cmd_begin(self.dir))

    # state validation is real
    def test_impossible_dates_fail_validation(self):
        self.set_record("alpha", last="2026-99-99")
        with self.assertRaises(S.FormatError):
            S.load_state(self.dir)

    # resizing is a verb, not a hand-edit
    def test_resize_sets_the_total_and_refuses_impossible_sizes(self):
        self.git_init()
        S.cmd_resize(self.dir, 12)
        self.assertEqual(self.hdr()["next-session"], "2/12")
        with self.assertRaises(S.IntegrityError):
            S.cmd_resize(self.dir, 3)


class TestUnjustFail(CourseCase):
    """A concept cannot fail before it was taught. The pilot's tutor used
    a bank quiz item as the door into an untaught concept; had it graded
    the missed guess 'fail', the learner would have been penalized for a
    lesson that never happened."""

    def test_fail_on_untaught_is_rejected_loudly(self):
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("beta", "fail", "missed the guess")))
        with self.assertRaisesRegex(S.IntegrityError, "cannot fail before"):
            S.cmd_commit_grades(self.dir, p)
        # all-or-nothing: nothing was applied
        self.assertEqual(self.rec("beta")["status"], "untaught")

    def test_taught_after_a_missed_guess_is_the_sanctioned_path(self):
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("beta", "taught",
                                          "guessed SRAM before instruction")))
        S.cmd_commit_grades(self.dir, p)
        r = self.rec("beta")
        self.assertEqual((r["status"], r["interval"]), ("active", 1))

    def test_fail_on_a_taught_concept_still_works(self):
        p = self.write_log("2026-07-21-2.md",
                           log_text("2", ("alpha", "fail", "real lapse")))
        S.cmd_commit_grades(self.dir, p)
        self.assertEqual(self.rec("alpha")["fails"], 1)


class TestAgentFacingErrors(CourseCase):

    def test_wrong_directory_says_what_to_do(self):
        """The clean-room agent hit a bare FileNotFoundError running from
        the wrong cwd. An error an agent cannot act on is a dead end."""
        empty = self.dir / "not-a-course"
        empty.mkdir()
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--course", str(empty), "check"],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not a course directory", r.stderr)
        self.assertIn("--course", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


class TestVisualWarnings(CourseCase):
    """A `- visual:` line in an asset file is a promise that a rendered
    image exists; a dangling one would have the tutor send a broken
    MEDIA path mid-lesson. Advisory, like every course_warnings rule."""

    def add_visual_line(self):
        p = self.dir / "assets" / "unit-01.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "## concept: alpha",
            "## concept: alpha\n- visual: u01-alpha-shape | presents: a",
            1), encoding="utf-8")

    def test_dangling_visual_is_flagged(self):
        self.add_visual_line()
        w = " | ".join(S.course_warnings(self.dir))
        self.assertIn("u01-alpha-shape", w)

    def test_visual_line_parses_through_check(self):
        """The asset parser whitelists fields and hard-errors on unknown
        ones — a course that adds a visual line must still pass check
        (and so still run begin)."""
        self.add_visual_line()
        d = self.dir / "visuals" / "u01-alpha-shape"
        d.mkdir(parents=True)
        (d / "teach.png").write_bytes(b"png")
        S.cmd_check(self.dir)  # must not raise
        assets = S.parse_assets((self.dir / "assets" / "unit-01.md")
                                .read_text(encoding="utf-8"))
        self.assertEqual(assets["concepts"]["alpha"]["visual"],
                         ["u01-alpha-shape"])

    def test_rendered_visual_is_silent(self):
        self.add_visual_line()
        d = self.dir / "visuals" / "u01-alpha-shape"
        d.mkdir(parents=True)
        (d / "teach.png").write_bytes(b"png")
        w = " | ".join(S.course_warnings(self.dir))
        self.assertNotIn("u01-alpha-shape", w)


class TestCourseWarnings(CourseCase):
    """Design rules that `check` advises on but must never fail for —
    every one of these was found broken in a real course before it was
    written down as code."""

    def warns(self):
        return " | ".join(S.course_warnings(self.dir))

    def test_padding_and_missing_scaffolding_are_flagged(self):
        (self.dir / "plan.md").write_text(
            PLAN_MD.replace("sessions: 3\nconcepts: [alpha, beta]",
                            "sessions: 5\nconcepts: [alpha, beta]"),
            encoding="utf-8")
        w = self.warns()
        self.assertIn("padded", w)          # 2 concepts in 5 sessions
        self.assertIn("no README.md", w)
        self.assertIn("history.md", w)

    def test_warnings_never_fail_the_check(self):
        self.assertEqual(S.cmd_check(self.dir), "ok")
        self.assertTrue(S.course_warnings(self.dir))

    def test_a_well_shaped_course_is_quiet(self):
        p = self.dir / "plan.md"
        p.write_text(PLAN_MD
                     .replace("sessions: 3\nconcepts: [alpha, beta]",
                              "sessions: 3\nconcepts: [alpha, beta, delta]")
                     .replace("sessions: 3\nconcepts: [gamma, delta]",
                              "sessions: 2\nconcepts: [gamma]")
                     .replace("## Unit 2: What is gamma for?",
                              "## Review: unit 1 mixed\nsessions: 1\n\n"
                              "## Unit 2: What is gamma for?")
                     .replace("next-session: 2/10", "next-session: 2/7"),
                     encoding="utf-8")
        self.add_u2_assets()
        (self.dir / "README.md").write_text("x", encoding="utf-8")
        (self.dir / "history.md").write_text("x", encoding="utf-8")
        (self.dir / "templates").mkdir(exist_ok=True)
        (self.dir / "templates" / "log.md").write_text("x", encoding="utf-8")
        self.assertEqual(S.course_warnings(self.dir), [])

    def test_missing_log_template_is_flagged(self):
        self.assertIn("templates/log.md", " | ".join(
            S.course_warnings(self.dir)))

    def test_ignored_plan_section_claiming_sessions_is_flagged(self):
        """A clean-room bootstrap wrote '## Terminal synthesis' with a
        sessions: line. Only Unit/Review blocks consume sessions, so it
        was silently dropped — honest here, wrong at any other count."""
        p = self.dir / "plan.md"
        p.write_text(PLAN_MD + "\n## Terminal synthesis: defend it\n"
                     "sessions: 1\n", encoding="utf-8")
        self.assertIn("scheduler ignores it", self.warns())

    def test_prose_sections_without_sessions_are_fine(self):
        p = self.dir / "plan.md"
        p.write_text(PLAN_MD + "\n## Review design\nrolling, not stacked\n",
                     encoding="utf-8")
        self.assertNotIn("scheduler ignores it", self.warns())

    def test_keystone_without_misconceptions_is_flagged(self):
        import re as _re
        stripped = _re.sub(r"misconceptions:\n(?:  M\d+: .*\n)+", "",
                           MAP_MD, count=1)
        self.assertNotIn("the common wrong model", stripped)   # fixture sanity
        (self.dir / "domain-map.md").write_text(stripped, encoding="utf-8")
        self.assertIn("nothing to warn against", self.warns())


if __name__ == "__main__":
    unittest.main()
