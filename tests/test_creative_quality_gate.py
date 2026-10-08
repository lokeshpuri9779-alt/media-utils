import unittest
from astra.creative_quality_gate import evaluate, WEIGHTS

class CreativeGateTests(unittest.TestCase):
    def setUp(self):
        self.metrics = {k: 90 for k in WEIGHTS["fiction"]}
        self.technical = {k: True for k in (
            "video_decodes", "audio_decodes", "duration_valid",
            "aspect_ratio_valid", "no_black_frames")}

    def test_pass(self):
        result = evaluate("fiction", self.metrics, self.technical)
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 90)

    def test_technical_failure_overrides_score(self):
        self.technical["video_decodes"] = False
        self.assertFalse(evaluate("suspense", self.metrics, self.technical).passed)

    def test_low_score_fails(self):
        self.assertFalse(evaluate("fiction", {k: 70 for k in self.metrics}, self.technical).passed)

    def test_missing_metric_rejected(self):
        with self.assertRaises(ValueError):
            evaluate("fiction", {}, self.technical)

    def test_missing_technical_check_fails_closed(self):
        self.assertFalse(evaluate("fiction", self.metrics, {}).passed)

    def test_weights_total_100(self):
        for weights in WEIGHTS.values():
            self.assertEqual(sum(weights.values()), 100)

if __name__ == "__main__":
    unittest.main()
