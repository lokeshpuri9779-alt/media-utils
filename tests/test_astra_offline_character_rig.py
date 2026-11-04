"""Unit and negative controls for hand-articulated CPU preview characters."""
from __future__ import annotations

from PIL import Image, ImageDraw
import unittest

from tools import astra_offline_character_rig as rig
from tools import astra_offline_procedural_preview as preview


class RigTests(unittest.TestCase):
    def test_three_rigs_remain_visible_across_all_four_scenes(self):
        self.assertEqual(set(preview.KINDS), set(rig.PROFILES))
        for case in preview.KINDS:
            with self.subTest(case=case):
                frames = [preview.render_frame(case, stage, 1.0)
                          for stage in range(4)]
                audit = rig.audit_character_presence(case, frames)
                self.assertTrue(audit["passed"], audit)
                self.assertEqual(len(audit["marker_pixel_counts"]), 4)
                self.assertEqual(audit["character_identity_semantics"], "not_verified")
                self.assertFalse(audit["production_ready"])
                self.assertFalse(audit["published"])

    def test_each_rig_changes_actual_silhouette_during_scene(self):
        for case in preview.KINDS:
            for stage in range(4):
                with self.subTest(case=case, stage=stage):
                    start = rig.render_actor_layer(case, stage, 0.0)
                    finish = rig.render_actor_layer(case, stage, 1.0)
                    self.assertEqual(start.mode, "RGBA")
                    self.assertEqual(start.size, rig.SIZE)
                    self.assertNotEqual(start.tobytes(), finish.tobytes())
                    # The character itself has nontransparent pixels.
                    self.assertIsNotNone(start.getchannel("A").getbbox())
                    self.assertIsNotNone(finish.getchannel("A").getbbox())

    def test_beaver_at_payoff_does_not_cover_ducklings_on_safe_bank(self):
        from tools.astra_offline_visual_cues import (
            CUES, cue_pixel_count, audit_visible_outcome,
        )
        case = "footbridge-ducklings"
        final = preview.render_frame(case, 3, 1.0)
        original = preview.render_frame(case, 0, 0.0)
        status = audit_visible_outcome(case, original, final)
        self.assertTrue(status["passed"])
        region, color, tolerance, _, minimum = CUES[case]["ducklings_on_safe_bank"]
        # Require a large reserve of visible duckling pixels to remain
        # legible after normal low-resolution H264 chroma subsampling.
        self.assertGreaterEqual(cue_pixel_count(final, region, color, tolerance),
                                minimum * 2)

    def test_missing_or_obscured_rig_marker_rejected(self):
        for case in preview.KINDS:
            frames = [preview.render_frame(case, stage, 1)
                      for stage in range(4)]
            missing = [frame.copy() for frame in frames]
            info = rig.PROFILES[case]
            ImageDraw.Draw(missing[2]).rectangle(
                info["roi"], fill=(2, 3, 4)
            )
            result = rig.audit_character_presence(case, missing)
            self.assertFalse(result["passed"], case)
            self.assertLess(result["marker_pixel_counts"][2],
                            result["minimum_per_beat"])

    def test_label_changes_cannot_fake_hidden_character(self):
        case = "glasshouse-sunshade"
        neutral = Image.new("RGB", rig.SIZE, (20, 20, 20))
        frames = [neutral.copy() for _ in range(4)]
        for frame in frames:
            ImageDraw.Draw(frame).rectangle((0, 0, 319, 27),
                                            fill=rig.PROFILES[case]["mark"])
        result = rig.audit_character_presence(case, frames)
        self.assertFalse(result["passed"])

    def test_only_a_color_marker_is_not_proof_of_actor_identity(self):
        case = "glasshouse-sunshade"
        marker = rig.PROFILES[case]["mark"]
        fake = Image.new("RGB", rig.SIZE, (20, 20, 20))
        ImageDraw.Draw(fake).rectangle((18, 90, 33, 106), fill=marker)
        audit = rig.audit_character_presence(case, [fake] * 4)
        # Explicit negative limitation: a matching patch can fool this
        # lightweight cue, so never call it a semantic identity check.
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["character_identity_semantics"], "not_verified")
        self.assertFalse(audit["approved"])

    def test_unknown_profiles_and_malformed_values_fail(self):
        with self.assertRaisesRegex(ValueError, "unknown"):
            rig.render_actor_layer("unlisted-case", 0, 0)
        for bad_stage in (-1, 4, True, "1"):
            with self.assertRaisesRegex(ValueError, "stage"):
                rig.render_actor_layer(preview.KINDS[0], bad_stage, 0.5)
        for bad_t in (-0.1, 1.5, float("nan"), float("inf")):
            with self.assertRaisesRegex(ValueError, "progress"):
                rig.render_actor_layer(preview.KINDS[0], 0, bad_t)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            rig.audit_character_presence(preview.KINDS[0], [])
        with self.assertRaisesRegex(ValueError, "RGB"):
            rig.marker_pixel_count(Image.new("RGBA", rig.SIZE), preview.KINDS[0])


if __name__ == "__main__":
    unittest.main()
