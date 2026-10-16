"""Regression tests for deterministic Pillow character dance motion."""
import unittest
from PIL import Image, ImageDraw, ImageChops
from astra_v2.pillow_duo_scene import _actor


class DanceMotionTests(unittest.TestCase):
    def render(self, t, action="dance"):
        image = Image.new("RGB", (1080, 1920), (32, 36, 48))
        _actor(ImageDraw.Draw(image), "fox", 540, 800, t, action, "happy", 0)
        return image

    def test_dance_has_visible_temporal_motion(self):
        first = self.render(0.0)
        second = self.render(0.25)
        self.assertIsNotNone(first.getbbox())
        self.assertNotEqual(first.tobytes(), second.tobytes())

    def test_locomotion_and_jump_have_visible_motion(self):
        for action, later in (("walk", 0.35), ("run", 0.25), ("chase", 0.25), ("jump", 0.25)):
            with self.subTest(action=action):
                self.assertNotEqual(self.render(0.0, action).tobytes(),
                                    self.render(later, action).tobytes())

    def test_interaction_actions_have_visible_motion(self):
        for action in ("wave", "clap", "swim", "push", "pull"):
            with self.subTest(action=action):
                self.assertNotEqual(self.render(0.0, action).tobytes(),
                                    self.render(0.4, action).tobytes())

    def test_action_motion_changes_a_meaningful_pixel_area(self):
        # A blinking eye alone must not count as substantial animation.
        # Compare two poses using a conservative changed-pixel threshold.
        for action, later in (("dance", 0.25), ("walk", 0.35),
                              ("run", 0.25), ("jump", 0.25)):
            with self.subTest(action=action):
                first = self.render(0.0, action)
                second = self.render(later, action)
                diff = ImageChops.difference(first, second).convert("L")
                changed = diff.point(lambda value: 255 if value >= 24 else 0)
                changed_pixels = changed.histogram()[255]
                self.assertGreater(changed_pixels, 2000,
                                   f"{action} only changed {changed_pixels} pixels")

    def test_locomotion_arms_counter_swing_with_legs(self):
        # Compare hands returned by the renderer: each arm must move
        # vertically, and the left/right motion must oppose each other.
        for action in ("walk", "run", "chase", "sneak"):
            with self.subTest(action=action):
                def hands_at(t):
                    image = Image.new("RGB", (1080, 1920), (32, 36, 48))
                    return _actor(ImageDraw.Draw(image), "fox", 540, 800,
                                  t, action, "happy", 0)
                start = hands_at(0.0)
                later = hands_at(0.25)
                left_delta = later[0][1] - start[0][1]
                right_delta = later[1][1] - start[1][1]
                self.assertNotEqual(left_delta, 0)
                self.assertEqual(left_delta, -right_delta)

    def test_dance_is_deterministic(self):
        self.assertEqual(self.render(0.25).tobytes(), self.render(0.25).tobytes())

    def test_dance_differs_from_idle(self):
        self.assertNotEqual(self.render(0.25).tobytes(), self.render(0.25, "idle").tobytes())


if __name__ == "__main__":
    unittest.main()
