import unittest
from astra_v2.editorial_review_worksheet import build_worksheet
from astra_v2.editorial_approval_manifest import story_digest


class WorksheetTests(unittest.TestCase):
    def setUp(self):
        self.story = {"content_id": "draft-001", "kind": "unreviewed_causal_draft",
                      "production_ready": False, "title": "Lantern",
                      "story_beats": [{"story_beat": "reveal", "speech": "A lantern failed", "visual": "river"}]}
        self.review = {"content_id": "draft-001", "story_sha256": story_digest(self.story),
                       "decision": "pending", "reviewer": "", "review_notes": ""}

    def test_read_only_packet(self):
        text = build_worksheet({"stories": [self.story]}, {"reviews": [self.review]})
        self.assertIn("Original narration", text)
        self.assertIn("approved", text.lower())
        self.assertIn("draft-001", text)

    def test_reject_stale_digest(self):
        with self.assertRaisesRegex(ValueError, "digest"):
            build_worksheet({"stories": [dict(self.story, title="changed")]},
                            {"reviews": [self.review]})

    def test_reject_approved_decision(self):
        with self.assertRaisesRegex(ValueError, "pending"):
            build_worksheet({"stories": [self.story]},
                            {"reviews": [dict(self.review, decision="approve")]})

    def test_reject_production_ready(self):
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            build_worksheet({"stories": [dict(self.story, production_ready=True)]},
                            {"reviews": [dict(self.review, story_sha256=story_digest(dict(self.story, production_ready=True)))]})


if __name__ == "__main__":
    unittest.main()
