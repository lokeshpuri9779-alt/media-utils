"""Story factory capacity, determinism, and publishing safety."""
import unittest
from astra_v2.story_factory import TARGET, CAPACITY, candidate_at

class StoryFactoryTests(unittest.TestCase):
    def test_capacity(self):
        self.assertGreaterEqual(CAPACITY, TARGET)
    def test_bounds(self):
        with self.assertRaises(IndexError): candidate_at(TARGET)
    def test_deterministic_and_unapproved(self):
        for i in (0,1,3000,195999):
            row=candidate_at(i)
            self.assertEqual(row,candidate_at(i))
            self.assertFalse(row["production_ready"])
            self.assertEqual(row["kind"],"unreviewed_causal_draft")
            self.assertEqual(len(row["story_beats"]),4)
    def test_sample_unique_ids(self):
        self.assertEqual(len({candidate_at(i)["candidate_id"] for i in range(1000)}),1000)
if __name__=="__main__": unittest.main()
