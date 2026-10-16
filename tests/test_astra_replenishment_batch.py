"""Validate the replenishment batch without bypassing publication safeguards."""
import unittest

from astra_v2.original_replenishment import catalog as replenishment_catalog
from astra_v2.original_stories import catalog as original_catalog, story
from astra_v2.publication_quality import publication_rejection
from astra_v2.shorts_novelty import is_near_duplicate


NEW_KEYS = (
    "rainclock", "lighthousefox", "librarycloud", "rivercompass",
    "midnightmuseum", "moonbridge", "pocketvolcano", "paperboatrescue",
    "snowglobeweather", "lastfirework", "desertwell", "starcartographer",
)


class ReplenishmentBatchTests(unittest.TestCase):
    def test_twelve_new_arcs_are_complete_and_have_unique_ids(self):
        batch = replenishment_catalog(story)
        new = [item for item in batch if any(
            item.get("content_id") == "rayvan-original-" + key + "-v1"
            for key in NEW_KEYS
        )]
        self.assertEqual(len(new), 12)
        self.assertEqual(len({item["content_id"] for item in new}), 12)
        self.assertEqual(len({item["plot_fingerprint"] for item in new}), 12)
        for item in new:
            self.assertEqual(len(item["story_beats"]), 4)
            self.assertTrue(item["production_ready"])
            self.assertIsNone(publication_rejection(item))

    def test_new_arcs_are_not_near_duplicates_of_existing_catalog(self):
        existing = original_catalog() + replenishment_catalog(story)
        new_ids = {"rayvan-original-" + key + "-v1" for key in NEW_KEYS}
        new = [item for item in existing if item.get("content_id") in new_ids]
        for item in new:
            others = [candidate for candidate in existing
                      if candidate.get("content_id") != item.get("content_id")]
            with self.subTest(content_id=item["content_id"]):
                self.assertFalse(is_near_duplicate(item, others))


if __name__ == "__main__":
    unittest.main()
