"""Tests for independently bound editorial evidence."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.editorial_approval_manifest import story_digest
from astra_v2.warehouse_editorial_evidence import approval_evidence_digest, verify_editorial_claim


class EditorialEvidenceTests(unittest.TestCase):
    def test_exact_review_digest_and_tampering(self):
        story = {"content_id": "story-1", "title": "A Unique Story"}
        review = {"content_id": "story-1", "story_sha256": story_digest(story),
                  "decision": "approve", "reviewer": "editor",
                  "review_notes": "Reviewed scene by scene"}
        with tempfile.TemporaryDirectory() as folder:
            stories = Path(folder) / "stories.json"
            reviews = Path(folder) / "reviews.json"
            stories.write_text(json.dumps({"stories": [story]}))
            reviews.write_text(json.dumps({"reviews": [review]}))
            claim = {"content_id": "story-1",
                     "approval_digest": approval_evidence_digest(story, review)}
            with patch("astra_v2.warehouse_editorial_evidence.review_decision", return_value=[]):
                self.assertTrue(verify_editorial_claim(claim, stories, reviews, eligible_ids=["story-1"]))
                tampered = dict(claim, approval_digest="0" * 64)
                with self.assertRaisesRegex(ValueError, "warehouse_approval_digest_mismatch"):
                    verify_editorial_claim(tampered, stories, reviews, eligible_ids=["story-1"])
                with self.assertRaisesRegex(ValueError, "warehouse_story_not_editorially_approved"):
                    verify_editorial_claim(claim, stories, reviews, eligible_ids=[])
                review["review_notes"] = "Changed after approval"
                reviews.write_text(json.dumps({"reviews": [review]}))
                with self.assertRaisesRegex(ValueError, "warehouse_approval_digest_mismatch"):
                    verify_editorial_claim(claim, stories, reviews, eligible_ids=["story-1"])


if __name__ == "__main__":
    unittest.main()
