import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.editorial_review_journal import record_review


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.story = {"content_id": "story-1", "kind": "authored_causal_story",
                      "production_ready": True, "story_beats": []}

    def test_rejection_is_recorded_without_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reviews.json"
            result = record_review(self.story, {"approved": False, "issues": ["policy"]}, path)
            self.assertFalse(result["approved"])
            self.assertIsNone(result["record"])
            self.assertEqual(len(json.loads(path.read_text())["reviews"]), 1)

    def test_duplicate_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reviews.json"
            verdict = {"approved": False, "issues": ["not_ready"]}
            record_review(self.story, verdict, path)
            with self.assertRaises(ValueError):
                record_review(self.story, verdict, path)

    def test_approval_requires_manifest_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reviews.json"
            with patch("astra_v2.editorial_review_journal.review_decision", return_value=["blocked"]):
                with self.assertRaises(ValueError):
                    record_review(self.story, {"approved": True, "record": {
                        "content_id": "story-1", "decision": "approve"}}, path)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
