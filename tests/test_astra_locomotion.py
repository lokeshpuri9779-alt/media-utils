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
        plan = build_ensemble_plan("solo-jump-check", [["cat"]])
        scene = plan["scenes"][0]
        scene.update(action="jump", visual_style="storybook")
        # Hold background time fixed by comparing jump against an otherwise
        # identical grounded scene at the same instant. This isolates the authored
        # movement cue from animated environmental elements.
        t = 0.45
        airborne = frame(scene, t)
        idle_scene = dict(scene, action="walk")
        grounded = frame(idle_scene, t)
        self.assertIsNotNone(ImageChops.difference(grounded, airborne).getbbox())

    def test_jump_vs_walk_at_multiple_timestamps(self):
        plan = build_ensemble_plan("solo-jump-check", [["cat"]])
        base = plan["scenes"][0]
        for timestamp in (0.3, 0.6, 0.9):
            with self.subTest(timestamp=timestamp):
                jump = frame(dict(base, action="jump"), timestamp)
                walk = frame(dict(base, action="walk"), timestamp)
                self.assertIsNotNone(ImageChops.difference(jump, walk).getbbox())

    def test_production_silhouette_accepts_all_locomotion_cues(self):
        from PIL import Image
        from astra_v2.character_object_catalog import draw_character_silhouette
        for gesture in ("walk", "run", "jump", "dance"):
            with self.subTest(gesture=gesture):
                canvas = Image.new("RGBA", (1080, 1920))
                draw_character_silhouette(canvas, 0, 0.4, 540, 960,
                                          expression="neutral", gesture=gesture)
                self.assertIsNotNone(canvas.getbbox())

    def test_publishing_remains_disabled(self):
        plan = build_ensemble_plan("locomotion-check", [["cat", "dog"]])
        self.assertFalse(plan["publication_allowed"])
        self.assertFalse(plan["quality_approved"])


if __name__ == "__main__":
    unittest.main()
