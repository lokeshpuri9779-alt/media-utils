"""Regression tests for ASTRA's structural scene-diversity quality gate."""
import unittest

from quality_lab import structural_quality_penalties


def scene(visual, treatment="illustration"):
    return {"visual": visual, "media_fit": "contain", "treatment": treatment,
            "headline": "A short scene", "duration": 2.0}


class StructuralVisualDiversityTests(unittest.TestCase):
    def test_repetitive_scenes_fail_even_when_numeric_score_is_high(self):
        report = {"genre": "fiction", "scenes": [scene("forest")] * 4}
        result = structural_quality_penalties(report)
        self.assertEqual(result["score"], 88.0)
        self.assertFalse(result["pass"])
        self.assertIn("visual-diversity", [p["type"] for p in result["penalties"]])

    def test_distinct_scene_treatments_pass(self):
        report = {"genre": "fiction", "scenes": [
            scene("forest"), scene("river"), scene("mountain"), scene("village")]}
        result = structural_quality_penalties(report)
        self.assertTrue(result["pass"])
        self.assertEqual(result["score"], 100.0)

    def test_other_existing_penalties_still_apply(self):
        report = {"genre": "fiction", "scenes": [
            scene("forest"), scene("river"), scene("mountain"), scene("village")],
            "layout_qa": {"safe_area_pass": False}}
        result = structural_quality_penalties(report)
        self.assertEqual(result["score"], 80.0)
        self.assertTrue(result["pass"])
        self.assertIn("safe-area", [p["type"] for p in result["penalties"]])


if __name__ == "__main__":
    unittest.main()
