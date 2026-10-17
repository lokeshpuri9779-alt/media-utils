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
        report = audit_samples(frames([70] * 9))
        self.assertIn("near_frozen_frames", [x["type"] for x in report["warnings"]])

    def test_flash(self):
        report = audit_samples(frames([80, 83, 250, 84, 88]))
        self.assertIn("single_sample_luminance_flash", [x["type"] for x in report["warnings"]])

    def test_sustained_scene_change(self):
        report = audit_samples(frames([60, 65, 175, 180, 185]))
        self.assertNotIn("single_sample_luminance_flash", [x["type"] for x in report["warnings"]])

if __name__ == "__main__":
    unittest.main()
