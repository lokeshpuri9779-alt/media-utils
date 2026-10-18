import unittest
from tools.astra_reviewed_story_promotion import promote
from astra_v2.story_expansion_2000 import candidate_records
from astra_v2.story_forge import plot_fingerprint

class PromotionTests(unittest.TestCase):
    def setUp(self):
        key, title, genre, beats = candidate_records()[0]
        self.approval = {"key": key, "reviewer": "editor", "editorial_reason": "Reviewed causal structure visual feasibility and distinctive story outcome manually",
                         "plot_fingerprint": plot_fingerprint(beats)}
    def test_requires_review_evidence(self):
        with self.assertRaises(ValueError):
            promote([{"key": self.approval["key"]}])
    def test_rejects_tampered_fingerprint(self):
        bad = dict(self.approval, plot_fingerprint="tampered")
        with self.assertRaises(ValueError):
            promote([bad])
    def test_rejects_duplicates(self):
        with self.assertRaises(ValueError):
            promote([self.approval, self.approval])
    def test_prepares_only_explicit_approval(self):
        result = promote([self.approval])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], self.approval["key"])

if __name__ == "__main__":
    unittest.main()
