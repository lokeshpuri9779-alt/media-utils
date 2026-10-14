"""Catalog regression tests: stable selection, valid dimensions, and diversity."""
import unittest
from experimental.asset_library import (
    character, prop, scene, catalog_counts, SKIN_TONES, BODY_TYPES,
    HAIR_STYLES, OUTFITS, PALETTES, EXPRESSIONS, OBJECT_TYPES,
    OBJECT_STATES, ENVIRONMENTS, LIGHTING, WEATHER
)

class AssetLibraryTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(character("episode-1"),character("episode-1"))
        self.assertEqual(prop("episode-1"),prop("episode-1"))
        self.assertEqual(scene("episode-1"),scene("episode-1"))
    def test_valid_attributes(self):
        for i in range(200):
            key=f"episode-{i}"
            c=character(key); p=prop(key); s=scene(key)
            self.assertIn(c.skin,SKIN_TONES)
            self.assertIn(c.body,BODY_TYPES)
            self.assertIn(c.hair,HAIR_STYLES)
            self.assertIn(c.outfit,OUTFITS)
            self.assertIn(c.palette,PALETTES)
            self.assertIn(c.expression,EXPRESSIONS)
            self.assertIn(p.kind,OBJECT_TYPES)
            self.assertIn(p.state,OBJECT_STATES)
            self.assertIn(s.environment,ENVIRONMENTS)
            self.assertIn(s.lighting,LIGHTING)
            self.assertIn(s.weather,WEATHER)
    def test_diversity(self):
        self.assertGreater(len({character(str(i)) for i in range(200)}),180)
        self.assertGreater(len({prop(str(i)) for i in range(200)}),70)
        self.assertGreater(len({scene(str(i)) for i in range(200)}),70)
    def test_catalog_sizes(self):
        counts=catalog_counts()
        self.assertGreaterEqual(counts["character_combinations"],2000)
        self.assertGreaterEqual(counts["prop_combinations"],200)
        self.assertGreaterEqual(counts["scene_combinations"],500)
        self.assertGreaterEqual(counts["action_labels"],30)

if __name__=="__main__":
    unittest.main()
