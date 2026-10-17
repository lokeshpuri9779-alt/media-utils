"""Regression tests for ASTRA frame diagnostics."""
import unittest
import numpy as np
from tools.astra_visual_artifact_audit import audit_samples

def frames(values):
    return np.stack([np.full((12, 16), value, dtype=np.uint8) for value in values])

class AuditTests(unittest.TestCase):
    def test_gradual_motion(self):
        self.assertEqual(audit_samples(frames([55, 60, 65, 70, 75, 80]))["warnings"], [])

    def test_empty_frames(self):
        report = audit_samples(frames([70, 0, 0, 0, 70]))
        self.assertIn("nearly_black_frames", [x["type"] for x in report["warnings"]])

    def test_frozen_sequence(self):
        report = audit_samples(frames([70] * 9), fps=2)
        self.assertIn("near_frozen_frames", [x["type"] for x in report["warnings"]])

    def test_flash(self):
        report = audit_samples(frames([80, 83, 250, 84, 88]))
        self.assertIn("single_sample_luminance_flash", [x["type"] for x in report["warnings"]])

    def test_sustained_scene_change(self):
        report = audit_samples(frames([60, 65, 175, 180, 185]))
        self.assertNotIn("single_sample_luminance_flash", [x["type"] for x in report["warnings"]])

    def test_horizontal_letterboxing(self):
        arr = frames([90] * 15)
        arr[:, 0, :] = 0
        arr[:, -1, :] = 0
        report = audit_samples(arr, fps=6)
        self.assertIn("horizontal_black_bars", [x["type"] for x in report["warnings"]])

    def test_letterboxing_does_not_flag_dark_scenes(self):
        arr = frames([5] * 15)
        self.assertNotIn("horizontal_black_bars",
                         [x["type"] for x in audit_samples(arr, fps=6)["warnings"]])

    def test_repeating_luminance_flicker(self):
        report = audit_samples(frames([55, 150] * 8), fps=6)
        self.assertIn("alternating_luminance_flicker",
                      [x["type"] for x in report["warnings"]])

    def test_sustained_brightness_change_is_not_flicker(self):
        report = audit_samples(frames([55] * 5 + [150] * 5), fps=6)
        self.assertNotIn("alternating_luminance_flicker",
                         [x["type"] for x in report["warnings"]])

    def test_invalid_sample_rate(self):
        with self.assertRaises(ValueError):
            audit_samples(frames([55, 60]), fps=0)

    def test_input_is_not_modified(self):
        arr = frames([55, 65, 75])
        original = arr.copy()
        audit_samples(arr)
        np.testing.assert_array_equal(arr, original)

if __name__ == "__main__":
    unittest.main()
