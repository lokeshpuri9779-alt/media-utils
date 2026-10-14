"""Offline video grammar and comic surprise regressions for ASTRA pilot."""
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops
from astra_v2.cinematic_comedy import (
    REVEAL_START, CAMERA_PRESETS, camera_params, camera_frame,
    draw_gift_surprise, dissolve
)
from astra_v2.comedy_sound import action_cues
from astra_v2.coordinated_development import build_comedy_demo, frame


class CinematicComedyTests(unittest.TestCase):
    def test_camera_actions_have_distinct_moves_and_bounded_crop(self):
        self.assertEqual(set(CAMERA_PRESETS),
                         {"approach", "point", "carry", "react", "celebrate"})
        motion = [camera_params(name, 2.5) for name in CAMERA_PRESETS]
        self.assertEqual(len(set(motion)), 5)
        self.assertTrue(all(1 <= zoom <= 1.25 for zoom, _, _ in motion))
        for name in CAMERA_PRESETS:
            source = Image.new("RGB", (540, 960), (41, 74, 98))
            changed = camera_frame(source, name, 1.9)
            self.assertEqual(changed.size, source.size)
            self.assertEqual(changed.getpixel((0, 0)), (41, 74, 98))
            self.assertEqual(changed.getpixel((539, 959)), (41, 74, 98))
        with self.assertRaises(ValueError):
            camera_params("fly", .5)

    def test_surprise_appears_after_delay_with_spring_and_duck(self):
        original = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        before = original.copy()
        self.assertFalse(draw_gift_surprise(before, 410, 820, 165, 160, 1.0))
        self.assertIsNone(before.getbbox())
        after = original.copy()
        self.assertTrue(draw_gift_surprise(after, 410, 820, 165, 160, 2.30))
        self.assertIsNotNone(after.getbbox())
        self.assertTrue(after.getbbox()[1] < 630)
        repeated = original.copy()
        draw_gift_surprise(repeated, 410, 820, 165, 160, 2.30)
        self.assertEqual(after.tobytes(), repeated.tobytes())

    def test_dissolves_are_brief_and_do_not_add_frames(self):
        a = Image.new("RGB", (540, 960), (19, 27, 43))
        b = Image.new("RGB", (540, 960), (230, 165, 67))
        self.assertEqual(dissolve(a, b, 0).getpixel((20, 20)), a.getpixel((20, 20)))
        self.assertEqual(dissolve(a, b, .25).getpixel((20, 20)), b.getpixel((20, 20)))
        middle = dissolve(a, b, .12).getpixel((20, 20))
        self.assertTrue(all(a.getpixel((20, 20))[i] < middle[i] < b.getpixel((20, 20))[i] for i in range(3)))
        with self.assertRaises(ValueError):
            dissolve(a, Image.new("RGB", (3, 3)), .1)

    def test_comedy_payoff_is_visible_and_sound_is_synchronized(self):
        plan = build_comedy_demo()
        finale = plan["scenes"][-1]
        with patch("astra_v2.coordinated_development.draw_gift_surprise",
                   wraps=draw_gift_surprise) as effect:
            early = frame(finale, .8)
            late = frame(finale, 2.3)
            self.assertFalse(effect.call_args_list[0].args[-1] >= REVEAL_START)
            self.assertTrue(effect.call_args_list[-1].args[-1] >= REVEAL_START)
            self.assertIsNotNone(ImageChops.difference(early, late).getbbox())
            self.assertEqual(early.size, late.size)
        honks = [cue for cue in action_cues(plan, 3)
                 if cue["event"] == "duck_honk"]
        self.assertEqual(len(honks), 1)
        self.assertEqual(honks[0]["scene"], 5)
        self.assertTrue(12 + REVEAL_START < honks[0]["at_seconds"] < 15)


if __name__ == "__main__":
    unittest.main()
