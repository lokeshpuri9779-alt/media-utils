"""Isolated narrated ensemble Studio-rate safety and creative path regressions."""
import unittest
from astra_v2.ensemble_story_experiments import catalog
from astra_v2.publication_quality import publication_rejection
from studio_renderer import FPS as STUDIO_FPS
from tools.astra_ensemble_voiced_preview import FPS,pilot_plan


class EnsembleNarrated30FpsTests(unittest.TestCase):
    def test_exact_production_studio_frame_rate(self):
        self.assertEqual(FPS,STUDIO_FPS)
        self.assertEqual(FPS,30)

    def test_preserve_full_cast_and_two_subshots_in_every_pilot(self):
        for story in catalog():
            with self.subTest(title=story["title"]):
                plan=pilot_plan(story)
                self.assertEqual(len(plan),len(story["story_beats"]))
                self.assertEqual(len(plan),len([s for s in plan if s["experimental_subshots"]]))
                self.assertEqual(
                    {tuple(s["story_cast"]) for s in plan},
                    {tuple(story["story_cast"])},
                )
                self.assertEqual(publication_rejection(story),"not_production_ready")

    def test_refuses_approved_or_nonexperimental_catalog(self):
        for change in ({"production_ready":True},
                       {"experimental_ensemble":False},
                       {"story_cast":("fox","owl")}):
            with self.subTest(change=change):
                story=dict(catalog()[0],**change)
                with self.assertRaisesRegex(RuntimeError,"rejected"):
                    pilot_plan(story)

    def test_world_scene_style_survives_second_camera_take(self):
        from astra_v2.ensemble_scene import grounded_positions,directed_subshot
        story=catalog()[0]
        shot=pilot_plan(story)[0]
        shot["duration"]=2.4
        self.assertEqual(directed_subshot(shot,.4)[1],0)
        self.assertEqual(directed_subshot(shot,1.4)[1],1)
        cast=shot["story_cast"]
        roles=shot["acting_notes"]
        focus=cast[0]
        for t in (.4,1.4):
            spots=grounded_positions(cast,shot["scene_style"],t,roles,focus)
            self.assertEqual({j for j,x,y,w in spots},set(range(len(cast))))


if __name__=="__main__":
    unittest.main()
