"""World library taxonomy and determinism regression tests."""
import unittest
from experimental.world_library import TAXONOMY, ANIMATION_TAGS, make_asset, counts

class WorldLibraryTests(unittest.TestCase):
    def test_all_categories_nonempty(self):
        self.assertEqual(set(TAXONOMY),set(ANIMATION_TAGS))
        self.assertTrue(all(TAXONOMY[k] and ANIMATION_TAGS[k] for k in TAXONOMY))
    def test_deterministic(self):
        for category in TAXONOMY:
            self.assertEqual(make_asset(category,"episode-7"),make_asset(category,"episode-7"))
    def test_valid_kinds(self):
        for category in TAXONOMY:
            for i in range(50):
                asset=make_asset(category,str(i))
                self.assertIn(asset.kind,TAXONOMY[category])
                self.assertEqual(asset.category,category)
    def test_coverage(self):
        summary=counts()
        self.assertGreaterEqual(summary["categories"],10)
        self.assertGreaterEqual(summary["base_kinds"],250)
        self.assertGreater(summary["descriptive_combinations"],100000)
    def test_unknown_category(self):
        with self.assertRaises(ValueError):
            make_asset("unknown","seed")

if __name__=="__main__":
    unittest.main()
