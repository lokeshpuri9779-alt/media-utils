import unittest
from PIL import ImageChops
from astra_v2.coordinated_development import build_ensemble_plan, frame, render


class LocomotionTests(unittest.TestCase):
    def test_new_motion_cues_produce_different_frames(self):
        for action in ("walk", "run", "jump", "dance"):
            with self.subTest(action=action):
                plan = build_ensemble_plan("locomotion-check", [["cat", "dog"]])
                scene = plan["scenes"][0]
                scene.update(action=action, visual_style="storybook")
                first = frame(scene, 0.15)
                later = frame(scene, 0.8)
                self.assertIsNotNone(ImageChops.difference(first, later).getbbox())

    def test_full_size_actor_jumps_vertically(self):
        """Regression: single-member ensemble previously lacked jump offset."""
        from PIL import ImageChops
        plan = build_ensemble_plan("solo-jump-check", [["cat"]])
        scene = plan["scenes"][0]
        scene.update(action="jump", visual_style="storybook")
        still = frame(scene, 0.0)
        airborne = frame(scene, 0.45)
        # Whole-frame difference includes backgrounds; this is a broad visual
        # regression check, not a physics or character tracking assertion.
        self.assertIsNotNone(ImageChops.difference(still, airborne).getbbox())

    def test_publishing_remains_disabled(self):
        plan = build_ensemble_plan("locomotion-check", [["cat", "dog"]])
        self.assertFalse(plan["publication_allowed"])
        self.assertFalse(plan["quality_approved"])


if __name__ == "__main__":
    unittest.main()
