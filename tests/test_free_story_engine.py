import unittest
from astra_v2.free_story_engine import catalog


class FreeStoryTests(unittest.TestCase):
    def test_unique_complete_original_stories(self):
        stories = catalog()
        self.assertGreaterEqual(len(stories), 3)
        self.assertEqual(len({s["content_id"] for s in stories}), len(stories))
        self.assertEqual(len({s["title"].casefold() for s in stories}), len(stories))
        for story in stories:
            self.assertTrue(story["production_ready"])
            self.assertEqual(len(story["story_beats"]), 4)
            self.assertTrue(story["question"])
            self.assertTrue(story["answer"])
            for beat in story["story_beats"]:
                self.assertTrue(beat["speech"])
                self.assertTrue(beat["visual"])


if __name__ == "__main__":
    unittest.main()
