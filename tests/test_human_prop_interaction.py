"""Prop grip continuity: the same actor wrists must control radio and key.

Source pixels and geometry are checked at early, middle and final story
positions. The real Studio encoded MP4s remain separately audited by CI.
"""
import math
import unittest

from PIL import Image, ImageChops, ImageDraw

from astra_errors import CreativeReject
from astra_v2.human_story_performance import _mara, _radio
from astra_v2.human_prop_interaction import (
    carried_radio_center, draw_radio_in_hand, draw_split_key_in_hands,
    key_half_positions,
)
from astra_v2.human_action_choreography import action_state
from astra_v2.omniroute_local import catalog
from astra_v2.unified_story_engine import draw_story_frame


BACKGROUND=(13,24,39)


def character(time, x=390, y=877, **opts):
    frame=Image.new("RGB",(1080,1920),BACKGROUND)
    hand=_mara(ImageDraw.Draw(frame),x,y,time,**opts)
    assert set(hand)=={"left_hand","right_hand"}
    return frame,hand


class WristAnchoredPropsTests(unittest.TestCase):
    def test_radio_grip_is_fixed_relative_to_same_moving_hand(self):
        positions=[]
        for t in (.18,.46,1.04,1.81):
            image,actor=character(t,running=True,carrying=True,gesture="protect")
            hand=actor["right_hand"]
            receipt=draw_radio_in_hand(ImageDraw.Draw(image),hand,t,_radio)
            self.assertTrue(receipt["attached"])
            self.assertEqual(receipt["hand"],hand)
            self.assertEqual(receipt["grip_offset"],(58,35))
            cx,cy=receipt["radio_center"]
            self.assertEqual(cx-hand[0],58)
            self.assertEqual(cy-hand[1],35)
            self.assertTrue(100<cx<980 and 560<cy<1300)
            positions.append(receipt["radio_center"])
        self.assertGreater(len(set(positions)),2,
                           "Receiver is frozen while Mara moves")

    def test_key_both_halves_end_exactly_at_different_wrist_joints(self):
        _,mara=character(1.1,x=280,y=865,reaching=True)
        _,double=character(1.1,x=765,y=865,reaching=True,emotion="knowing")
        a,b=mara["right_hand"],double["left_hand"]
        start=key_half_positions(.05,a,b)
        middle=key_half_positions(.45,a,b)
        end=key_half_positions(1.,a,b)
        self.assertFalse(start["attached"])
        self.assertFalse(middle["attached"])
        self.assertTrue(end["attached"])
        self.assertEqual(end["mara"],a)
        self.assertEqual(end["double"],b)
        self.assertNotEqual(end["mara"],end["double"])
        self.assertLess(math.dist(start["mara"],a),
                        math.dist(start["double"],a)+500)
        self.assertLess(math.dist(middle["mara"],a),
                        math.dist(start["mara"],a))
        self.assertLess(math.dist(middle["double"],b),
                        math.dist(start["double"],b))
        canvas=Image.new("RGB",(1080,1920),BACKGROUND)
        receipt=draw_split_key_in_hands(ImageDraw.Draw(canvas),1.,a,b)
        self.assertTrue(receipt["attached"])
        self.assertEqual(receipt["mara"],a)
        self.assertEqual(receipt["double"],b)

    def test_key_fragment_motion_uses_progressive_placement_not_teleport(self):
        a=(429,838)
        b=(612,914)
        # Adjacent 30fps samples throughout actual event: no large jumps.
        previous=None
        for i in range(16,30):
            p=i/30
            points=key_half_positions(p,a,b)
            if previous:
                self.assertLess(math.dist(points["mara"],previous["mara"]),12)
                self.assertLess(math.dist(points["double"],previous["double"]),12)
            previous=points

    def test_flee_and_key_scenes_really_render_correct_props(self):
        for number,action in ((1,"flee_door"),(4,"split_glass_key")):
            story=next(s for s in catalog(max_candidates=30)
                       if s['episode']==number)
            beat=next(s for s in story['story_beats']
                      if s['story_human_action']==action)
            shot={**beat,"story_visual_seed":story['content_id'],
                  "story_title":story['title'],"duration":12.0}
            before=Image.new("RGB",(1080,1920),BACKGROUND)
            after=before.copy()
            self.assertEqual(draw_story_frame(before,shot,3.0),"human")
            self.assertEqual(draw_story_frame(after,shot,10.4),"human")
            self.assertIsNotNone(ImageChops.difference(
                before.crop((170,650,980,1265)),
                after.crop((170,650,980,1265))).getbbox())
            for frame in (before,after):
                for safe in ((0,0,1080,480),(0,1400,1080,1920)):
                    self.assertIsNone(ImageChops.difference(
                        frame.crop(safe),Image.new("RGB",frame.crop(safe).size,BACKGROUND)
                    ).getbbox())

    def test_invalid_prop_coordinates_fail_closed(self):
        for invalid in (None,(1,),("bad",3),(float("nan"),3),
                        (2,float("inf")),(1,2,3)):
            with self.subTest(invalid=invalid),self.assertRaises(CreativeReject):
                carried_radio_center(invalid)
        for p in (-.1,1.3,float("nan"),float("inf")):
            with self.subTest(p=p),self.assertRaises(CreativeReject):
                key_half_positions(p,(100,100),(200,200))
        with self.assertRaises(CreativeReject):
            draw_radio_in_hand(ImageDraw.Draw(Image.new("RGB",(1080,1920))),
                               (300,300),float("nan"),_radio)


if __name__=="__main__":
    unittest.main()
