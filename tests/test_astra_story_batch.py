import unittest
from astra_v2.story_batch import STORY_ACTIONS, TEMPLATES, build_story_batch
from astra_v2.story_composition import action_for_beat
from astra_v2.coordinated_development import verify_story_cast


class StoryBatchTests(unittest.TestCase):
    def test_distinct_stories_casts_and_props(self):
        batch = build_story_batch()
        self.assertEqual(batch["story_count"], 4)
        stories = batch["stories"]
        self.assertEqual(len({s["title"] for s in stories}), 4)
        self.assertEqual(len({tuple(a["subject"] for a in s["scenes"][0]["actors"])
                              for s in stories}), 4)
        self.assertGreaterEqual(len({s["scenes"][0]["object"][0] for s in stories}), 3)
        self.assertEqual(len({s["genre"] for s in stories}), 4)
        self.assertGreaterEqual(len({s["location"] for s in stories}), 2)
        for story in stories:
            self.assertTrue(all(scene["location"] == story["location"] for scene in story["scenes"]))
            self.assertTrue(all(scene["caption"] == scene["narration"] for scene in story["scenes"]))
        for story in stories:
            self.assertTrue(verify_story_cast(story))
            self.assertEqual(tuple(s["action"] for s in story["scenes"]),
                             tuple(action_for_beat(i, s["narration"]) for i, s in enumerate(story["scenes"])))
        authored = build_story_batch(composed=False)["stories"]
        for story in authored:
            self.assertEqual(tuple(s["action"] for s in story["scenes"]), STORY_ACTIONS[story["title"]])
            self.assertFalse(story["publication_allowed"])
            self.assertFalse(story["quality_approved"])

    def test_reproducibility_and_seed_variation(self):
        self.assertEqual(build_story_batch("repeat"), build_story_batch("repeat"))
        self.assertEqual(build_story_batch("repeat", 2)["story_count"], 2)
        self.assertNotEqual(build_story_batch("repeat", episode=1),
                            build_story_batch("repeat", episode=2))
        self.assertEqual(build_story_batch("repeat", episode=2),
                         build_story_batch("repeat", episode=2))

    def test_adjacent_episode_batches_do_not_repeat_titles(self):
        first = build_story_batch("rotation", episode=1)["stories"]
        second = build_story_batch("rotation", episode=2)["stories"]
        self.assertTrue({story["title"] for story in first}.isdisjoint(
            {story["title"] for story in second}))

    def test_expanded_catalog(self):
        self.assertEqual(len(TEMPLATES), 8)
        self.assertEqual(build_story_batch("full", 8)["story_count"], 8)
        self.assertEqual(len({story["title"] for story in build_story_batch("full", 8)["stories"]}), 8)

    def test_invalid_inputs(self):
        for episode in (0, -1, 100001, "2"):
            with self.assertRaises(ValueError):
                build_story_batch(episode=episode)
        for seed, limit in (("", 1), ("valid", 0), ("valid", len(TEMPLATES)+1)):
            with self.assertRaises(ValueError):
                build_story_batch(seed, limit)


if __name__ == "__main__":
    unittest.main()
