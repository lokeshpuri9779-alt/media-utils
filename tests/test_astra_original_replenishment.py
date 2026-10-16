"""Guard fresh original Shorts inventory without bypassing quality policy."""
import unittest
from astra_v2.original_stories import catalog
from astra_v2.publication_quality import publication_rejection
from astra_v2.shorts_novelty import is_near_duplicate


class OriginalSupplyReplenishmentTests(unittest.TestCase):
    def test_eight_new_original_stories_are_ready_and_distinct(self):
        new = [s for s in catalog() if s["content_id"].startswith("rayvan-original-") and any(
            s["content_id"] == "rayvan-original-" + key + "-v1" for key in
            ("paperplanet", "lanterntrain", "cloudtailor", "clockseed", "submarinestar",
             "mirrorbird", "moonbakery", "glassforest"))]
        self.assertEqual(len(new), 8)
        self.assertEqual(len({s["plot_fingerprint"] for s in new}), 8)
        for item in new:
            self.assertTrue(item["production_ready"])
            self.assertIsNone(publication_rejection(item))
            self.assertEqual(len(item["story_beats"]), 4)

    def test_new_stories_not_near_duplicate_of_existing_catalog(self):
        stories = catalog()
        for i, story in enumerate(stories):
            with self.subTest(content_id=story["content_id"]):
                self.assertFalse(is_near_duplicate(story, stories[:i] + stories[i + 1:]))


if __name__ == "__main__":
    unittest.main()
