import unittest
from astra_v2.story_factory_rewrite_queue import rewrite_packet, select_premises


def packet():
    return {"approved_count": 0, "publication_triggered": False,
            "candidates": [{"candidate_id": "c1", "source_sha256": "a" * 64,
                            "review_status": "awaiting_editorial_review",
                            "decision": "not_approved", "production_ready": False,
                            "eligible_for_automatic_publishing": False,
                            "story_beats": ["a", "b", "c", "d"]}]}


class RewriteQueueTests(unittest.TestCase):
    def test_rewrite_is_not_approved_or_production_ready(self):
        result = rewrite_packet(packet(), generator=lambda *a, **k: {"title": "New story", "production_ready": True})
        self.assertEqual(result["approved_count"], 0)
        self.assertFalse(result["rewrites"][0]["story"]["production_ready"])
        self.assertFalse(result["rewrites"][0]["approved"])

    def test_rejected_packet_fails_closed(self):
        p = packet()
        p["approved_count"] = 1
        with self.assertRaises(ValueError):
            select_premises(p)

    def test_failed_generation_stays_review_only(self):
        def fail(*args, **kwargs):
            raise ValueError("invalid")
        result = rewrite_packet(packet(), generator=fail)
        self.assertEqual(result["rewrites"][0]["status"], "rewrite_failed")
        self.assertEqual(result["approved_count"], 0)


if __name__ == "__main__":
    unittest.main()
