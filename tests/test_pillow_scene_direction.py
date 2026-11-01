"""Regression gates against repeating identical backdrops or static story props."""
import unittest
from PIL import Image, ImageChops

from astra_v2.pillow_duo_scene import draw_duo
from astra_v2.pillow_scene_direction import (
    actor_translation, draw_story_stage, prop_trajectory, story_setting
)

class DirectedPillowScenesTests(unittest.TestCase):
    def test_different_locations_are_not_one_stock_background(self):
        locations = [
            ("The fox and cat play a game on a hillside.", "hill"),
            ("The fox and cat reach the village fountain.", "village"),
            ("The fox and cat carry a ball to a flat meadow.", "meadow"),
            ("The cat and dog search the old library.", "library"),
            ("The otter and squirrel follow a boat on the river.", "river"),
            ("The dog and otter reached the fishing harbor.", "harbor"),
            ("The rabbit and dog found a flower in the garden.", "garden"),
        ]
        from PIL import ImageDraw
        sigs = []
        for speech, label in locations:
            shot = {"speech": speech}
            self.assertEqual(story_setting(shot), label)
            im = Image.new("RGB", (1080,1920),(24,35,60))
            result=draw_story_stage(ImageDraw.Draw(im),shot,.5)
            self.assertEqual(result,label)
            # Background landscape should materially change, not just props.
            sigs.append(im.crop((60,570,1015,1180)).tobytes())
            for rect in ((0,0,1080,480),(0,1400,1080,1920)):
                self.assertIsNone(ImageChops.difference(
                    im.crop(rect),
                    Image.new("RGB",(rect[2]-rect[0],rect[3]-rect[1]),(24,35,60))).getbbox())
        self.assertEqual(len(set(sigs)),len(sigs))

    def test_authored_location_is_not_replaced_by_handheld_props(self):
        self.assertEqual(story_setting({
            "speech":"The fox carried a book and a flower through the village.",
            "story_environment":"village"}),"village")
        self.assertEqual(story_setting({
            "speech":"They read a letter near the river bank.",
            "story_environment":"river"}),"river")
        self.assertEqual(story_setting({
            "speech":"They held a flower at the hillside crossing."}),"hill")
        self.assertEqual(story_setting({
            "speech":"They carried a book into the village square."}),"village")
        self.assertEqual(story_setting({
            "speech":"The friends opened a book at the library."}),"library")

    def test_broken_river_bridge_has_visible_missing_plank(self):
        from PIL import ImageDraw
        broken = {"speech": "The fox ran toward the river bridge, but the rabbit spotted a broken plank and waved a warning."}
        intact = {"speech": "The fox and rabbit walked beside the river bridge."}
        images = []
        for shot in (broken, intact):
            im = Image.new("RGB", (1080, 1920), (24, 35, 60))
            self.assertEqual(draw_story_stage(ImageDraw.Draw(im), shot, 0.5), "river")
            images.append(im)
        damaged, baseline = images
        self.assertEqual(damaged.getpixel((350, 1160)), (174, 125, 83))
        self.assertNotEqual(damaged.getpixel((550, 1160)), (174, 125, 83))
        self.assertNotEqual(baseline.getpixel((350, 1160)), (174, 125, 83))
        for rect in ((0, 0, 1080, 480), (0, 1400, 1080, 1920)):
            self.assertIsNone(ImageChops.difference(
                damaged.crop(rect), baseline.crop(rect)).getbbox())

    def test_ball_rolls_and_the_catch_overrides_earlier_roll_verb(self):
        first={"speech":"The fox and cat watched the ball roll away.",
               "story_beat":"reveal","story_action":"idle"}
        catch={"speech":"The cat picked up the ball before it rolled away.",
               "story_beat":"twist","story_action":"pick"}
        close={"speech":"The fox and cat carried the rescued ball.",
               "story_beat":"payoff","story_action":"carry"}
        x0,y0=prop_trajectory(first,0.0)
        x1,y1=prop_trajectory(first,1.6)
        self.assertGreater(x1-x0,180)
        self.assertNotEqual((x0,y0),(x1,y1))
        self.assertLess(prop_trajectory(catch,1.3)[1],prop_trajectory(catch,0.0)[1])
        self.assertEqual(prop_trajectory(close,0.0),prop_trajectory(close,2.0))

    def test_running_actor_translates_independently(self):
        self.assertEqual(actor_translation("idle",2,0),0)
        self.assertGreater(actor_translation("run",1.8,0),45)
        self.assertGreater(actor_translation("run",1.8,0),
                           actor_translation("run",1.8,1))
        self.assertEqual(actor_translation("run",1.8,0),
                         actor_translation("run",1.8,0))

    def test_story_frames_vary_with_narrated_setting_and_prop_motion(self):
        base={"story_cast":("fox","cat"),"story_subject":"fox",
              "story_action":"run","story_beat":"build"}
        first=dict(base,speech="The fox and cat chase a rolling ball down the rocky hillside.")
        second=dict(base,speech="The fox and cat chase a rolling ball beside the village fountain.")
        a=Image.new("RGB",(1080,1920),(24,35,60))
        b=a.copy()
        c=a.copy()
        self.assertTrue(draw_duo(a,first,.1))
        self.assertTrue(draw_duo(b,first,1.4))
        self.assertTrue(draw_duo(c,second,1.4))
        self.assertIsNotNone(ImageChops.difference(a,b).getbbox())
        self.assertIsNotNone(ImageChops.difference(b,c).getbbox())
        for im in (a,b,c):
            self.assertIsNone(ImageChops.difference(
                im.crop((0,0,1080,480)),
                Image.new("RGB",(1080,480),(24,35,60))).getbbox())
            self.assertIsNone(ImageChops.difference(
                im.crop((0,1400,1080,1920)),
                Image.new("RGB",(1080,520),(24,35,60))).getbbox())

if __name__=="__main__":
    unittest.main()
