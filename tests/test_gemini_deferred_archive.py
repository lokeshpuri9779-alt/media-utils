"""Offline tests: deferred Gemini drafts never become publication inventory."""
import json
import unittest

from astra_v2.gemini_deferred_archive import (
    build_archive, ARCHIVE_STATUS, MAX_ENTRIES,
)


def candidate(i):
    return {"content_id": "story-" + str(i), "kind": "microfiction",
            "production_ready": True, "title": "Draft " + str(i)}


def batch(stories, issues, approved=None):
    if approved is None:
        approved = [False] * len(stories)
    return ({"status": "unreviewed", "stories": stories},
            {"reviews": [
                {"content_id": story["content_id"], "approved": flag,
                 "issues": row}
                for story, flag, row in zip(stories, approved, issues)
            ]})


class GeminiDeferredArchiveTests(unittest.TestCase):
    def test_only_deferred_stories_are_preserved_as_review_only(self):
        stories = [candidate(i) for i in range(4)]
        p, audit = batch(stories, [
            ["review_deferred:provider_unavailable"],
            ["ai_editorial_rejection"],
            [],
            ["review_deferred:rate_limited"],
        ], approved=[False, False, True, False])
        archive, added = build_archive(p, audit, run_id="12345")
        self.assertEqual(added, 2)
        self.assertEqual([x["content_id"] for x in archive["entries"]],
                         ["story-0", "story-3"])
        self.assertTrue(all(x["review_status"] == "deferred_unreviewed"
                            for x in archive["entries"]))
        self.assertEqual(archive["status"], ARCHIVE_STATUS)
        self.assertFalse(archive["publication_approval"])
        self.assertFalse(archive["eligible_for_automatic_publishing"])
        self.assertNotIn("stories", archive)
        self.assertNotIn("reviews", archive)
        self.assertEqual(archive["entries"][0]["source_run_id"], "12345")

    def test_repeat_archive_deduplicates_by_exact_source_digest(self):
        p, audit = batch([candidate(1)],
                         [["review_deferred:provider_unavailable"]])
        old, _ = build_archive(p, audit)
        new, added = build_archive(p, audit, old)
        self.assertEqual(added, 0)
        self.assertEqual(old, new)
        different = candidate(1)
        different["title"] = "Rewritten draft"
        another, added = build_archive(*batch(
            [different], [["review_deferred:timeout"]]), new)
        self.assertEqual(added, 1)
        self.assertEqual(len(another["entries"]), 2)

    def test_mismatched_audit_identity_fails_closed(self):
        p, audit = batch([candidate(1)],
                         [["review_deferred:provider_unavailable"]])
        audit["reviews"][0]["content_id"] = "different"
        with self.assertRaisesRegex(ValueError, "identity_mismatch"):
            build_archive(p, audit)

    def test_invalid_previous_archive_cannot_promote_drafts(self):
        p, audit = batch([candidate(1)],
                         [["review_deferred:provider_unavailable"]])
        for modified in (
            {"version": 1, "status": "approved", "entries": []},
            {"version": 1, "status": ARCHIVE_STATUS, "publication_approval": True,
             "eligible_for_automatic_publishing": False, "entries": []},
            {"version": 1, "status": ARCHIVE_STATUS, "publication_approval": False,
             "eligible_for_automatic_publishing": False,
             "entries": [{"review_status": "approved"}]},
        ):
            with self.subTest(modified=modified), self.assertRaises(ValueError):
                build_archive(p, audit, modified)

    def test_archive_is_bounded_and_never_treats_review_deferred_as_approval(self):
        current = None
        for offset in range(0, 120, 40):
            stories = [candidate(i) for i in range(offset, offset + 40)]
            p, audit = batch(stories, [
                ["review_deferred:provider_unavailable"]] * 40)
            current, added = build_archive(p, audit, current)
            self.assertEqual(added, 40)
        self.assertEqual(len(current["entries"]), MAX_ENTRIES)
        self.assertEqual(current["entries"][0]["content_id"], "story-20")
        self.assertEqual(current["entries"][-1]["content_id"], "story-119")
        self.assertFalse(current["publication_approval"])
        self.assertFalse(current["eligible_for_automatic_publishing"])

    def test_rejects_oversized_proposals_and_unknown_reasons(self):
        huge = candidate(1)
        huge["visual_bible"] = "x" * 130_000
        with self.assertRaisesRegex(ValueError, "too_large"):
            build_archive(*batch([huge], [["review_deferred:timeout"]]))
        p, audit = batch([candidate(1)], [["review_deferred:unknown"]])
        archive, added = build_archive(p, audit)
        self.assertEqual((added, archive["entries"]), (0, []))

    def test_workflow_archives_only_after_review_without_publisher_intake(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        flow = (root / ".github/workflows/astra-gemini-proposal-batch.yml").read_text()
        review = flow.index("      - name: Independently review generated proposals")
        archive = flow.index("      - name: Archive deferred Gemini proposals")
        report = flow.index("      - name: Persist Gemini batch diagnostic")
        self.assertLess(review, archive)
        self.assertLess(archive, report)
        block = flow[archive:report]
        self.assertIn("if: success()", block)
        self.assertIn("python -m astra_v2.gemini_deferred_archive", block)
        self.assertIn("gemini-deferred-review-archive.json", block)
        self.assertNotIn("gemini_inventory_merge", block)
        # Reading --publisher-state for offline history checks is permitted.
        # Actual publishing/approval intake must remain absent.
        for prohibited in ("youtube_upload", "ASTRA_PUBLISH",
                           "python -m astra_v2.publisher",
                           "ai-reviewed-stories.json",
                           "ai-reviewed-decisions.json"):
            self.assertNotIn(prohibited, block)


if __name__ == "__main__":
    unittest.main()
