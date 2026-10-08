import unittest
from creative_director import evaluate

class TechnicalFailClosedTests(unittest.TestCase):
    def test_explicit_technical_failure_blocks_perfect_scores(self):
        report = {
            "genre": "suspense",
            "creative": {k + "_score": 100 for k in ("hook", "retention", "visual", "novelty", "coherence")},
            "scene_analysis": {"pacing_score": 100},
            "audio": {"score": 100},
            "captions": {"score": 100},
            "technical": {"score": 100, "pass": False},
        }
        result = evaluate(report)
        self.assertFalse(result["publish_allowed"])
        self.assertIn("technical_validation_missing_or_failed", result["hard_failures"])

    def test_missing_technical_evidence_blocks(self):
        report = {"genre": "fiction", "creative": {k + "_score": 100 for k in ("hook", "retention", "visual", "novelty", "coherence")}, "scene_analysis": {"pacing_score": 100}, "audio": {"score": 100}, "captions": {"score": 100}}
        self.assertFalse(evaluate(report)["publish_allowed"])

if __name__ == "__main__":
    unittest.main()
