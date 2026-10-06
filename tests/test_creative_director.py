import unittest

from creative_director import evaluate, production_feedback


class CreativeDirectorTests(unittest.TestCase):
    def test_strong_video_publishes(self):
        report = {
            "creative": {
                "hook_score": 90, "retention_score": 86, "visual_score": 88,
                "novelty_score": 82, "coherence_score": 90,
            },
            "scene_analysis": {
                "scene_count": 8, "avg_scene_duration": 1.8, "max_scene_duration": 2.8,
            },
            "audio": {"score": 90},
            "captions": {"score": 91},
            "technical": {"pass": True, "score": 100},
        }
        result = evaluate(report)
        self.assertTrue(result["publish_allowed"])
        self.assertEqual(result["action"], "publish")

    def test_mid_video_gets_targeted_repairs(self):
        report = {
            "creative": {
                "hook_score": 92, "retention_score": 78, "visual_score": 48,
                "novelty_score": 76, "coherence_score": 88,
            },
            "scene_analysis": {
                "scene_count": 4, "avg_scene_duration": 3.1, "max_scene_duration": 5.2,
            },
            "audio": {"score": 88},
            "captions": {"score": 90},
            "technical": {"pass": True, "score": 100},
        }
        result = evaluate(report)
        feedback = production_feedback(result)
        self.assertFalse(result["publish_allowed"])
        self.assertIn(result["action"], {"targeted_regeneration", "regenerate_concept"})
        self.assertIn("replace_weak_visuals_and_broll", result["repair_plan"])
        self.assertFalse(feedback["keep"]["visuals"])
        self.assertTrue(feedback["keep"]["voice"])

    def test_hard_failure_blocks_publication(self):
        result = evaluate({
            "hard_failures": ["copyright provenance unresolved"],
            "creative": {"hook_score": 100, "retention_score": 100, "visual_score": 100,
                         "novelty_score": 100, "coherence_score": 100},
            "scene_analysis": {"scene_count": 10, "avg_scene_duration": 1.0, "max_scene_duration": 1.5},
            "audio": {"score": 100},
            "captions": {"score": 100},
            "technical": {"pass": True, "score": 100},
        })
        self.assertFalse(result["publish_allowed"])
        self.assertEqual(result["action"], "rebuild_or_block")


if __name__ == "__main__":
    unittest.main()
