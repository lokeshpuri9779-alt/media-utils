"""Regression checks for distinct ASTRA story protagonists.

Run: python -m unittest tests.test_astra_character_art
"""
import unittest
from PIL import Image, ImageChops
from astra_v2.story_visuals import draw_subject, select_subject

CHARACTERS = ("fox", "owl", "duck", "squirrel", "mouse", "otter", "crab", "firefly")

class CharacterArtworkTests(unittest.TestCase):
    def test_title_character_wins_over_tree_prop(self):
        for character in CHARACTERS:
            with self.subTest(character=character):
                story = {"title": f"The {character} and the forest"}
                shot = {"speech": "A tree rustled in the wind", "visual_prompt": "tree"}
                self.assertEqual(select_subject(story, shot), character)

    def test_title_character_survives_scenery_only_visual(self):
        for character in CHARACTERS:
            with self.subTest(character=character):
                story = {"title": f"The {character} and the broken bridge"}
                for visual in ("forest", "tree", "woods", "landscape"):
                    shot = {"speech": "A strange sound echoed nearby", "visual": visual}
                    self.assertEqual(select_subject(story, shot), character)
        story = {"title": "The fox and the broken bridge"}
        self.assertEqual(select_subject(story, {"speech": "The owl arrived", "visual": "forest"}), "owl")

    def test_characters_have_distinct_visible_art(self):
        images = {}
        for character in CHARACTERS:
            with self.subTest(character=character):
                im = Image.new("RGB", (1080, 1920), (13, 17, 29))
                self.assertTrue(draw_subject(im, character, 0.7, (100, 180, 210)))
                self.assertIsNotNone(ImageChops.difference(im, Image.new("RGB", im.size, (13,17,29))).getbbox())
                images[character] = im.crop((180, 500, 870, 1260)).tobytes()
        self.assertEqual(len(set(images.values())), len(CHARACTERS))

    def test_animation_changes_frames(self):
        for character in CHARACTERS:
            with self.subTest(character=character):
                a = Image.new("RGB", (1080,1920), (13,17,29))
                b = Image.new("RGB", (1080,1920), (13,17,29))
                draw_subject(a, character, 0, (100,180,210))
                draw_subject(b, character, 1.1, (100,180,210))
                self.assertIsNotNone(ImageChops.difference(a,b).getbbox())

if __name__ == "__main__":
    unittest.main()
