"""Deterministic visual evidence that Episode 1 events are drawable.

Pixel checks show intended stage geometry and causal timing, NOT full video
semantic fidelity; production must still require independent MP4 review.
"""
import math
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageChops

from astra_errors import CreativeReject
from astra_v2.human_pilot_causal_visuals import (
    draw_power_disconnect, draw_blackout_skyline, blackout_lit_window_count,
    draw_escape_stairs,
)
from astra_v2.human_story_performance import (
    draw_human_scene, _door, _mara,
)
from astra_v2.human_action_choreography import action_state
from astra_v2.omniroute_local import catalog

BASE = (9, 19, 29)
DURATION = 12.0


def pilot(action):
    for story in catalog(max_candidates=30):
        if story["content_id"] != "rayvan-season-01-episode-01":
            continue
        for beat in story["story_beats"]:
            if beat["story_human_action"] == action:
                return {**beat, "story_visual_seed": story["content_id"],
                        "story_title": story["title"], "duration": DURATION}
    raise AssertionError(f"pilot action not found: {action}")


def stage(shot, p):
    canvas = Image.new("RGB", (1080, 1920), BASE)
    assert draw_human_scene(canvas, shot, p * DURATION)
    return canvas


class PilotCausalVisualsTests(unittest.TestCase):
    def test_visible_power_lead_disconnects_before_city_blackout(self):
        a = action_state("hear_warning", DURATION*.12, DURATION)
        b = action_state("hear_warning", DURATION*.38, DURATION)
        c = action_state("hear_warning", DURATION*.86, DURATION)
        self.assertEqual(blackout_lit_window_count(a.event), 5)
        self.assertEqual(blackout_lit_window_count(b.event), 5)
        self.assertEqual(blackout_lit_window_count(c.event), 0)
        self.assertLess(a.attention, b.attention)
        self.assertLess(b.attention, c.attention)
        canvas = Image.new("RGB", (1080, 1920), BASE)
        d = ImageDraw.Draw(canvas)
        at_start = draw_power_disconnect(d, a.attention)
        before_outage = draw_power_disconnect(d, b.attention)
        after_outage = draw_power_disconnect(d, c.attention)
        self.assertLess(at_start["plug_separation_px"],
                        before_outage["plug_separation_px"])
        self.assertLess(before_outage["plug_separation_px"],
                        after_outage["plug_separation_px"])
        self.assertFalse(after_outage["visual_semantics_verified"])

    def test_blackout_replaces_five_bright_city_light_groups_with_dark(self):
        early = Image.new("RGB", (1080, 1920), BASE)
        late = early.copy()
        a = draw_blackout_skyline(ImageDraw.Draw(early), 0.0)
        b = draw_blackout_skyline(ImageDraw.Draw(late), 1.0)
        self.assertEqual(a["lit_building_groups"], 5)
        self.assertEqual(b["lit_building_groups"], 0)
        # First facade has a real window at this pixel, not an abstract icon.
        self.assertEqual(early.getpixel((522, 800)), (251, 205, 114))
        self.assertEqual(late.getpixel((522, 800)), (24, 37, 55))
        self.assertIsNotNone(ImageChops.difference(
            early.crop((486, 681, 931, 957)),
            late.crop((486, 681, 931, 957))).getbbox())
        self.assertFalse(b["visual_semantics_verified"])

    def test_stairs_are_physical_treads_behind_actual_moving_door(self):
        closed = Image.new("RGB", (1080, 1920), BASE)
        open_ = closed.copy()
        _door(ImageDraw.Draw(closed), .08, with_stairs=True)
        _door(ImageDraw.Draw(open_), .76, with_stairs=True)
        crop = (750, 790, 945, 1160)
        self.assertIsNotNone(ImageChops.difference(
            closed.crop(crop), open_.crop(crop)).getbbox())
        # The hinged leaf hides more of the staircase as the door closes.
        self.assertNotEqual(closed.getpixel((850, 1100)),
                            open_.getpixel((850, 1100)))
        bare = Image.new("RGB", (1080, 1920), BASE)
        draw_escape_stairs(ImageDraw.Draw(bare))
        self.assertNotEqual(bare.getpixel((900, 1099)), BASE)

    def test_actor_runs_toward_door_not_out_of_frame_to_the_left(self):
        shot = pilot("flee_door")
        positions = []
        for p in (.10, .89):
            with patch("astra_v2.human_story_performance._mara", wraps=_mara) as spy:
                stage(shot, p)
            self.assertEqual(spy.call_count, 1)
            positions.append(spy.call_args.args[1])
        self.assertGreater(positions[1], positions[0]+85)
        self.assertLess(positions[1], 650)
        frame_a, frame_b = stage(shot, .10), stage(shot, .89)
        self.assertIsNotNone(ImageChops.difference(
            frame_a.crop((620, 650, 1015, 1210)),
            frame_b.crop((620, 650, 1015, 1210))).getbbox())

    def test_human_warning_scene_contains_staged_cable_and_blackout(self):
        shot = pilot("hear_warning")
        observed = []
        for p in (.14, .38, .87):
            with patch("astra_v2.human_pilot_causal_visuals.draw_blackout_skyline",
                       wraps=draw_blackout_skyline) as skyline, patch(
                           "astra_v2.human_pilot_causal_visuals.draw_power_disconnect",
                           wraps=draw_power_disconnect) as lead:
                stage(shot, p)
            self.assertEqual(skyline.call_count, 1)
            self.assertEqual(lead.call_count, 1)
            observed.append((skyline.call_args.args[1],
                             lead.call_args.args[1]))
        self.assertEqual([blackout_lit_window_count(row[0]) for row in observed],
                         [5, 5, 0])
        self.assertLess(observed[0][1], observed[1][1])
        self.assertLess(observed[1][1], observed[2][1])

    def test_unknown_invalid_stages_fail_closed(self):
        image = Image.new("RGB", (1080, 1920), BASE)
        d = ImageDraw.Draw(image)
        for bad in (float("nan"), float("inf"), -1, 1.01, True, None):
            with self.subTest(bad=bad):
                with self.assertRaises(CreativeReject):
                    draw_blackout_skyline(d, bad)
                with self.assertRaises(CreativeReject):
                    draw_power_disconnect(d, bad)
        with self.assertRaises(CreativeReject):
            draw_escape_stairs(None)


if __name__ == "__main__":
    unittest.main()
