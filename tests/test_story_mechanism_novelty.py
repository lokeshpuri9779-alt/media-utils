"""Regression tests for the editorial-only mechanism novelty queue."""
import unittest
from astra_v2.story_mechanism_novelty import mechanism_novelty_queue


class MechanismNoveltyQueueTests(unittest.TestCase):
    def test_zero_limit(self):
        self.assertEqual(mechanism_novelty_queue(limit=0)["review_queue"], [])

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_novelty_queue(limit=-1)

    def test_unique_mechanisms(self):
        result = mechanism_novelty_queue()
        keys = [item["mechanism"] for item in result["review_queue"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(keys), 30)
        self.assertFalse(result["publication_enabled"])
        self.assertTrue(all(not x["production_ready"] for x in result["review_queue"]))

    def test_exclusion(self):
        result = mechanism_novelty_queue(history_mechanisms={"lantern-rain"})
        self.assertNotIn("lantern-rain", [x["mechanism"] for x in result["review_queue"]])


if __name__ == "__main__":
    unittest.main()
