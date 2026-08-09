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


def log_text(session, *grades, extra=""):
    body = "\n".join(
        f"- grade: {cid} | result: {res} | note: {note}"
        for cid, res, note in grades)
    return (f"session: {session}\n\n## taught\nstuff\n\n"
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

    def test_pass_climbs_the_ladder(self):
        self.grade("alpha", "pass")
        self.assertEqual(self.rec("alpha")["interval"], 3)

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
        for cid in ("beta", "gamma", "delta"):
            self.set_record(cid, status="active", next="2026-07-01")
        self.assertIn("quiz these (3)", S.cmd_begin(self.dir))

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
        self.git_init()
        (self.dir / "scratch.md").write_text("debris", encoding="utf-8")
        self.stale("2")
        self.assertEqual(S.cmd_recover(self.dir), "reset")
        self.assertFalse((self.dir / "scratch.md").exists())

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
        r = self.cli("check")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "ok"))

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


if __name__ == "__main__":
    unittest.main()
