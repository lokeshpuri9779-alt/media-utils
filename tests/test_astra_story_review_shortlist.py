import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.story_review_shortlist import shortlist


class EditorialShortlistTests(unittest.TestCase):
    def test_only_editorial_only_drafts_are_shortlisted(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            stories = [{"content_id": str(i), "title": "Story", "production_ready": False}
                       for i in range(3)]
            audits = [
                {"content_id": "0", "editorial_issues": ["human_or_model_editorial_review_required"],
                 "publication_rejection": "unreviewed_causal_draft"},
                {"content_id": "1", "editorial_issues": ["narrative_duplicate"],
                 "publication_rejection": "not_production_ready"},
                {"content_id": "2", "editorial_issues": ["human_or_model_editorial_review_required"],
                 "publication_rejection": "not_production_ready"},
            ]
            (root / "ledger.json").write_text(json.dumps({"proposals": stories}))
            (root / "audit.json").write_text(json.dumps({"proposals": audits}))
            result = shortlist(root / "ledger.json", root / "audit.json", root / "out.json")
            self.assertEqual([x["content_id"] for x in result["review_candidates"]], ["0", "2"])
            self.assertEqual(result["approved_for_production"], 0)
            self.assertFalse(result["publication_enabled"])
            self.assertTrue(all(not x["production_ready"] for x in result["review_candidates"]))

    def test_rejects_misaligned_audit(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "ledger.json").write_text(json.dumps({"proposals": [{"content_id": "one"}]}))
            (root / "audit.json").write_text(json.dumps({"proposals": [{"content_id": "other"}]}))
            with self.assertRaises(ValueError):
                shortlist(root / "ledger.json", root / "audit.json", root / "out.json")


if __name__ == "__main__":
    unittest.main()
