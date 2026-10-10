"""Offline tests for ASTRA's bounded procedural fiction inventory."""
import unittest
from astra_v2.procedural_stories import catalog


class ProceduralStoriesTest(unittest.TestCase):
    def test_unique_ids_and_core_plots(self):
        stories = catalog(limit=128)
        self.assertGreater(len(stories), 8)
        self.assertEqual(len(stories), len({s["content_id"] for s in stories}))
        # Replacing the cast/location must not count as a different core plot.
        fingerprints = []
        for story in stories:
            self.assertEqual(len(story["story_beats"]), 4)
            self.assertTrue(all(beat["speech"].strip() for beat in story["story_beats"]))
            fingerprints.append((story["question"],
                                 story["story_beats"][2]["speech"],
                                 story["story_beats"][3]["speech"]))
        self.assertEqual(len(fingerprints), len(set(fingerprints)))

    def test_excluded_ids_and_stability(self):
        first = catalog(limit=16)
        self.assertEqual(first, catalog(limit=16))
        skipped = {s["content_id"] for s in first}
        later = catalog(excluded_ids=skipped, limit=16)
        self.assertEqual(len(later), 16)
        self.assertTrue(all(s["content_id"] not in skipped for s in later))

    def test_publication_history_changes_character_priority(self):
        from unittest.mock import patch
        with patch("astra_v2.control.read_json", return_value={"published": {}}):
            baseline = catalog(limit=16)
        history = {"published": {str(i): {"title": "Mara and the Lantern at the Floating Market"} for i in range(20)}}
        with patch("astra_v2.control.read_json", return_value=history):
            adapted = catalog(limit=16)
        self.assertEqual(len(adapted), 16)
        self.assertNotEqual([x["content_id"] for x in baseline],
                            [x["content_id"] for x in adapted])
        self.assertLess(sum(x["title"].startswith("Mara ") for x in adapted), sum(x["title"].startswith("Mara ") for x in baseline))

    def test_zero_limit(self):
        self.assertEqual(catalog(limit=0), [])


if __name__ == "__main__":
    unittest.main()
