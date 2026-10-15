"""Guard against changing procedural stage geometry on each narration beat."""
import unittest
from PIL import Image, ImageChops, ImageDraw
from astra_v2.pillow_scene_direction import _text_seed, draw_story_stage

class StoryStageContinuityTests(unittest.TestCase):
    def test_story_seed_survives_headline_and_narration_changes(self):
        first={"story_visual_seed":"episode-42","speech":"A fox found a clue",
               "headline":"THE CLUE","story_environment":"forest"}
        next_={"story_visual_seed":"episode-42","speech":"The rabbit asked for help",
               "headline":"THE WARNING","story_environment":"forest"}
        self.assertEqual(_text_seed(first),_text_seed(next_))
        self.assertNotEqual(_text_seed(first),_text_seed({**next_,"story_visual_seed":"episode-43"}))
        a=Image.new("RGB",(1080,1920),(15,21,37))
        b=a.copy()
        draw_story_stage(ImageDraw.Draw(a),first,0.7)
        draw_story_stage(ImageDraw.Draw(b),next_,0.7)
        self.assertIsNone(ImageChops.difference(a,b).getbbox())
    def test_stage_stays_within_caption_and_headline_safe_areas(self):
        for setting in ("forest","garden","village","library","harbor","winter"):
            im=Image.new("RGB",(1080,1920),(15,21,37))
            draw_story_stage(ImageDraw.Draw(im),{
                "story_visual_seed":"story-123","story_environment":setting,
                "speech":"The characters investigate."},0.6)
            self.assertEqual(im.getpixel((30,1800)),(15,21,37))
            self.assertEqual(im.getpixel((30,200)),(15,21,37))
    def test_no_bright_gold_swoosh_in_scenery(self):
        im=Image.new("RGB",(1080,1920),(15,21,37))
        draw_story_stage(ImageDraw.Draw(im),{
            "story_visual_seed":"story-123","story_environment":"forest",
            "speech":"The fox and rabbit walk."},1.1)
        # Bright yellow scene-spanning guide arc seen in user screenshots.
        # Scenery may contain small warm accents, but no long horizontal run.
        pixels=im.load()
        for y in range(580,1000,18):
            n=sum(1 for x in range(80,1000,4)
                  if pixels[x,y][0]>195 and pixels[x,y][1]>145
                  and pixels[x,y][2]<135)
            self.assertLess(n,95,(y,n))
if __name__=="__main__":
    unittest.main()
