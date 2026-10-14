import unittest
from astra_v2.pillow_release_gate import evaluate

class ReleaseGateTests(unittest.TestCase):
    def test_rejects_missing(self):
        result=evaluate({})
        self.assertFalse(result["production_enable"])
        self.assertFalse(result["ready_for_full_story_qa"])

    def test_rejects_measured_slow_motion(self):
        result=evaluate({"width":1080,"height":1920,"frames":30,
                         "incremental_mean_ms":13.509,"motion_p95_ms":15.613})
        self.assertFalse(result["ready_for_full_story_qa"])
        self.assertIn("motion_overhead_too_high",result["reasons"])

    def test_fast_benchmark_still_requires_creative_qa(self):
        result=evaluate({"width":1080,"height":1920,"frames":30,
                         "incremental_mean_ms":5,"motion_p95_ms":7})
        self.assertTrue(result["ready_for_full_story_qa"])
        self.assertFalse(result["production_enable"])

if __name__=="__main__":
    unittest.main()
