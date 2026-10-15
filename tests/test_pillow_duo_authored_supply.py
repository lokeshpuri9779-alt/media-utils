"""Authored Pillow Duo story supply must retain cast and causal beats."""
import unittest
from astra_v2.pillow_duo_stories import PLOTS
from astra_v2.pillow_duo_scene import duo_compatibility
from astra_v2.story_forge import catalog

NEW_KEYS = {
    "fox-owl-midnight-bell", "rabbit-mouse-wandering-book",
    "cat-otter-floating-key", "dog-squirrel-festival-clock",
    "owl-otter-storm-lantern", "fox-cat-rocket-parcel",
    "mouse-squirrel-missing-flower", "rabbit-dog-lost-compass",
}

class AuthoredDuoSupplyTests(unittest.TestCase):
    def test_eight_distinct_four_beat_plots(self):
        records = [p for p in PLOTS if p[0] in NEW_KEYS]
        self.assertEqual(len(records), len(NEW_KEYS))
        self.assertEqual({p[0] for p in records}, NEW_KEYS)
        self.assertEqual(len({p[1] for p in records}), len(NEW_KEYS))
        for key, title, genre, beats in records:
            with self.subTest(key=key):
                self.assertEqual(len(beats), 4)
                self.assertEqual(len({b[1] for b in beats}), 4)
                for headline, speech, visual, label in beats:
                    self.assertEqual(visual, "story")
                    self.assertGreaterEqual(len(speech.split()), 9)
                    self.assertTrue(duo_compatibility({"speech": speech})["supported"])

    def test_stories_enter_existing_quality_gated_catalog(self):
        stories = catalog()
        ids = {s["content_id"] for s in stories}
        import hashlib
        for key in NEW_KEYS:
            expected = "rayvan-forge-" + hashlib.sha256(key.encode()).hexdigest()[:16]
            self.assertIn(expected, ids)

if __name__ == "__main__":
    unittest.main()
