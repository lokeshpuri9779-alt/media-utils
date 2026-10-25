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
                reference = Image.new("RGB", (1080,1920), (13,22,37))
                for pic in frames:
                    for region in ((0,0,1080,480), (0,1400,1080,1920)):
                        self.assertIsNone(ImageChops.difference(
                            pic.crop(region), reference.crop(region)).getbbox(),
                            "Action overlapped headline or caption-safe region")

    def test_break_glass_key_reveals_two_halves_after_setup(self):
        beat = next(shot for shot in records()
                    if shot["story_human_action"] == "split_glass_key")
        early, late = frame(beat,.10), frame(beat,.85)
        prop_region=(400,875,720,1070)
        self.assertIsNotNone(ImageChops.difference(
            early.crop(prop_region),late.crop(prop_region)).getbbox())
        self.assertLess(action_state("split_glass_key",DURATION*.10,DURATION).event,.02)
        self.assertGreater(action_state("split_glass_key",DURATION*.85,DURATION).event,.95)

    def test_underwater_door_is_a_final_reveal_not_onscreen_at_opening(self):
        beat = next(shot for shot in records()
                    if shot["story_human_action"] == "seal_and_reveal_sea_door")
        first, last = frame(beat,.10), frame(beat,.93)
        page=(602,1020,980,1266)
        diff=ImageChops.difference(first.crop(page),last.crop(page))
        self.assertIsNotNone(diff.getbbox())
        self.assertEqual(action_state("seal_and_reveal_sea_door",
                                     DURATION*.10,DURATION).aftermath,0.0)
        self.assertGreater(action_state("seal_and_reveal_sea_door",
                                        DURATION*.93,DURATION).aftermath,.9)

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


if __name__ == "__main__":
    unittest.main()
