"""Real-scene pixel cues and negative controls; no model or internet calls."""
from __future__ import annotations

from PIL import Image, ImageDraw
import unittest

from tools import astra_offline_procedural_preview as render
from tools import astra_offline_visual_cues as cues


class VisualCueTests(unittest.TestCase):
    def test_every_original_reference_has_completed_payoff_cues(self):
        self.assertEqual(set(render.KINDS), set(cues.CUES))
        for case in render.KINDS:
            with self.subTest(case=case):
                first = render.render_frame(case, 0, 0.0)
                payoff = render.render_frame(case, 3, 1.0)
                report = cues.audit_visible_outcome(case, first, payoff)
                self.assertTrue(report["passed"], report["failed_cues"])
                self.assertEqual(len(report["checks"]), 2)
                self.assertEqual(report["story_semantics"], "not_verified")
                for key in ("approved", "production_ready", "published"):
                    self.assertFalse(report[key])
                for check in report["checks"].values():
                    self.assertLessEqual(check["baseline_match_pixels"],
                                         check["baseline_max"])
                    self.assertGreaterEqual(check["payoff_match_pixels"],
                                            check["payoff_min"])

    def test_same_frame_motion_cannot_fake_a_completed_payoff(self):
        for case in render.KINDS:
            with self.subTest(case=case):
                initial = render.render_frame(case, 0, 0.0)
                result = cues.audit_visible_outcome(case, initial, initial)
                self.assertFalse(result["passed"])
                self.assertGreater(len(result["failed_cues"]), 0)

    def test_caption_only_change_cannot_fake_a_visual_payoff(self):
        for case in render.KINDS:
            initial = render.render_frame(case, 0, 0.0)
            altered = initial.copy()
            ImageDraw.Draw(altered).rectangle((0, 0, 319, 27),
                                              fill=(245, 150, 1))
            ImageDraw.Draw(altered).rectangle((0, 161, 319, 179),
                                              fill=(230, 20, 20))
            report = cues.audit_visible_outcome(case, initial, altered)
            self.assertFalse(report["passed"], case)

    def test_unfinished_attempt_is_not_a_completed_payoff(self):
        for case in render.KINDS:
            with self.subTest(case=case):
                first = render.render_frame(case, 0, 0.0)
                unfinished = render.render_frame(case, 1, 1.0)
                report = cues.audit_visible_outcome(case, first, unfinished)
                self.assertFalse(report["passed"], case)

    def test_only_one_achieved_cue_is_insufficient(self):
        for case in render.KINDS:
            with self.subTest(case=case):
                first = render.render_frame(case, 0, 0.0)
                final = render.render_frame(case, 3, 1.0)
                censored = final.copy()
                name, (region, _, _, _, _) = list(cues.CUES[case].items())[1]
                ImageDraw.Draw(censored).rectangle(region, fill=(4, 10, 17))
                report = cues.audit_visible_outcome(case, first, censored)
                self.assertFalse(report["passed"])
                self.assertIn(name, report["failed_cues"])

    def test_unknown_scene_and_invalid_image_fails_closed(self):
        first = render.render_frame(render.KINDS[0], 0, 0)
        final = render.render_frame(render.KINDS[0], 3, 1)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            cues.audit_visible_outcome("imagined-production-genre", first, final)
        with self.assertRaisesRegex(ValueError, "RGB"):
            cues.audit_visible_outcome(render.KINDS[0], first, final.convert("L"))
        with self.assertRaisesRegex(ValueError, "RGB"):
            cues.audit_visible_outcome(render.KINDS[0], first, Image.new("RGB", (4, 4)))

    def test_only_scene_pixels_are_accepted_by_cue_helper(self):
        img = render.render_frame(render.KINDS[0], 0, 0)
        with self.assertRaisesRegex(ValueError, "exclude captions"):
            cues.cue_pixel_count(img, (0, 0, 50, 20), (20, 30, 40), 20)
        with self.assertRaisesRegex(ValueError, "tolerance"):
            cues.cue_pixel_count(img, (0, 32, 50, 40), (20, 30, 40), 70)


if __name__ == "__main__":
    unittest.main()
