"""Shot-directed camera and moving reach, grounded in all 16 season scenes."""
import math
import unittest

from PIL import Image, ImageChops

from astra_errors import CreativeReject
from astra_v2.human_cinematic_camera import FOCUS, camera_box, apply_human_camera
from astra_v2.human_story_performance import draw_human_scene
from astra_v2.omniroute_local import catalog


def season_shots():
    for story in catalog(max_candidates=30):
        for beat in story["story_beats"]:
            yield {**beat, "story_visual_seed":story["content_id"],
                   "story_title":story["title"], "duration":12.0}


class HumanCinematicStagingTests(unittest.TestCase):
    def test_all_sixteen_authored_actions_have_stable_camera_profiles(self):
        shots=list(season_shots())
        self.assertEqual(len(shots),16)
        self.assertEqual(set(FOCUS),{s["story_human_action"] for s in shots})
        for shot in shots:
            action=shot["story_human_action"]
            first=camera_box(action,0.0,12.0)
            last=camera_box(action,12.0,12.0)
            for region in (first,last):
                left,top,right,bottom=region
                self.assertTrue(0<=left<right<=1080)
                self.assertTrue(0<=top<bottom<=1920)
                self.assertAlmostEqual((right-left)/(bottom-top),1080/1920,delta=.0015)
            self.assertLess(last[2]-last[0],first[2]-first[0])
            self.assertEqual(camera_box(action,5.0,12.0),camera_box(action,5.0,12.0))
            prev=camera_box(action,5.0,12.0)
            following=camera_box(action,5.0+1/30,12.0)
            self.assertLessEqual(max(abs(a-b) for a,b in zip(prev,following)),2,
                                 "Camera would visibly jump between frames")

    def test_cropped_stage_is_deterministic_and_contains_real_acting(self):
        shot=next(season_shots())
        still=Image.new("RGB",(1080,1920),(10,20,33))
        draw_human_scene(still,shot,1.0)
        image=apply_human_camera(still,shot,2.4)
        repeated=apply_human_camera(still,shot,2.4)
        self.assertEqual(image.size,still.size)
        self.assertEqual(image.tobytes(),repeated.tobytes())
        self.assertIsNotNone(ImageChops.difference(still,image).getbbox(),
                             "Cinematic camera did not change framing")
        self.assertEqual(still.getpixel((0,0)),(10,20,33),
                         "Source frame mutated by camera")

    def test_headline_and_caption_drawing_can_remain_outside_camera_transform(self):
        shot=next(season_shots())
        blank=Image.new("RGB",(1080,1920),(10,20,33))
        draw_human_scene(blank,shot,.5)
        cropped=apply_human_camera(blank,shot,.5)
        for area in ((0,0,1080,420),(0,1450,1080,1920)):
            reference=Image.new("RGB",blank.crop(area).size,(10,20,33))
            self.assertIsNone(ImageChops.difference(cropped.crop(area),reference).getbbox(),
                              "Scene artwork overlaps a reserved typography region")

    def test_unknown_or_mismatched_actor_fails_before_any_camera(self):
        original=next(season_shots())
        frame=Image.new("RGB",(1080,1920),(10,20,33))
        for override in (
            {"story_human_actor":"unknown"},
            {"story_visual_seed":"unreviewed-series"},
            {"story_human_action":"unsupported_action"},
        ):
            with self.subTest(override=override),self.assertRaises(CreativeReject):
                apply_human_camera(frame,{**original,**override},.3)
        for args in (("discover_radio",-1,12),("discover_radio",float("nan"),12),
                     ("discover_radio",.2,0),("missing",.2,12)):
            with self.assertRaises((ValueError,CreativeReject)):
                camera_box(*args)

    def test_actor_reaching_motion_not_just_blinking(self):
        shot=next(season_shots())
        a=Image.new("RGB",(1080,1920),(10,20,33))
        b=a.copy()
        draw_human_scene(a,shot,0.0)
        draw_human_scene(b,shot,1.15)
        # Radio interaction drives a substantial hand/arm pose change.
        hand_region=(470,765,655,1080)
        diff=ImageChops.difference(a.crop(hand_region),b.crop(hand_region))
        self.assertIsNotNone(diff.getbbox())


if __name__=="__main__":
    unittest.main()
