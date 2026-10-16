"""Validate new authored ASTRA original story inventory before rendering."""
import unittest

from astra_v2.original_stories import catalog
from astra_v2.publication_quality import publication_rejection


class OriginalStorySupplyTests(unittest.TestCase):
    def test_original_catalog_has_unique_publishable_storyboards(self):
        stories = catalog()
        ids = [story["content_id"] for story in stories]
        titles = [story["title"].casefold().strip() for story in stories]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(titles), len(set(titles)))
        for story in stories:
            with self.subTest(story=story["content_id"]):
                self.assertTrue(story["production_ready"])
                self.assertIsNone(publication_rejection(story))
                beats = story["story_beats"]
                self.assertGreaterEqual(len(beats), 4)
                self.assertEqual(len({beat["speech"] for beat in beats}), len(beats))
                self.assertTrue(all(beat["speech"] and beat["visual"] for beat in beats))
                self.assertTrue(all(beat["visual_intent"] == beat["speech"] for beat in beats))

    def test_replenishment_has_four_distinct_story_ids(self):
        ids = {story["content_id"] for story in catalog()}
        self.assertTrue({
            "rayvan-original-moonpost-v1",
            "rayvan-original-rainmuseum-v1",
            "rayvan-original-clockworkbridge-v1",
            "rayvan-original-starseed-v1",
        }.issubset(ids))


if __name__ == "__main__":
    unittest.main()
