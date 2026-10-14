import unittest
from experimental.engine_comparison import evaluate,compare,REQUIRED

class EngineComparisonTests(unittest.TestCase):
    def test_missing_evidence_rejects_candidate(self):
        self.assertFalse(evaluate({"render_success":True})["eligible"])
    def test_animatic_fails_motion_gate(self):
        report={key:True for key in REQUIRED}
        report.update(motion_gate_passed=False,render_seconds=22)
        self.assertEqual(evaluate(report)["reason"],"failed_quality_gates")
    def test_passing_candidate_never_switches_automatically(self):
        report={key:True for key in REQUIRED}
        report["render_seconds"]=22
        result=compare({},report)
        self.assertEqual(result["recommendation"],"review_candidate")
        self.assertFalse(result["switch_main"])
        self.assertFalse(result["publish"])
if __name__=="__main__":unittest.main()
