import unittest

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.global_story_novelty import filter_global_novelty


def batch(stories):
    return {"batch_id": "batch", "count": len(stories), "stories": stories,
            "approved_count": 0, "publication_triggered": False}


class GlobalStoryNoveltyTests(unittest.TestCase):
    def test_unique_candidates_remain_unreviewed(self):
        result = filter_global_novelty(batch([proposal(5), proposal(100)]))
        self.assertEqual(result["proposed"], 2)
        self.assertEqual(result["approved_count"], 0)
        self.assertFalse(result["publication_triggered"])
        self.assertTrue(all(not x["production_ready"] for x in result["stories"]))

    def test_existing_identity_rejected(self):
        original = proposal(5)
        result = filter_global_novelty(batch([original]), existing=[original])
        self.assertEqual(result["accepted"], 0)
        self.assertEqual(result["rejected"][0]["reason"], "existing_content_id")

    def test_duplicate_within_batch_rejected(self):
        first = proposal(5)
        second = dict(first, content_id="different-id")
        result = filter_global_novelty(batch([first, second]))
        self.assertEqual(result["accepted"], 1)
        self.assertEqual(len(result["rejected"]), 1)

    def test_approved_story_rejected(self):
        story = dict(proposal(1), production_ready=True)
        with self.assertRaises(ValueError):
            filter_global_novelty(batch([story]))

    def test_incorrect_count_rejected(self):
        invalid = batch([proposal(1)])
        invalid["count"] = 2
        with self.assertRaises(ValueError):
            filter_global_novelty(invalid)


if __name__ == "__main__":
    unittest.main()
