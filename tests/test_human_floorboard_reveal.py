"""Review-only regression for Episode 1's missing physical floorboard reveal.

These tests validate actual pixels and permitted action routing, NOT whether
the complete encoded MP4 satisfies semantic/narrative visual review.
"""
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw
from astra_errors import CreativeReject
from astra_v2.human_floorboard_reveal import (
    OPENING, LIFTED_BOARD, WOOD, VOID, draw_floorboard_hatch,
    floorboard_panel, floorboard_reveal_fraction,
)
from astra_v2.human_story_performance import draw_human_scene
from astra_v2.omniroute_local import catalog


def trace_shot():
    story = next(s for s in catalog(max_candidates=30)
                 if s["content_id"] == "rayvan-season-01-episode-01")
    beat = next(b for b in story["story_beats"]
                if b["story_human_action"] == "trace_cable")
    return {**beat, "story_visual_seed": story["content_id"],
            "story_title": story["title"], "duration": 12.0}


class FloorboardRevealTests(unittest.TestCase):
    def test_physical_hatch_covers_room_first_then_exposes_darker_space(self):
        start = Image.new("RGB", (1080, 1920), (23, 35, 50))
        end = start.copy()
        a = draw_floorboard_hatch(ImageDraw.Draw(start), 0.0)
        b = draw_floorboard_hatch(ImageDraw.Draw(end), 1.0)
        self.assertEqual(a["hatch_open_fraction"], 0.0)
        self.assertEqual(b["hatch_open_fraction"], 1.0)
        self.assertFalse(a["verified_semantics"])
        self.assertFalse(b["verified_semantics"])
        self.assertEqual(start.getpixel((370, 1100)), WOOD)
        self.assertEqual(end.getpixel((370, 1100)), VOID)
        self.assertEqual(floorboard_panel(0), OPENING)
        self.assertEqual(floorboard_panel(1), LIFTED_BOARD)
        changed = ImageChops.difference(
            start.crop((150, 925, 510, 1230)),
            end.crop((150, 925, 510, 1230)))
        self.assertIsNotNone(changed.getbbox())
        # The artwork remains entirely in the subject stage; no changes to
        # text/header and caption-safe regions.
        for region in ((0, 0, 1080, 480), (0, 1400, 1080, 1920)):
            self.assertIsNone(ImageChops.difference(
                start.crop(region), end.crop(region)).getbbox())

    def test_opening_is_finite_gradual_and_deterministic(self):
        fractions = [floorboard_reveal_fraction(x / 100) for x in range(101)]
        self.assertTrue(all(a <= b for a, b in zip(fractions, fractions[1:])))
        self.assertEqual(fractions[0], 0)
        self.assertEqual(fractions[-1], 1)
        for event in (0, .1, .4, .55, .75, 1):
            with self.subTest(event=event):
                self.assertEqual(floorboard_panel(event), floorboard_panel(event))
                self.assertTrue(all(80 <= x <= 1000 and 555 <= y <= 1260
                                    for x, y in floorboard_panel(event)))
        for bad in (-.1, 1.01, float("nan"), float("inf"), "bad", None, True):
            with self.subTest(bad=bad), self.assertRaises(CreativeReject):
                floorboard_reveal_fraction(bad)

    def test_actual_pilot_actor_path_draws_hatch_and_delays_second_radio(self):
        from astra_v2.human_action_choreography import action_state
        from astra_v2.human_story_performance import _radio
        shot = trace_shot()
        rendered = []
        for p in (.12, .49, .62, .88):
            canvas = Image.new("RGB", (1080, 1920), (23, 35, 50))
            with patch("astra_v2.human_floorboard_reveal.draw_floorboard_hatch",
                       wraps=draw_floorboard_hatch) as hatch, \
                 patch("astra_v2.human_story_performance._radio",
                       wraps=_radio) as radios:
                self.assertTrue(draw_human_scene(canvas, shot, p * 12))
            hatch.assert_called_once()
            self.assertAlmostEqual(hatch.call_args.args[1],
                                   action_state("trace_cable", p * 12, 12).event)
            coords = [(x.args[1], x.args[2]) for x in radios.call_args_list]
            rendered.append((canvas, coords))
        self.assertEqual([len(radio) for _, radio in rendered], [1, 1, 2, 2])
        self.assertIn((342, 1109), rendered[-1][1])
        self.assertIsNotNone(ImageChops.difference(
            rendered[0][0].crop((220, 1030, 520, 1200)),
            rendered[-1][0].crop((220, 1030, 520, 1200))).getbbox())

    def test_invalid_image_surface_rejected_without_silent_fallback(self):
        with self.assertRaises(CreativeReject):
            draw_floorboard_hatch(None, .5)


if __name__ == "__main__":
    unittest.main()
