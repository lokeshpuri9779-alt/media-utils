import unittest
from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_forge import catalog
from astra_v2.editorial_review_packet import build_packet


class ReviewPacketTests(unittest.TestCase):
    def test_unreviewed_draft_not_reviewable(self):
        packet = build_packet([proposal(0)])
        self.assertEqual(packet["reviewable_count"], 0)
        self.assertEqual(packet["items"][0]["review_template"]["decision"], "pending")
        self.assertFalse(packet["items"][0]["reviewable"])
        self.assertEqual(packet["approved_count"], 0)

    def test_authored_story_packet_is_content_bound(self):
        story = catalog(limit=1)[0]
        item = build_packet([story])["items"][0]
        self.assertEqual(item["review_template"]["story_sha256"], item["story_sha256"])
        self.assertEqual(item["review_template"]["content_id"], story["content_id"])
        self.assertEqual(item["review_template"]["decision"], "pending")

    def test_duplicate_story_ids_fail(self):
        story = catalog(limit=1)[0]
        with self.assertRaises(ValueError):
            build_packet([story, story])


if __name__ == "__main__":
    unittest.main()
