"""Text-only review queue guard never overwrites unreviewed drafts."""
import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.story_factory_text_review_guard import refresh_decision


def valid_queue():
    return {
        "schema_version": 1,
        "publication_triggered": False,
        "approved_count": 0,
        "rewrites": [{
            "candidate_id": "candidate-1",
            "source_sha256": "a" * 64,
            "status": "awaiting_independent_editorial_approval",
            "approved": False,
            "story": {
                "content_id": "story-1",
                "title": "A New Story",
                "production_ready": False,
            },
        }],
    }


class TextReviewGuardTests(unittest.TestCase):
    def test_missing_queue_allows_one_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                refresh_decision(Path(tmp) / "queue.json"),
                (True, "no_pending_text_review"),
            )

    def test_valid_pending_queue_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            original = json.dumps(valid_queue())
            path.write_text(original, encoding="utf-8")
            self.assertEqual(
                refresh_decision(path),
                (False, "existing_text_review_queue_preserved"),
            )
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_malformed_existing_queue_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unreadable"):
                refresh_decision(path)

    def test_invalid_existing_queue_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            path.write_text(json.dumps({"approved_count": 1}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manual_recovery"):
                refresh_decision(path)


if __name__ == "__main__":
    unittest.main()
