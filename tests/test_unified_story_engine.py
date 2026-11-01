"""Single Studio story renderer: cast coverage, continuity and no fallbacks."""
import os
import unittest
from unittest.mock import Mock, patch

from PIL import Image, ImageChops
from astra_errors import CreativeReject
from astra_v2.unified_story_engine import (
    cast_from_title, validate_story_shot, draw_story_frame,
)


class UnifiedEngineTests(unittest.TestCase):
    def test_directed_nonanimal_story_is_first_class(self):
        shot = {"speech": "The city lost its gravity.", "visual": "city",
                "label": "THE CITY", "sub": "A mystery"}
        self.assertEqual(validate_story_shot(shot), "directed")
        draw = Mock()
        result = draw_story_frame(object(), shot, .25, draw_directed=draw,
                                  global_time=7.5, accent=(100, 150, 200))
        self.assertEqual(result, "directed")
        self.assertEqual(draw.call_count, 1)
        self.assertEqual(draw.call_args.args[2:], (7.5, .25, (100, 150, 200)))

    def test_directed_renderer_is_required_not_a_fallback(self):
        with self.assertRaises(CreativeReject):
            draw_story_frame(object(), {"speech": "A distant star glows."}, .2)

    def test_named_solo(self):
        shot = {"speech": "The owl repaired the clock.", "story_cast": ("owl",)}
        self.assertEqual(validate_story_shot(shot), "solo")
        with patch("astra_v2.unified_story_engine._draw_solo", return_value=True):
            self.assertEqual(draw_story_frame(object(), shot, .2), "solo")

    def test_badger_is_not_replaced_by_single_squirrel(self):
        # The 2026-11-01 published candidate narrated Bramble the badger
        # alongside Pip the squirrel, but sampled frames showed only one
        # squirrel-like puppet. The unsupported actor must fail before upload.
        for field in ("story_title", "visual_prompt", "speech"):
            shot = {"story_cast": ("squirrel",),
                    "speech": "We must cross the ravine.",
                    field: "Bramble the badger and Pip the squirrel"}
            with self.subTest(field=field):
                with self.assertRaisesRegex(CreativeReject, "unsupported badger actor"):
                    validate_story_shot(shot)

    def test_supported_squirrel_still_renders_without_badger(self):
        shot = {"story_title": "Pip the Squirrel",
                "visual_prompt": "Pip the squirrel watches the moon.",
                "story_cast": ("squirrel",)}
        self.assertEqual(validate_story_shot(shot), "solo")

    def test_duo_cast_stable(self):
        shot = {"speech": "The fox helped the rabbit carry a lantern.",
                "story_cast": ("fox", "rabbit")}
        self.assertEqual(validate_story_shot(shot), "duo")

    def test_three_through_eight_character_cast(self):
        cast = ("fox", "rabbit", "owl", "otter", "squirrel",
                "mouse", "dog", "cat")
        for count in range(3, 9):
            shot = {"speech": "The friends assembled.",
                    "story_cast": cast[:count]}
            with self.subTest(count=count):
                self.assertEqual(validate_story_shot(shot), "ensemble")

    def test_story_title_has_stable_character_order(self):
        self.assertEqual(cast_from_title("The Rabbit and Fox's Lantern"),
                         ("rabbit", "fox"))
        self.assertEqual(cast_from_title("A City Without Gravity"), ())

    def test_omitted_third_character_is_not_hidden(self):
        shot = {"speech": "The owl rescued the fox and rabbit.",
                "story_cast": ("fox", "rabbit")}
        with self.assertRaises(CreativeReject):
            validate_story_shot(shot)

    def test_invalid_explicit_cast_is_never_replaced(self):
        for cast in (("fox", "rabbit", "unknown"),
                     ("fox", "fox"), ("fox",) * 9, "fox"):
            with self.subTest(cast=cast):
                with self.assertRaises(CreativeReject):
                    validate_story_shot({"speech": "They walked.",
                                         "story_cast": cast})

    def test_duo_render_failure_is_fatal(self):
        shot = {"speech": "The fox and rabbit ran.",
                "story_cast": ("fox", "rabbit")}
        with patch("astra_v2.unified_story_engine.draw_duo", return_value=False):
            with self.assertRaises(CreativeReject):
                draw_story_frame(object(), shot, .2)

    def test_ensemble_render_failure_is_fatal(self):
        shot = {"speech": "The fox rabbit and owl ran.",
                "story_cast": ("fox", "rabbit", "owl")}
        with patch("astra_v2.unified_story_engine.ensemble_frame", return_value=False) as render:
            with self.assertRaises(CreativeReject):
                draw_story_frame(object(), shot, .2)
            self.assertTrue(render.call_args.args[1]["experimental_ensemble"])

    def test_optimized_pillow_motion_is_now_shared(self):
        from astra_v2 import story_motion
        from experimental import motion_profiles
        self.assertIs(story_motion.evaluate, motion_profiles.evaluate)
        self.assertEqual(story_motion.evaluate(1.25),
                         story_motion.evaluate(1.25))
        self.assertGreater(story_motion.evaluate(2.3).walk, .95)

    def test_true_pillow_frames_are_rendered(self):
        for names in (("owl",), ("fox", "rabbit"),
                      ("fox", "rabbit", "owl")):
            with self.subTest(cast=names):
                shot = {"story_cast": names,
                        "speech": "The friends looked for the lantern.",
                        "story_visual_seed": "qa-unified",
                        "story_beat": "reveal", "story_action": "look"}
                canvas = Image.new("RGB", (1080, 1920))
                before = canvas.copy()
                self.assertIn(draw_story_frame(canvas, shot, .4),
                              ("solo", "duo", "ensemble"))
                self.assertIsNotNone(ImageChops.difference(canvas, before).getbbox())

    def test_newly_introduced_characters_persist_without_cast_reset(self):
        from astra_v2.story_forge import catalog
        from studio_renderer import make_plan
        stories = catalog(limit=256)
        for title, lead in (("The Owl and the Last Library Light", "owl"),
                            ("The Cat Who Ran a Bakery", "cat")):
            story = next(s for s in stories if s["title"] == title)
            with self.subTest(title=title):
                with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}):
                    plan = make_plan(dict(story))
                casts = [tuple(shot.get("story_cast") or ()) for shot in plan]
                self.assertTrue(all(lead in cast for cast in casts))
                self.assertTrue(any(len(cast) > 1 for cast in casts))
                self.assertTrue(all(set(a).issubset(b)
                                    for a, b in zip(casts, casts[1:])))

    def test_real_studio_plan_keeps_duo_cast(self):
        from astra_v2.story_forge import catalog
        from studio_renderer import make_plan
        source = next(s for s in catalog(limit=256)
                      if s["title"] == "The Fox and Rabbit's Last Lantern")
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}):
            plan = make_plan(source)
        self.assertEqual(len(plan), 4)
        self.assertTrue(all(shot.get("story_cast") == ("fox", "rabbit")
                            for shot in plan))


if __name__ == "__main__":
    unittest.main()
