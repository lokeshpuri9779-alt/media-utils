import unittest
from quality_lab import structural_quality_penalties

class NarrativePacingTests(unittest.TestCase):
    def test_fiction_long_shot_not_penalized(self):
        report = {"genre": "fiction", "scenes": [
            {"duration": 10, "visual": "a"},
            {"duration": 10, "visual": "b"},
            {"duration": 10, "visual": "c"},
            {"duration": 10, "visual": "d"}]}
        penalties = structural_quality_penalties(report)["penalties"]
        self.assertNotIn("static-shot", [p["type"] for p in penalties])
        self.assertNotIn("uniform-pacing", [p["type"] for p in penalties])

    def test_nonfiction_still_checks_long_shot(self):
        report = {"genre": "education", "scenes": [
            {"duration": 10, "visual": "a"},
            {"duration": 2, "visual": "b"},
            {"duration": 2, "visual": "c"}]}
        penalties = structural_quality_penalties(report)["penalties"]
        self.assertIn("static-shot", [p["type"] for p in penalties])

if __name__ == "__main__":
    unittest.main()
