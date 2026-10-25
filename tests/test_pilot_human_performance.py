"""End-to-end character contract and frame-level acting regressions.

These tests cover the exact authored Mara pilot. They deliberately do not
claim semantic fidelity for other human stories or replace manual review.
"""
import unittest
from PIL import Image, ImageChops
from astra_errors import CreativeReject
from astra_v2.omniroute_local import catalog
from astra_v2.human_story_performance import ACTIONS, draw_human_scene
from astra_v2.unified_story_engine import validate_story_shot, draw_story_frame


def pilot_shots():
    story = next(s for s in catalog() if s["content_id"] == "rayvan-season-01-episode-01")
    return [{**beat, "story_visual_seed": story["content_id"], "story_title": story["title"]}
            for beat in story["story_beats"]]


def acted_frame(shot, at):
    frame=Image.new("RGB",(1080,1920),(10,20,33))
    result=draw_story_frame(frame,shot,at)
    assert result=="human"
    return frame


class PilotHumanPerformanceTests(unittest.TestCase):
    def test_four_authored_actions_route_to_acted_human_grammar(self):
        shots=pilot_shots()
        self.assertEqual([s["story_human_action"] for s in shots], list(ACTIONS))
        for scene in shots:
            self.assertEqual(validate_story_shot(scene),"human")

    def test_every_actually_rendered_shot_moves_its_actor_and_props(self):
        for index, shot in enumerate(pilot_shots(),1):
            a,b=acted_frame(shot,.32),acted_frame(shot,1.45)
            actor_crop=(150,580,980,1250)
            delta=ImageChops.difference(a.crop(actor_crop),b.crop(actor_crop))
            self.assertIsNotNone(delta.getbbox(),f"Scene {index} is static")

    def test_character_is_visibly_drawn_and_stays_inside_safe_stage(self):
        base=Image.new("RGB",(1080,1920),(10,20,33))
        for index,shot in enumerate(pilot_shots(),1):
            output=base.copy()
            self.assertTrue(draw_human_scene(output,shot,.5))
            self.assertIsNotNone(ImageChops.difference(base,output).getbbox(),
                                 f"Scene {index} has no actor")
            self.assertIsNone(ImageChops.difference(
                base.crop((0,0,1080,480)),
                output.crop((0,0,1080,480))).getbbox(),
                "Actor changed headline-safe area")
            self.assertIsNone(ImageChops.difference(
                base.crop((0,1400,1080,1920)),
                output.crop((0,1400,1080,1920))).getbbox(),
                "Actor changed caption-safe area")

    def test_malformed_or_unapproved_humans_fail_without_icon_fallback(self):
        first=pilot_shots()[0]
        for change in (
            {"story_visual_seed":"other-story"},
            {"story_human_actor":"other-person"},
            {"story_human_action":"teleport"},
            {"story_cast":["fox"]},
            {"visual":"door"},
            {"speech":"A sound occurred, with no relevant prop."},
        ):
            with self.subTest(change=change), self.assertRaises(CreativeReject):
                validate_story_shot({**first,**change})
        with self.assertRaises(CreativeReject):
            draw_human_scene(Image.new("RGB",(540,960)),first,.5)


if __name__=="__main__":
    unittest.main()
