"""Checks actual plot progression over the ENTIRE narrated shot, not blinks.

Independent deterministic scene-time sampling at four narrative quarters.
No changes to publisher configuration, voice generation or fiction safety gates.
"""
import unittest

from PIL import Image, ImageChops

from astra_errors import CreativeReject
from astra_v2.human_action_choreography import ACTION_SEQUENCE, action_state
from astra_v2.human_story_performance import PERFORMANCE
from astra_v2.omniroute_local import catalog
from astra_v2.unified_story_engine import draw_story_frame, validate_story_shot

DURATION = 12.0
SAMPLES = (.08, .32, .60, .88)
STAGE = (105, 555, 1015, 1325)


def records():
    for story in catalog(max_candidates=30):
        for beat in story["story_beats"]:
            yield {**beat, "story_visual_seed": story["content_id"],
                   "story_title": story["title"], "duration": DURATION}


def frame(shot, p):
    result = Image.new("RGB", (1080, 1920), (13, 22, 37))
    assert draw_story_frame(result, shot, p * DURATION) == "human"
    return result


class HumanStoryChoreographyTests(unittest.TestCase):
    def test_each_approved_action_has_four_distinct_semantic_stage_cues(self):
        self.assertEqual(set(ACTION_SEQUENCE), set(PERFORMANCE))
        self.assertEqual(len(ACTION_SEQUENCE), 16)
        for shot in records():
            self.assertEqual(validate_story_shot(shot), "human")
            action = shot["story_human_action"]
            cues = ACTION_SEQUENCE[action]
            self.assertEqual(len(cues), 4)
            self.assertEqual(len(set(cues)), 4)
            observed = [action_state(action, p*DURATION, DURATION)
                        for p in SAMPLES]
            self.assertEqual([s.phase for s in observed], [0, 1, 2, 3])
            self.assertEqual([s.cue for s in observed], list(cues))
            self.assertEqual(action_state(action, DURATION, DURATION).phase, 3)

    def test_each_of_16_scenes_has_substantial_visual_progression_across_quarters(self):
        for shot in records():
            with self.subTest(action=shot["story_human_action"]):
                frames = [frame(shot, p) for p in SAMPLES]
                for a, b in zip(frames, frames[1:]):
                    delta = ImageChops.difference(a.crop(STAGE), b.crop(STAGE))
                    bbox = delta.getbbox()
                    self.assertIsNotNone(bbox, "Entire scene froze between story quarters")
                    changed_pixels = sum(delta.convert("L").point(
                        lambda x: 1 if x > 18 else 0).getdata())
                    self.assertGreater(changed_pixels, 2000,
                        "Only a blink or tiny decorative animation changed")
                # The authored original performance remains restricted to stage.
                # The sea-door finale intentionally replaces the upper backdrop
                # with a static underwater environment. Keep that region stable
                # across story time, while retaining the strict lower caption band.
                reference = Image.new("RGB", (1080,1920), (13,22,37))
                for index, pic in enumerate(frames):
                    if shot["story_human_action"] == "seal_and_reveal_sea_door":
                        upper = (0,0,1080,480)
                        upper_delta = ImageChops.difference(
                            pic.crop(upper), frames[0].crop(upper)).getbbox()
                        # Only the left-side underwater bubble field animates
                        # above the stage. Keep that motion confined to its
                        # backdrop lane; no actor or prop may enter the header.
                        if upper_delta is not None:
                            self.assertLessEqual(upper_delta[2], 405,
                                "Actor/prop entered headline-safe region")
                        regions = ((0,1400,1080,1920),)
                    else:
                        regions = ((0,0,1080,480), (0,1400,1080,1920))
                    for region in regions:
                        self.assertIsNone(ImageChops.difference(
                            pic.crop(region), reference.crop(region)).getbbox(),
                            "Action overlapped headline or caption-safe region")

    def test_pilot_second_radio_is_hidden_until_narrated_discovery(self):
        # Regression from the real Episode 1 MP4: the second radio was already
        # visible at ~16.4s, before its narrated reveal at ~22s.
        from unittest.mock import patch
        from astra_v2.human_story_performance import draw_human_scene, _radio
        beat = next(shot for shot in records()
                    if shot["story_human_action"] == "trace_cable")
        seen = []
        for progress in (.12, .49, .62, .88):
            canvas = Image.new("RGB", (1080, 1920), (13, 22, 37))
            with patch("astra_v2.human_story_performance._radio",
                       wraps=_radio) as calls:
                self.assertTrue(draw_human_scene(canvas, beat, progress * DURATION))
            radios = [(call.args[1], call.args[2]) for call in calls.call_args_list]
            self.assertIn((757, 945), radios)
            seen.append(radios)
        self.assertEqual([len(radios) for radios in seen], [1, 1, 2, 2])
        self.assertNotIn((342, 1138), seen[0])
        self.assertNotIn((342, 1138), seen[1])
        self.assertIn((342, 1138), seen[2])
        self.assertIn((342, 1138), seen[3])

    def test_pilot_city_blackout_is_visible_through_actual_stage_camera(self):
        # The pre-fix source skyline had towers near x=688..947. Studio's
        # reaction close-up crops at x~27..727, hiding four of five towers.
        # This checks *the real composed output* rather than raw Pillow art.
        from PIL import ImageDraw
        from astra_v2.human_story_performance import (
            BLACKOUT_TOWERS, _blackout_skyline, draw_human_scene, GOLD,
        )
        from astra_v2.human_story_composition import stage_crop_box
        from astra_v2.human_cinematic_camera import apply_human_camera

        beat = next(shot for shot in records()
                    if shot["story_human_action"] == "hear_warning")
        self.assertEqual(len(BLACKOUT_TOWERS), 5)
        for progress in (.10, .30, .60, .88, .99):
            with self.subTest(progress=progress):
                left, top, right, bottom = stage_crop_box(
                    "hear_warning", progress * DURATION, DURATION)
                for x0, y0, x1, y1 in BLACKOUT_TOWERS:
                    self.assertGreaterEqual(x0, left)
                    self.assertLessEqual(x1, right)
                    self.assertGreaterEqual(y0, top)
                    self.assertLessEqual(y1, bottom)

        snapshots = []
        for progress in (.10, .90):
            original = Image.new("RGB", (1080, 1920), (13, 22, 37))
            self.assertTrue(draw_human_scene(original, beat, progress * DURATION))
            stage = apply_human_camera(original, beat, progress * DURATION)
            left, top, right, bottom = stage_crop_box(
                "hear_warning", progress * DURATION, DURATION)
            colors = []
            for x0, y0, _, _ in BLACKOUT_TOWERS:
                # Center of a real skyline-window, *after* camera resampling.
                src_x, src_y = x0 + 8, y0 + 17
                x = round((src_x - left) * 1080 / (right - left))
                y = 480 + round((src_y - top) * 890 / (bottom - top))
                colors.append(stage.getpixel((x, y)))
            snapshots.append(colors)
        early, late = snapshots
        # At least four distinct lit windows must be visible despite the
        # actor and camera transform, then turn dark within the shot.
        self.assertGreaterEqual(sum(c[0] > 180 and c[1] > 125
                                    for c in early), 4, early)
        self.assertGreaterEqual(sum(c[0] < 140 and c[1] < 140
                                    for c in late), 4, late)
        self.assertNotEqual(early, late)

        for event, expected in ((0.0, 5), (.5, 3), (1.0, 0)):
            canvas = Image.new("RGB", (1080, 1920))
            result = _blackout_skyline(ImageDraw.Draw(canvas), event)
            self.assertEqual(result["lit_buildings"], expected)
            self.assertFalse(result["verified_visual_semantics"])
        for bad in (-.1, 1.1, float("nan"), "invalid"):
            with self.assertRaises(CreativeReject):
                _blackout_skyline(ImageDraw.Draw(
                    Image.new("RGB", (1080, 1920))), bad)

    def test_break_glass_key_reveals_two_halves_after_setup(self):
        beat = next(shot for shot in records()
                    if shot["story_human_action"] == "split_glass_key")
        early, late = frame(beat,.10), frame(beat,.85)
        prop_region=(400,875,720,1070)
        self.assertIsNotNone(ImageChops.difference(
            early.crop(prop_region),late.crop(prop_region)).getbbox())
        self.assertLess(action_state("split_glass_key",DURATION*.10,DURATION).event,.02)
        self.assertGreater(action_state("split_glass_key",DURATION*.85,DURATION).event,.95)

    def test_underwater_notebook_survives_the_actual_opaque_environment_repaint(self):
        from astra_v2.human_story_performance import draw_human_scene
        from astra_v2.visual_artifact_backdrop import apply_underwater_reveal

        beat = next(shot for shot in records()
                    if shot["story_human_action"] == "seal_and_reveal_sea_door")
        first = Image.new("RGB", (1080, 1920), (13, 22, 37))
        last = Image.new("RGB", (1080, 1920), (13, 22, 37))
        self.assertTrue(draw_human_scene(first, beat, DURATION*.10))
        self.assertTrue(draw_human_scene(last, beat, DURATION*.93))
        identity = "episode-four-underwater-notebook-regression"
        apply_underwater_reveal(first, identity)
        apply_underwater_reveal(last, identity)
        # The final page is in the preserved left stage; the old right-side
        # page region is deliberately repainted by the underwater door layer.
        page=(35,1078,395,1382)
        diff=ImageChops.difference(first.crop(page),last.crop(page))
        self.assertIsNotNone(diff.getbbox())
        self.assertEqual(action_state("seal_and_reveal_sea_door",
                                     DURATION*.10,DURATION).aftermath,0.0)
        self.assertGreater(action_state("seal_and_reveal_sea_door",
                                        DURATION*.93,DURATION).aftermath,.9)
        # Confirm a recognizable page field remains after the exact overlay.
        self.assertNotEqual(last.getpixel((70,1110)), first.getpixel((70,1110)))

    def test_authorized_action_contract_remains_fail_closed(self):
        record=next(records())
        for change in (
            {"story_visual_seed":"unauthorized-series"},
            {"story_human_action":"not-in-story"},
            {"story_human_actor":"unknown-person"},
        ):
            with self.subTest(change=change), self.assertRaises(CreativeReject):
                validate_story_shot({**record,**change})
        for values in (
            ("unknown-action",2,12),
            ("discover_radio",-1,12),
            ("discover_radio",float("nan"),12),
            ("discover_radio",float("inf"),12),
            ("discover_radio",1,0),
            ("discover_radio",1,-5),
        ):
            with self.subTest(values=values), self.assertRaises((ValueError,CreativeReject)):
                action_state(*values)

    def test_state_and_frames_deterministic_at_identical_story_time(self):
        shot = next(records())
        a=frame(shot,.61)
        b=frame(shot,.61)
        self.assertEqual(a.tobytes(),b.tobytes())
        self.assertEqual(action_state("discover_radio",7.32,12),
                         action_state("discover_radio",7.32,12))

    def test_underwater_reveal_replaces_the_entire_old_floor_strip(self):
        from astra_v2.human_story_performance import _underwater_left_stage
        from astra_v2.visual_artifact_backdrop import apply_underwater_reveal
        frame = Image.new("RGB", (1080, 1920), (92, 65, 55))
        _underwater_left_stage(frame, 1.0)
        apply_underwater_reveal(frame, "underwater-floor-regression")
        # The right strip used to retain brown floor below the 1260px overlay.
        self.assertNotEqual(frame.getpixel((900, 1320)), (92, 65, 55))
        # Both sides of the preserved stage must replace the inherited floor.
        self.assertNotEqual(frame.getpixel((200, 1270)), (92, 65, 55))
        self.assertNotEqual(frame.getpixel((200, 1350)), (92, 65, 55))


if __name__ == "__main__":
    unittest.main()
