import unittest
from astra_v2.story_expansion_2000 import MECHANISMS, candidate_count, candidate_records

class ExpandedEditorialMechanismTests(unittest.TestCase):
    def test_six_new_causal_premises(self):
        keys = [row[0] for row in MECHANISMS]
        self.assertEqual(len(keys), 36)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(candidate_count(), 3600)
        self.assertEqual(len(candidate_records()), 3600)
        self.assertTrue({"silent-windmill", "painted-sign", "floating-seed", "mismatched-bells", "fading-mural", "night-bridge"} <= set(keys))

if __name__ == "__main__":
    unittest.main()
