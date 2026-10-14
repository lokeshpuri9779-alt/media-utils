import unittest
from astra_v2.motion_quality_diagnostics import assess_motion


class MotionQualityDiagnosticsTests(unittest.TestCase):
    def test_flags_scenes_with_insufficient_sustained_motion(self):
        report = {"scenes": [
            {"scene": 1, "action": "walk", "adjacent_frame_differences": [
                {"changed_pixel_fraction_proxy": 0.002},
                {"changed_pixel_fraction_proxy": 0.003},
                {"changed_pixel_fraction_proxy": 0.006},
                {"changed_pixel_fraction_proxy": 0.002}]},
            {"scene": 2, "action": "dance", "adjacent_frame_differences": [
                {"changed_pixel_fraction_proxy": 0.02}] * 4},
        ]}
        result = assess_motion(report)
        self.assertTrue(result["review_required"])
        self.assertTrue(result["scenes"][0]["needs_visual_review"])
        self.assertFalse(result["scenes"][1]["needs_visual_review"])
        self.assertFalse(result["publication_allowed"])
        self.assertFalse(result["quality_approved"])

    def test_rejects_missing_samples(self):
        with self.assertRaises(ValueError):
            assess_motion({"scenes": [{"scene": 1, "adjacent_frame_differences": []}]})


if __name__ == "__main__":
    unittest.main()
