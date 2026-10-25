"""Narrative anticipations and reactions: verified 2D body/head acting.

Avoid proving improvement with only a checksum: we test body/facial pixels,
planted feet, 30 FPS motion continuity, opposite doppelganger performance and
the previously verified wrist-attached plot objects.
"""
import math
import unittest

from PIL import Image, ImageChops, ImageDraw

from astra_errors import CreativeReject
from astra_v2.human_action_choreography import ACTION_SEQUENCE
from astra_v2.human_performance_cues import LEAN_DIRECTION, acting_cue
from astra_v2.human_story_performance import _mara, PERFORMANCE
from astra_v2.omniroute_local import catalog
from astra_v2.unified_story_engine import draw_story_frame

BACKGROUND=(13,23,38)
SIZE=(1080,1920)


def actor(t, **opts):
    image=Image.new("RGB",SIZE,BACKGROUND)
    joints=_mara(ImageDraw.Draw(image),375,860,t,**opts)
    return image,joints


class PhysicalStoryActingTests(unittest.TestCase):
    def test_all_sixteen_narrative_actions_get_authored_reaction_cues(self):
        self.assertEqual(set(ACTION_SEQUENCE),set(LEAN_DIRECTION))
        self.assertEqual(set(ACTION_SEQUENCE),set(PERFORMANCE))
        for action in ACTION_SEQUENCE:
            with self.subTest(action=action):
                first=acting_cue(action,0,12)
                approach=acting_cue(action,3.5,12)
                impact=acting_cue(action,6.5,12)
                reaction=acting_cue(action,11.2,12)
                self.assertAlmostEqual(first.lean,0,delta=.01)
                self.assertGreater(approach.anticipation,.4)
                self.assertGreater(impact.contact,.4)
                self.assertGreater(reaction.reaction,.9)
                self.assertNotAlmostEqual(approach.lean,impact.lean,delta=1.0)
                self.assertNotAlmostEqual(impact.lean,reaction.lean,delta=2.0)
                self.assertGreater(reaction.expression_strength,first.expression_strength)

    def test_continuous_torso_motion_at_30_fps(self):
        for action in ("discover_radio","hear_warning","flee_door",
                       "split_glass_key","seal_and_reveal_sea_door"):
            points=[acting_cue(action,i/30,12) for i in range(360)]
            for before,after in zip(points,points[1:]):
                self.assertLessEqual(abs(after.lean-before.lean),.5,
                                     "Torso will snap between 30 FPS frames")
                self.assertLessEqual(abs(after.expression_strength-before.expression_strength),.02)
                self.assertTrue(0<=after.expression_strength<=1)

    def test_upper_body_anticipates_and_reacts_with_planted_leg_coordinates(self):
        prep,prep_hands=actor(1.0,reaching=True,emotion="afraid",lean=11,expression_strength=.52)
        react,react_hands=actor(1.0,reaching=True,emotion="afraid",lean=-9,expression_strength=1.)
        # Head and arms turn in response to events; boot region remains planted.
        self.assertIsNotNone(ImageChops.difference(
            prep.crop((258,558,523,1035)),
            react.crop((258,558,523,1035))).getbbox())
        self.assertEqual(prep.crop((207,1115,543,1240)).tobytes(),
                         react.crop((207,1115,543,1240)).tobytes(),
                         "Foot anchors slid when only the torso should lean")
        # Wrist-attached prop geometry follows the same rendered arm shift.
        self.assertNotEqual(prep_hands["right_hand"],react_hands["right_hand"])

    def test_expression_intensity_changes_face_not_unrelated_scene_background(self):
        low,_=actor(.8,emotion="startled",gaze=1,expression_strength=.45)
        high,_=actor(.8,emotion="startled",gaze=1,expression_strength=1.)
        self.assertIsNotNone(ImageChops.difference(
            low.crop((278,610,469,791)),
            high.crop((278,610,469,791))).getbbox())
        self.assertEqual(low.crop((600,600,900,1000)).tobytes(),
                         high.crop((600,600,900,1000)).tobytes())

    def test_double_responds_as_mirror_not_duplicate_pose(self):
        a=acting_cue("split_glass_key",6.4,12,double=False)
        b=acting_cue("split_glass_key",6.4,12,double=True)
        self.assertAlmostEqual(a.lean,-b.lean,delta=.001)
        self.assertEqual(a.expression_strength,b.expression_strength)
        self.assertNotEqual(a.lean,0)

    def test_actual_timed_scenes_preserve_original_approved_grammar(self):
        count=0
        for story in catalog(max_candidates=30):
            for beat in story["story_beats"]:
                shot={**beat,"story_visual_seed":story["content_id"],
                      "story_title":story["title"],"duration":12}
                a=Image.new("RGB",SIZE,BACKGROUND)
                b=a.copy()
                self.assertEqual(draw_story_frame(a,shot,3.5),"human")
                self.assertEqual(draw_story_frame(b,shot,10.8),"human")
                self.assertIsNotNone(ImageChops.difference(
                    a.crop((145,570,975,1255)),
                    b.crop((145,570,975,1255))).getbbox())
                for frame in (a,b):
                    for safe in ((0,0,1080,480),(0,1400,1080,1920)):
                        self.assertIsNone(ImageChops.difference(
                            frame.crop(safe),
                            Image.new("RGB",frame.crop(safe).size,BACKGROUND)).getbbox())
                count+=1
        self.assertEqual(count,16)

    def test_invalid_actor_pose_and_scene_timing_fail_closed(self):
        for opts in (
            {"lean":float("nan")},
            {"lean":float("inf")},
            {"lean":25},
            {"expression_strength":1.1},
            {"expression_strength":float("nan")},
        ):
            with self.subTest(opts=opts),self.assertRaises(CreativeReject):
                actor(.8,**opts)
        for args in (("unapproved_action",.5,12),
                     ("discover_radio",-1,12),
                     ("discover_radio",float("nan"),12),
                     ("discover_radio",1,0)):
            with self.subTest(args=args),self.assertRaises((CreativeReject,ValueError)):
                acting_cue(*args)
        with self.assertRaises(CreativeReject):
            acting_cue("discover_radio",1,12,double="yes")


if __name__=="__main__":
    unittest.main()
