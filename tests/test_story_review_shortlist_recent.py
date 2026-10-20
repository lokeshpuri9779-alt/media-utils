import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.story_review_shortlist import shortlist


class RecentShortlistTests(unittest.TestCase):
    def test_recent_candidates_take_priority_without_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ledger = {"proposals": [
                {"content_id": f"id-{i}", "title": f"Story {i}", "genre": "mystery",
                 "production_ready": False, "story_beats": []} for i in range(40)
            ]}
            review = {"proposals": [
                {"content_id": f"id-{i}",
                 "editorial_issues": ["human_or_model_editorial_review_required"],
                 "publication_rejection": "unreviewed_causal_draft"} for i in range(40)
            ]}
            (root / "ledger.json").write_text(json.dumps(ledger))
            (root / "review.json").write_text(json.dumps(review))
            result = shortlist(root / "ledger.json", root / "review.json", root / "out.json", limit=3)
            self.assertEqual([x["content_id"] for x in result["review_candidates"]],
                             ["id-39", "id-38", "id-37"])
            self.assertEqual(result["approved_for_production"], 0)
            self.assertFalse(result["publication_enabled"])
            self.assertTrue(all(not x["eligible_for_automatic_publishing"]
                                for x in result["review_candidates"]))

    def test_mismatched_audit_still_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "ledger.json").write_text(json.dumps({"proposals": [
                {"content_id": "a", "production_ready": False}]}))
            (root / "review.json").write_text(json.dumps({"proposals": [
                {"content_id": "b", "editorial_issues": ["human_or_model_editorial_review_required"]}]}))
            with self.assertRaises(ValueError):
                shortlist(root / "ledger.json", root / "review.json", root / "out.json")
