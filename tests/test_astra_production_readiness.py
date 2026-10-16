import unittest
from astra_v2.production_readiness import assess, GATES
from astra_v2.autonomous_story_proposals import proposal


class ProductionReadinessTests(unittest.TestCase):
    def test_all_eight_gates_reported(self):
        result = assess()
        self.assertEqual(set(GATES), set(result) - {"end_to_end_verified"})
        self.assertFalse(result["end_to_end_verified"])
        self.assertFalse(result["youtube_publication"]["passed"])

    def test_unreviewed_proposals_cannot_be_approved(self):
        result = assess(proposal(0))
        self.assertFalse(result["editorial_approval"]["passed"])
        self.assertFalse(result["approved_story_supply"]["passed"])
        self.assertFalse(result["end_to_end_verified"])

    def test_unverified_metrics_do_not_imply_publication(self):
        result = assess(metrics={"video_id": "test", "measured_at": "2026-01-01"})
        self.assertFalse(result["youtube_publication"]["passed"])
        self.assertFalse(result["end_to_end_verified"])


if __name__ == "__main__":
    unittest.main()
