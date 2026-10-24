import unittest
from unittest.mock import patch
from scripts.benchmark_story_assets import benchmark


class BenchmarkStoryAssetsTests(unittest.TestCase):
    @patch("scripts.benchmark_story_assets.inspect_story_assets")
    def test_coverage_math_and_no_render_claim(self, inspect):
        inspect.side_effect = [
            {"shot_count": 4, "matched_shots": 3, "all_shots_matched": False,
             "shots": [{"setting": "railway", "has_verified_match": False}]},
            {"shot_count": 4, "matched_shots": 4, "all_shots_matched": True,
             "shots": []},
        ]
        report = benchmark("/unused", count=2)
        self.assertEqual(report["shot_coverage_ratio"], 7 / 8)
        self.assertEqual(report["missing_scene_settings"], ["railway"])
        self.assertEqual(report["fully_matched_stories"], 1)
        self.assertFalse(report["video_rendered"])

    def test_rejects_zero_count(self):
        with self.assertRaises(ValueError):
            benchmark("/unused", count=0)


if __name__ == "__main__":
    unittest.main()
