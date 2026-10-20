"""Tests for explicit editorial promotion; no automatic publishing."""
import unittest
from astra_v2.editorial_promotion_bridge import promote_reviewed_batch
from astra_v2.editorial_approval_manifest import story_digest


class EditorialPromotionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.story = {
            "content_id": "test-bridge-001",
            "title": "The Lantern at the Crossing",
            "kind": "authored_causal_story",
            "production_ready": True,
            "genre": "fiction",
            "plot_fingerprint": "bridge_test_unique_lantern_001",
            "story_beats": [
                {"story_beat": "reveal", "speech": "The storm swept across the village and the old bridge lost its warning lamp.", "visual": "bridge"},
                {"story_beat": "build", "speech": "A traveler spotted a boat approaching the hidden barrier while the current kept rising.", "visual": "river"},
                {"story_beat": "twist", "speech": "She found a working lantern inside the shelter and climbed to the signal platform.", "visual": "lantern"},
                {"story_beat": "payoff", "speech": "Her signal stopped the boat before the barrier, and the village repaired the warning light.", "visual": "bridge_lamp"},
            ],
        }
        self.decision = {"content_id": self.story["content_id"], "story_sha256": story_digest(self.story),
                         "decision": "approve", "reviewer": "External editor",
                         "review_notes": "Reviewed all four scenes for continuity, visual coherence, distinct plot and safe resolution."}

    def test_no_approval_is_rejected(self):
        with self.assertRaises(ValueError):
            promote_reviewed_batch([self.story], [dict(self.decision, decision="pending")])

    def test_unreviewed_draft_is_rejected(self):
        draft = dict(self.story, kind="unreviewed_causal_draft", production_ready=False)
        with self.assertRaises(ValueError):
            promote_reviewed_batch([draft], [dict(self.decision, story_sha256=story_digest(draft))])

    def test_modified_story_digest_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "review_digest_mismatch"):
            promote_reviewed_batch([dict(self.story, title="Changed")], [self.decision])

    def test_duplicate_decisions_are_rejected(self):
        with self.assertRaises(ValueError):
            promote_reviewed_batch([self.story], [self.decision, self.decision])

    def test_history_blocks_reuse(self):
        with self.assertRaises(ValueError):
            promote_reviewed_batch([self.story], [self.decision], [self.story])


if __name__ == "__main__":
    unittest.main()
