"""Narrative staging QA for the existing CPU-only Studio Pillow compositor."""
import unittest
from PIL import Image, ImageChops
from astra_v2.pillow_duo_scene import (
    draw_duo, scene_setting, scene_mood, story_prop_position, scene_pair
)

class PillowStoryDirectionTests(unittest.TestCase):
    def test_story_settings_use_story_location(self):
        cases = {
            "The Fox and Cat's Runaway Ball": ("A game began on a hillside.", "hillside"),
            "The Cat, the Dog, and the Missing Chapter": ("A library lost a page.", "library"),
            "The Dog and Otter's Harbor Lantern": ("The harbor flooded.", "harbor"),
            "The Rabbit and Dog's First Flower": ("The garden opened.", "garden"),
            "The Otter and Squirrel's Floating Gift": ("A box drifted downriver.", "river"),
            "The Rabbit and Squirrel's Festival Ball": ("A parade crossed town.", "village"),
        }
        for title, (speech, setting) in cases.items():
            with self.subTest(title=title):
                self.assertEqual(scene_setting({"story_title": title, "speech": speech}), setting)

    def test_ball_moves_through_problem_chase_catch_and_finish(self):
        beats = ("reveal", "build", "twist", "payoff")
        at_start = [
            story_prop_position({"speech": "The fox and cat found a ball.",
                                 "story_action": "run", "story_beat": beat}, 0)
            for beat in beats
        ]
        at_end = [
            story_prop_position({"speech": "The fox and cat found a ball.",
                                 "story_action": "run", "story_beat": beat}, 3.0)
            for beat in beats
        ]
        self.assertLess(at_start[0][0], at_end[0][0])
        self.assertGreater(at_start[1][0], at_end[1][0])
        self.assertLess(at_start[2][1], at_start[2][1] + 1)
        self.assertGreater(at_start[2][1], at_end[2][1])
        self.assertEqual(at_start[3], at_end[3])

    def test_scene_changes_composition_but_keeps_named_cast(self):
        first = {"speech": "The fox and cat chase the ball down a hillside.",
                 "story_title": "The Fox and Cat's Runaway Ball",
                 "story_setting": "hillside", "story_cast": ("fox", "cat"),
                 "story_action": "run", "story_beat": "reveal"}
        last = dict(first, story_action="carry", story_beat="payoff")
        a = Image.new("RGB", (1080, 1920), (24, 35, 60))
        b = a.copy()
        self.assertTrue(draw_duo(a, first, 1.0))
        self.assertTrue(draw_duo(b, last, 1.0))
        self.assertEqual(scene_pair(first), scene_pair(last))
        self.assertIsNotNone(ImageChops.difference(a, b).getbbox())
        self.assertNotEqual(a.getpixel((260, 900)), b.getpixel((260, 900)))
        for image in (a, b):
            self.assertEqual(image.getpixel((20, 140)), (24, 35, 60))
            self.assertEqual(image.getpixel((20, 1580)), (24, 35, 60))

    def test_emotions_progress_in_story(self):
        descriptions = ["The fox and cat discovered a ball.",
                        "The ball escaped as they ran.",
                        "The cat caught the ball.",
                        "They celebrated the rescued ball."]
        beats = ("reveal", "build", "twist", "payoff")
        emotions = [scene_mood({"speech": text, "story_beat": role})
                    for text, role in zip(descriptions, beats)]
        self.assertGreaterEqual(len(set(emotions)), 3)

    def test_curated_story_contract_is_present_in_studio_plan(self):
        from astra_v2.story_forge import catalog
        from studio_renderer import make_plan
        story = next(s for s in catalog(limit=256)
                     if s["title"] == "The Fox and Cat's Runaway Ball")
        self.assertEqual(story["visual_contract"], "pillow_duo_v2")
        plan = make_plan(story)
        self.assertEqual(len(plan), 4)
        self.assertEqual(len({s["story_setting"] for s in plan}), 1)
        self.assertEqual(len({s["story_title"] for s in plan}), 1)
        self.assertTrue(all(scene_pair(s) == ("fox", "cat") for s in plan))

if __name__ == "__main__":
    unittest.main()
