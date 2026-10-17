"""Performance + visual-identity invariants for Studio's Pillow hot path."""
import math
import unittest
import numpy as np
from PIL import Image, ImageChops, ImageDraw

from astra_v2.pillow_duo_scene import (
    scene_pair, scene_mood, scene_prop, draw_duo,
    _cached_actor_mentions, _cached_mood, _cached_prop)
from astra_v2.pillow_scene_direction import (
    story_setting, prop_trajectory, _cached_scene_setting,
    _cached_stage_seed, _cached_prop_verb)
from astra_v2.procedural_visual_library import (
    visual_identity, icon_for_story, _cached_visual_identity, _cached_icon_selection)
from studio_renderer import font, starfield, _starfield_points

class StudioRuntimeOptimizationTests(unittest.TestCase):
    def setUp(self):
        for fn in (_cached_actor_mentions, _cached_mood, _cached_prop,
                   _cached_scene_setting, _cached_stage_seed,
                   _cached_prop_verb, _cached_visual_identity,
                   _cached_icon_selection, _starfield_points):
            fn.cache_clear()

    def test_cast_and_prop_cache_used_for_each_frame(self):
        shot={"speech":"The fox and rabbit carry a gift box across the river.",
              "story_cast":("fox","rabbit"),"story_action":"carry",
              "story_visual_seed":"fixed-episode"}
        frames=[]
        for t in (0.2,0.55):
            im=Image.new("RGB",(1080,1920),(20,25,40))
            self.assertTrue(draw_duo(im,shot,t))
            frames.append(im)
        self.assertGreater(_cached_actor_mentions.cache_info().hits,0)
        self.assertGreater(_cached_prop.cache_info().hits,0)
        self.assertGreater(_cached_mood.cache_info().hits,0)
        self.assertGreater(_cached_visual_identity.cache_info().hits,0)
        self.assertGreater(_cached_icon_selection.cache_info().hits,0)
        self.assertGreater(_cached_scene_setting.cache_info().hits,0)
        self.assertGreater(_cached_stage_seed.cache_info().hits,0)
        self.assertIsNotNone(ImageChops.difference(*frames).getbbox())

    def test_cache_is_keyed_by_current_narration_not_stale_shot(self):
        s={"speech":"The fox and rabbit found a gift box.","story_cast":("fox","rabbit")}
        self.assertEqual(scene_pair(s),("fox","rabbit"))
        self.assertEqual(scene_prop(s),"box")
        s["speech"]="The fox and owl found a book."
        self.assertEqual(scene_pair(s),())
        self.assertEqual(scene_prop(s),"book")
        self.assertEqual(scene_mood({"speech":"Oh no!"}),"surprised")
        self.assertEqual(scene_mood({"speech":"The fox waved happily."}),"happy")

    def test_story_direction_follows_explicit_narration(self):
        self.assertEqual(story_setting({"speech":"The fox is in a library.",
                                         "story_environment":"harbor"}),"library")
        self.assertEqual(story_setting({"speech":"The fox looked up.",
                                         "story_environment":"harbor"}),"harbor")
        self.assertEqual(story_setting({"speech":"The fox looked up."}),"meadow")
        rolling={"speech":"The ball rolled across the river.","story_action":"idle"}
        a=prop_trajectory(rolling,.2)
        b=prop_trajectory(rolling,1.6)
        self.assertNotEqual(a,b)
        self.assertGreater(_cached_prop_verb.cache_info().hits,0)

    def test_cached_star_positions_identical_to_original_seed(self):
        rng=np.random.default_rng(17)
        expected=tuple(zip(rng.integers(45,1035,65),rng.integers(475,1330,65),
                           rng.integers(1,4,65),rng.random(65)))
        self.assertEqual(_starfield_points(),expected)
        d=ImageDraw.Draw(Image.new("RGB",(1080,1920)))
        starfield(d,.45,(188,163,255))
        starfield(d,.75,(188,163,255))
        self.assertGreater(_starfield_points.cache_info().hits,0)

    def test_cached_fonts_and_identity_stable(self):
        font.cache_clear()
        one=font(38)
        self.assertIs(one,font(38))
        self.assertGreater(font.cache_info().hits,0)
        self.assertEqual(visual_identity("episode","fox"),visual_identity("episode","fox"))
        self.assertEqual(icon_for_story("book","episode"),icon_for_story("book","episode"))
        self.assertLessEqual(_cached_visual_identity.cache_info().maxsize,4096)

if __name__=="__main__":
    unittest.main()
