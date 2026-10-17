import unittest
from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_forge import catalog
from astra_v2.editorial_approval_manifest import (
    story_digest, review_decision, validate_manifest,
)


class EditorialManifestTests(unittest.TestCase):
    def test_draft_cannot_be_promoted_by_record(self):
        draft = proposal(0)
        record = {"content_id": draft["content_id"], "story_sha256": story_digest(draft),
                  "decision": "approve", "reviewer": "editor", "review_notes": "Reviewed"}
        self.assertIn("not_reviewed_authored_story", review_decision(draft, record))
        self.assertEqual(validate_manifest([draft], [record])["approved_count"], 0)

    def test_missing_and_rejected_reviews_fail_closed(self):
        story = catalog(limit=1)[0]
        self.assertIn("missing_editorial_record", review_decision(story, None))
        record = {"content_id": story["content_id"], "story_sha256": story_digest(story),
                  "decision": "reject", "reviewer": "editor", "review_notes": "Needs work"}
        self.assertIn("editorial_approval_missing", review_decision(story, record))

    def test_payload_change_invalidates_review(self):
        story = catalog(limit=1)[0]
        record = {"content_id": story["content_id"], "story_sha256": story_digest(story),
                  "decision": "approve", "reviewer": "editor", "review_notes": "Reviewed"}
        altered = dict(story, title=story["title"] + " changed")
        self.assertIn("review_story_digest_mismatch", review_decision(altered, record))

    def test_duplicate_records_rejected(self):
        story = catalog(limit=1)[0]
        record = {"content_id": story["content_id"]}
        with self.assertRaises(ValueError):
            validate_manifest([story], [record, record])


if __name__ == "__main__":
    unittest.main()
