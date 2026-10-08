import unittest
from creative_director import evaluate, GENRE_WEIGHTS

def report(genre="fiction", **scores):
    values = dict(hook=90, retention=90, visual=90, pacing=90, audio=90,
                  captions=90, novelty=90, coherence=90, technical=100)
    values.update(scores)
    return {
        "genre": genre,
        "creative": {k + "_score": values[k] for k in ("hook", "retention", "visual", "novelty", "coherence")},
        "scene_analysis": {"pacing_score": values["pacing"], "max_scene_duration": 10, "avg_scene_duration": 5, "scene_count": 5},
        "audio": {"score": values["audio"]},
        "captions": {"score": values["captions"]},
        "technical": {"score": values["technical"], "pass": values["technical"] >= 85},
    }

class ProductionGenreGateTests(unittest.TestCase):
    def test_weights(self):
        for genre in ("fiction", "suspense"):
            self.assertAlmostEqual(sum(GENRE_WEIGHTS[genre].values()), 1.0)

    def test_high_quality_fiction_passes(self):
        self.assertTrue(evaluate(report())["publish_allowed"])

    def test_high_quality_suspense_passes(self):
        self.assertTrue(evaluate(report("suspense"))["publish_allowed"])

    def test_floor_blocks_even_if_total_below_publish_threshold(self):
        verdict = evaluate(report(hook=74, retention=75, visual=75, pacing=70,
                                  audio=75, captions=75, novelty=75, coherence=75))
        self.assertFalse(verdict["publish_allowed"])

    def test_technical_floor_blocks(self):
        self.assertFalse(evaluate(report(technical=80))["publish_allowed"])

    def test_long_scene_without_pacing_score_not_auto_penalized(self):
        r = report()
        del r["scene_analysis"]["pacing_score"]
        self.assertEqual(evaluate(r)["component_scores"]["pacing"], 100.0)

if __name__ == "__main__":
    unittest.main()
