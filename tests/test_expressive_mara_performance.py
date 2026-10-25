"""Per-beat expressive actor QA for The Tomorrow Signal Season 1.

These pixel assertions prove changes in facial acting and physical gestures.
They do not claim real lip synchronization, photorealism or 3D animation.
"""
import math
import unittest

from PIL import Image, ImageChops

from astra_errors import CreativeReject
from astra_v2.human_story_performance import (
    ACTIONS, EPISODE_TWO_ACTIONS, EPISODE_THREE_ACTIONS,
    EPISODE_FOUR_ACTIONS, PERFORMANCE, _mara,
)
from astra_v2.omniroute_local import catalog
from astra_v2.unified_story_engine import draw_story_frame, validate_story_shot


def actor_frame(*, emotion="focused", gaze=0, gesture="consider", t=.8):
    frame=Image.new("RGB",(1080,1920),(16,26,38))
    from PIL import ImageDraw
    draw=ImageDraw.Draw(frame)
    _mara(draw,490,872,t,reaching=True,emotion=emotion,
          gaze=gaze,gesture=gesture)
    return frame


class ExpressiveMaraPerformanceTests(unittest.TestCase):
    def test_all_sixteen_canonical_scenes_get_distinct_authored_intentions(self):
        approved=set(ACTIONS+EPISODE_TWO_ACTIONS+
                     EPISODE_THREE_ACTIONS+EPISODE_FOUR_ACTIONS)
        self.assertEqual(set(PERFORMANCE),approved)
        self.assertEqual(len(PERFORMANCE),16)
        moods={value[0] for value in PERFORMANCE.values()}
        gestures={value[2] for value in PERFORMANCE.values()}
        self.assertGreaterEqual(len(moods),8)
        self.assertEqual(gestures,{"consider","protect","open"})
        for story in catalog(max_candidates=30):
            for beat in story["story_beats"]:
                shot={**beat,"story_visual_seed":story["content_id"]}
                self.assertEqual(validate_story_shot(shot),"human")
                self.assertIn(beat["story_human_action"],PERFORMANCE)

    def test_mood_actually_changes_brows_eyes_and_mouth(self):
        a=actor_frame(emotion="afraid",gaze=1)
        b=actor_frame(emotion="determined",gaze=1)
        head=(383,590,598,797)
        self.assertIsNotNone(ImageChops.difference(
            a.crop(head),b.crop(head)).getbbox())
        c=actor_frame(emotion="grieving",gaze=-1)
        self.assertIsNotNone(ImageChops.difference(
            b.crop(head),c.crop(head)).getbbox())

    def test_eyeline_changes_without_changing_costume_or_person(self):
        a=actor_frame(emotion="curious",gaze=1)
        b=actor_frame(emotion="curious",gaze=-1)
        head=(411,674,560,752)
        self.assertIsNotNone(ImageChops.difference(
            a.crop(head),b.crop(head)).getbbox())
        jacket=(395,820,590,1010)
        self.assertIsNone(ImageChops.difference(
            a.crop(jacket),b.crop(jacket)).getbbox())

    def test_physical_gestures_distinct_from_one_generic_raise(self):
        a=actor_frame(gesture="protect")
        b=actor_frame(gesture="open")
        c=actor_frame(gesture="consider")
        arm=(280,780,720,1040)
        self.assertIsNotNone(ImageChops.difference(
            a.crop(arm),b.crop(arm)).getbbox())
        self.assertIsNotNone(ImageChops.difference(
            a.crop(arm),c.crop(arm)).getbbox())

    def test_scene_acting_and_typography_safety_preserved(self):
        for episode in range(1,5):
            story=next(s for s in catalog(max_candidates=30)
                       if s["episode"]==episode)
            for beat in story["story_beats"]:
                shot={**beat,"story_visual_seed":story["content_id"],
                      "story_title":story["title"]}
                frame=Image.new("RGB",(1080,1920),(16,26,38))
                self.assertEqual(draw_story_frame(frame,shot,.78),"human")
                for zone in ((0,0,1080,480),(0,1400,1080,1920)):
                    reference=Image.new("RGB",frame.crop(zone).size,(16,26,38))
                    self.assertIsNone(ImageChops.difference(
                        frame.crop(zone),reference).getbbox(),
                        "Character drawing overlapped reserved caption/headline")

    def test_blinks_and_gestures_are_deterministic_not_random(self):
        self.assertEqual(actor_frame(t=1.2).tobytes(),
                         actor_frame(t=1.2).tobytes())

    def test_unknown_face_eyeline_or_animation_time_is_rejected(self):
        for opts in ({"emotion":"unapproved"},
                     {"gaze":42},
                     {"gesture":"magic"},
                     {"t":float("nan")},
                     {"t":float("inf")}):
            with self.subTest(opts=opts),self.assertRaises(CreativeReject):
                actor_frame(**opts)


if __name__=="__main__":
    unittest.main()
