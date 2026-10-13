"""Regression checks for ASTRA's character-led story illustrations."""
import unittest
from PIL import Image
from astra_v2.story_visuals import draw_subject, select_subject

CHARACTERS = ("fox", "owl", "duck", "squirrel", "mouse", "otter", "crab", "firefly")

class CharacterVisualTests(unittest.TestCase):
    def test_title_protagonist_beats_incidental_tree(self):
        for name in CHARACTERS:
            with self.subTest(name=name):
                story = {"title": f"The {name} and the forest"}
                shot = {"speech": "The tree moved in the moonlight.", "visual_prompt": "tree in a forest"}
                self.assertEqual(select_subject(story, shot), name)

    def test_characters_draw_distinct_frames(self):
        signatures = set()
        for name in CHARACTERS:
            with self.subTest(name=name):
                im = Image.new("RGB", (1080, 1920), (12, 14, 29))
                self.assertTrue(draw_subject(im, name, 0.75, (245, 170, 90)))
                signature = im.crop((250, 520, 880, 1230)).tobytes()
                self.assertNotIn(signature, signatures, f"{name} duplicated another character")
                signatures.add(signature)

    def test_character_frames_animate(self):
        for name in CHARACTERS:
            with self.subTest(name=name):
                frames = []
                for t in (0.0, 1.0):
                    im = Image.new("RGB", (1080, 1920), (12, 14, 29))
                    self.assertTrue(draw_subject(im, name, t, (245, 170, 90)))
                    frames.append(im.crop((250, 520, 880, 1230)).tobytes())
                self.assertNotEqual(*frames)

if __name__ == "__main__":
    unittest.main()
