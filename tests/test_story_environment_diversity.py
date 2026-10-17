"""Regression tests for story-matched backgrounds and deterministic artwork."""
import unittest
from PIL import Image, ImageDraw
from astra_v2.pillow_scene_direction import story_setting, draw_story_stage

class EnvironmentDiversityTests(unittest.TestCase):
    def test_story_locations(self):
        cases = {"mangrove":"mangrove", "observatory":"observatory",
                 "railway":"railway", "museum":"museum",
                 "workshop":"workshop", "cavern":"cavern", "desert":"desert"}
        for phrase, expected in cases.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(story_setting({"speech":"At the "+phrase}), expected)

    def test_no_implicit_forest(self):
        self.assertEqual(story_setting({"speech":"The tapir found a bell"}),"meadow")

    def test_different_settings_render_distinct_frames(self):
        hashes = []
        for setting in ("mangrove","observatory","railway","museum",
                        "workshop","cavern","desert"):
            image = Image.new("RGB",(1080,1920),(27,36,57))
            draw_story_stage(ImageDraw.Draw(image),
                             {"story_environment":setting,"story_visual_seed":"fixed"},0)
            hashes.append(hash(image.tobytes()))
        self.assertEqual(len(set(hashes)),len(hashes))

    def test_stage_stable_for_same_seed_and_time(self):
        shot={"story_environment":"railway","story_visual_seed":"stable"}
        images=[]
        for _ in range(2):
            im=Image.new("RGB",(1080,1920),(27,36,57))
            draw_story_stage(ImageDraw.Draw(im),shot,0.5)
            images.append(im.tobytes())
        self.assertEqual(images[0],images[1])
