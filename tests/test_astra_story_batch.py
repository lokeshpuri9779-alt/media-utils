import unittest
from astra_v2.story_batch import ACTIONS, TEMPLATES, build_story_batch
from astra_v2.coordinated_development import verify_story_cast


class StoryBatchTests(unittest.TestCase):
    def test_distinct_stories_casts_and_props(self):
        batch = build_story_batch()
        self.assertEqual(batch["story_count"], 4)
        stories = batch["stories"]
        self.assertEqual(len({s["title"] for s in stories}), 4)
        self.assertEqual(len({tuple(a["subject"] for a in s["scenes"][0]["actors"])
                              for s in stories}), 4)
        self.assertEqual(len({s["scenes"][0]["object"][0] for s in stories}), 4)
        for story in stories:
            self.assertTrue(verify_story_cast(story))
            self.assertEqual(tuple(s["action"] for s in story["scenes"]), ACTIONS)
            self.assertFalse(story["publication_allowed"])
            self.assertFalse(story["quality_approved"])

    def test_reproducibility_and_seed_variation(self):
        self.assertEqual(build_story_batch("repeat"), build_story_batch("repeat"))
        self.assertEqual(build_story_batch("repeat", 2)["story_count"], 2)

    def test_invalid_inputs(self):
        for seed, limit in (("", 1), ("valid", 0), ("valid", len(TEMPLATES)+1)):
            with self.assertRaises(ValueError):
                build_story_batch(seed, limit)


if __name__ == "__main__":
    unittest.main()
