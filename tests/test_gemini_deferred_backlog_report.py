"""Offline invariants for the deferred Gemini backlog diagnostic."""
import copy
import hashlib
import unittest

from astra_v2.gemini_deferred_archive import ARCHIVE_STATUS, _encoded
from astra_v2.gemini_deferred_backlog_report import (
    REPORT_STATUS, build_backlog_report,
)
from astra_v2.gemini_deferred_retry_queue import empty_retry_state


def make_archive():
    entries = []
    for cid in ("blocked", "clear", "also-clear"):
        story = {"kind": "microfiction", "content_id": cid,
                 "title": "Private proposal " + cid}
        entries.append({
            "source_sha256": hashlib.sha256(_encoded(story)).hexdigest(),
            "content_id": cid, "review_status": "deferred_unreviewed",
            "deferred_reason": "review_deferred:rate_limited",
            "source_run_id": "123", "proposal": story,
        })
    return {"version": 1, "status": ARCHIVE_STATUS,
            "publication_approval": False,
            "eligible_for_automatic_publishing": False,
            "entries": entries}


class DeferredBacklogReportTests(unittest.TestCase):
    def test_ranks_retry_eligible_clear_drafts_first_without_approval(self):
        archive = make_archive()
        before = copy.deepcopy(archive)
        def gate(story, history):
            return ["publication_renderer_incompatible: private detail"] if story["content_id"] == "blocked" else []
        report, state = build_backlog_report(
            archive, [], empty_retry_state(), now=100, cooldown_seconds=0,
            checker=gate)
        self.assertEqual(report["status"], REPORT_STATUS)
        self.assertEqual(report["source_count"], 3)
        self.assertEqual(report["retry_eligible_count"], 3)
        self.assertEqual(report["ranking"][0]["content_id"], "clear")
        self.assertEqual(report["ranking"][1]["content_id"], "also-clear")
        blocked = report["ranking"][2]
        self.assertEqual(blocked["content_id"], "blocked")
        self.assertEqual(blocked["blocker_categories"], ["renderer_incompatible"])
        self.assertEqual(blocked["local_check_status"], "blocked")
        self.assertEqual([row["rank"] for row in report["ranking"]], [1, 2, 3])
        self.assertEqual(archive, before)
        self.assertEqual([row["attempts"] for row in state["entries"]], [0, 0, 0])
        for key in ("provider_requests_enabled", "editorial_approval",
                    "publication_approval", "eligible_for_automatic_publishing",
                    "publication_triggered"):
            self.assertFalse(report[key])

    def test_cooldown_is_visible_and_not_consumed_by_reporting(self):
        archive = make_archive()
        report, state = build_backlog_report(
            archive, [], empty_retry_state(), now=100,
            cooldown_seconds=3600, checker=lambda story, history: [])
        self.assertEqual(report["retry_eligible_count"], 0)
        self.assertTrue(all(not row["retry_eligible"] for row in report["ranking"]))
        self.assertTrue(all(row["attempts_so_far"] == 0 for row in report["ranking"]))
        self.assertEqual(len(state["entries"]), 3)

    def test_checker_failure_is_unavailable_not_clear(self):
        def fail(*args):
            raise RuntimeError("provider secret must not leak")
        report, _ = build_backlog_report(
            make_archive(), [], now=100, cooldown_seconds=0, checker=fail)
        self.assertEqual(report["local_check_unavailable_count"], 3)
        self.assertEqual(report["local_checks_clear_count"], 0)
        self.assertNotIn("secret", str(report))
        self.assertNotIn("Private proposal", str(report))

    def test_unavailable_checks_rank_below_known_blockers(self):
        archive = make_archive()
        def gate(story, history):
            if story["content_id"] == "clear":
                return []
            if story["content_id"] == "blocked":
                return ["publication_renderer_incompatible: private detail"]
            raise RuntimeError("local checker unavailable")
        report, _ = build_backlog_report(
            archive, [], now=100, cooldown_seconds=0, checker=gate)
        self.assertEqual(
            [row["content_id"] for row in report["ranking"]],
            ["clear", "blocked", "also-clear"],
        )
        self.assertEqual(report["ranking"][1]["local_check_status"], "blocked")
        self.assertEqual(report["ranking"][2]["local_check_status"], "unavailable")
        self.assertEqual(report["ranking"][2]["blocker_category_count"], 0)

    def test_hash_or_archive_metadata_tampering_fails_closed(self):
        archive = make_archive()
        changed = copy.deepcopy(archive)
        changed["entries"][0]["proposal"]["title"] = "tampered"
        with self.assertRaises(ValueError):
            build_backlog_report(changed, [], now=100, checker=lambda s, h: [])
        promoted = copy.deepcopy(archive)
        promoted["publication_approval"] = True
        with self.assertRaises(ValueError):
            build_backlog_report(promoted, [], now=100, checker=lambda s, h: [])


if __name__ == "__main__":
    unittest.main()
