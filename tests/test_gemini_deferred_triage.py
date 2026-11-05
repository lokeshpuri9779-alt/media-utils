"""No-network, non-publishing tests for archived Gemini local triage."""
import hashlib
import json
import unittest
from unittest.mock import patch

from astra_v2.gemini_deferred_archive import _encoded, ARCHIVE_STATUS
from astra_v2.gemini_deferred_triage import triage_archive


def entry(content_id="c1", *, title="Source story", reason="review_deferred:provider_unavailable"):
    story = {"kind": "microfiction", "content_id": content_id,
             "title": title, "production_ready": True}
    return {"source_sha256": hashlib.sha256(_encoded(story)).hexdigest(),
            "content_id": content_id, "review_status": "deferred_unreviewed",
            "deferred_reason": reason, "source_run_id": "123", "proposal": story}


def archive(items):
    return {"version": 1, "status": ARCHIVE_STATUS,
            "publication_approval": False,
            "eligible_for_automatic_publishing": False,
            "entries": items}


class GeminiDeferredTriageTests(unittest.TestCase):
    def test_aggregates_clear_and_blocked_but_never_approves(self):
        items = [entry("a"), entry("b")]
        snapshot = json.dumps(items, sort_keys=True)
        history = [{"content_id": "published"}]
        seen = []
        def local_gate(story, provided_history):
            seen.append((story["kind"], story["content_id"], provided_history))
            return [] if story["content_id"] == "a" else [
                "narrative_duplicate", "publication_renderer_incompatible: private detail"]
        report = triage_archive(archive(items), history, checker=local_gate)
        self.assertEqual(report["source_count"], 2)
        self.assertEqual(report["local_checks_clear"], 1)
        self.assertEqual(report["blocked"], 1)
        self.assertEqual(report["unavailable"], 0)
        self.assertEqual(report["issue_category_counts"], {
            "narrative_duplicate": 1, "renderer_incompatible": 1})
        self.assertTrue(all(x[0] == "authored_causal_story" for x in seen))
        self.assertEqual(seen[0][2], history)
        self.assertFalse(report["editorial_approval"])
        self.assertFalse(report["publication_triggered"])
        self.assertNotIn("private detail", str(report))
        self.assertNotIn("Source story", str(report))
        self.assertEqual(json.dumps(items, sort_keys=True), snapshot)

    def test_exception_does_not_turn_into_clear_pass_or_log_secret(self):
        def fail(*args):
            raise RuntimeError("API_KEY_PRIVATE")
        report = triage_archive(archive([entry()]), [], checker=fail)
        self.assertEqual(report["unavailable"], 1)
        self.assertEqual(report["local_checks_clear"], 0)
        self.assertNotIn("PRIVATE", str(report))

    def test_hash_mismatch_identity_mismatch_and_duplicates_fail_closed(self):
        original = entry()
        for invalid in (
            [{**original, "source_sha256": "0" * 64}],
            [{**original, "content_id": "different"}],
            [{**original, "review_status": "approved"}],
            [{**original, "deferred_reason": "review_deferred:unknown"}],
            [original, original],
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                triage_archive(archive(invalid), [], checker=lambda s, h: [])

    def test_invalid_or_missing_state_cannot_be_silent_empty_history(self):
        with self.assertRaises(ValueError):
            triage_archive({"status": "approved", "entries": []}, [],
                           checker=lambda s, h: [])
        with self.assertRaises(ValueError):
            triage_archive(archive([]), None, checker=lambda s, h: [])

    def test_only_sanitized_categories_leave_triage(self):
        report = triage_archive(archive([entry()]), [],
                               checker=lambda s, h: ["a_private_message",
                                   "publication_invalid_PRIVATE_DETAILS"])
        self.assertEqual(report["issue_category_counts"], {
            "other_local_issue": 1, "other_publication_blocker": 1})
        self.assertNotIn("PRIVATE", str(report))
        self.assertFalse(report["publication_triggered"])

    def test_workflow_uses_history_and_retains_separate_review_only_artifacts(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        flow = (root / ".github/workflows/astra-gemini-proposal-batch.yml").read_text()
        arch = flow.split("      - name: Archive deferred Gemini proposals", 1)[1].split(
            "      - name: Persist Gemini batch diagnostic", 1)[0]
        self.assertIn("ASTRA_UNIFIED_STORY_ENGINE=1 python -m astra_v2.gemini_deferred_triage", arch)
        self.assertIn("gemini-deferred-triage.json", arch)
        self.assertIn("--publisher-state astra_v2_state.json", arch)
        self.assertIn("--story-history astra_story_history.json", arch)
        self.assertIn("git add gemini-deferred-review-archive.json gemini-deferred-triage.json", arch)
        self.assertNotIn("ai-reviewed-stories.json", arch)
        self.assertNotIn("gemini_inventory_merge", arch)


if __name__ == "__main__":
    unittest.main()
