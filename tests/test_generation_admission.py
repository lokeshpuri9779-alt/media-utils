import unittest

from generation_admission import evaluate_generation_admission


class GenerationAdmissionTests(unittest.TestCase):
    def test_private_self_hosted_is_allowed(self):
        report=evaluate_generation_admission(
            {"ready":True,"selected":"ltx-local"},
            publish_mode="private",
            scene_count=5,
            requested_scene_seconds=[2,2,2,2,2],
        )
        self.assertTrue(report["allowed"])

    def test_public_character_render_is_blocked(self):
        report=evaluate_generation_admission(
            {"ready":True,"selected":"ltx-local"},
            publish_mode="public",
            scene_count=5,
            requested_scene_seconds=[2]*5,
        )
        self.assertFalse(report["allowed"])
        self.assertTrue(any("private-review" in x for x in report["failures"]))

    def test_paid_provider_is_blocked_autonomously(self):
        report=evaluate_generation_admission(
            {"ready":True,"selected":"replicate"},
            publish_mode="private",
            scene_count=5,
            requested_scene_seconds=[2]*5,
        )
        self.assertFalse(report["allowed"])

    def test_scene_budget_is_enforced(self):
        report=evaluate_generation_admission(
            {"ready":True,"selected":"wan2.2-local"},
            publish_mode="private",
            scene_count=9,
            requested_scene_seconds=[2]*9,
        )
        self.assertFalse(report["allowed"])


if __name__=="__main__":
    unittest.main()
