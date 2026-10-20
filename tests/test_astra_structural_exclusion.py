"""Structural exclusions must work without granting publication approval."""
import unittest
from astra_v2.plot_first_proposals import proposals, structural_key


class StructuralExclusionTests(unittest.TestCase):
    def test_excludes_existing_structure(self):
        baseline = proposals(limit=2)
        blocked = structural_key(baseline[0])
        candidates = proposals(limit=2, excluded_structural_keys=(blocked,))
        self.assertEqual(len(candidates), 2)
        self.assertNotIn(blocked, [structural_key(item) for item in candidates])
        self.assertFalse(any(item["production_ready"] for item in candidates))

    def test_no_repeated_structures(self):
        items = proposals(limit=100)
        keys = [structural_key(item) for item in items]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(keys))

    def test_missing_structure_not_treated_as_verified(self):
        self.assertIsNone(structural_key({"title": "Unknown"}))


if __name__ == "__main__":
    unittest.main()
