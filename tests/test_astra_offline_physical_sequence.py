"""Negative controls for six concrete CPU-only physical repair actions.

Pixel/material witnesses are *not* a human semantic judgment. Every recorded
preview stays unapproved, unpublished and separate from Main.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch
from PIL import Image

from tools import astra_offline_procedural_preview as preview
from tools import astra_offline_physical_sequence as physical


class PhysicalRepairSequenceTests(unittest.TestCase):
    def test_six_real_scene_actions_have_moving_distinct_materials(self):
        self.assertEqual(sum(map(len, physical.WITNESSES.values())), 6)
        self.assertEqual(set(physical.CASES), set(preview.KINDS))
        for case in physical.CASES:
            for stage_name in physical.WITNESSES[case]:
                stage = physical.STAGES.index(stage_name)
                with self.subTest(case=case, stage=stage_name):
                    first = preview.render_frame(case, stage, 0)
                    last = preview.render_frame(case, stage, 1)
                    audit = physical.audit_physical_sequence(case, stage, first, last)
                    self.assertTrue(audit["passed"], audit)
                    self.assertLess(audit["earlier_matching_pixels"] + 5,
                                    audit["later_matching_pixels"])
                    self.assertEqual(audit["semantics"], "not_verified")
                    self.assertEqual(audit["hand_prop_mechanics"], "not_verified")
                    self.assertFalse(audit["approved"])

    def test_removing_physical_actions_fails_even_when_actor_and_link_move(self):
        empty = Image.new("RGBA", physical.SIZE, (0, 0, 0, 0))
        with patch.object(preview, "render_physical_sequence", return_value=empty):
            for case in physical.CASES:
                for stage_name in physical.WITNESSES[case]:
                    stage = physical.STAGES.index(stage_name)
                    with self.subTest(case=case, stage=stage_name):
                        early = preview.render_frame(case, stage, 0)
                        late = preview.render_frame(case, stage, 1)
                        result = physical.audit_physical_sequence(case, stage, early, late)
                        self.assertFalse(result["passed"], result)

    def test_still_or_caption_only_cannot_fake_repair(self):
        for case in physical.CASES:
            for stage_name in physical.WITNESSES[case]:
                stage = physical.STAGES.index(stage_name)
                image = preview.render_frame(case, stage, 1)
                with self.subTest(case=case, stage=stage_name):
                    self.assertFalse(physical.audit_physical_sequence(
                        case, stage, image, image)["passed"])

    def test_no_overlay_for_irrelevant_scene(self):
        for case in physical.CASES:
            layer = physical.render_physical_sequence(case, 0, 1)
            self.assertIsNone(layer.getchannel("A").getbbox())

    def test_invalid_case_stage_progress_fail_closed(self):
        for case, stage, t in (
            ("unknown-case", 1, 0.5),
            (physical.CASES[0], -1, 0.5),
            (physical.CASES[0], True, 0.5),
            (physical.CASES[0], 4, 0.5),
            (physical.CASES[0], 1, float("nan")),
            (physical.CASES[0], 1, float("inf")),
            (physical.CASES[0], 1, -0.05),
        ):
            with self.subTest(case=case, stage=stage, progress=t):
                with self.assertRaises(ValueError):
                    physical.render_physical_sequence(case, stage, t)

    def test_malformed_pixel_frame_and_unknown_moment_fail(self):
        case = physical.CASES[0]
        with self.assertRaises(ValueError):
            physical.audit_physical_sequence(
                case, 0, Image.new("RGB", physical.SIZE),
                Image.new("RGB", physical.SIZE))
        with self.assertRaises(ValueError):
            physical.audit_physical_sequence(
                case, 1, Image.new("RGB", (100, 100)),
                Image.new("RGB", physical.SIZE))

    def test_safety_metadata_is_not_semantic_approval(self):
        from pathlib import Path
        source = Path(physical.__file__).read_text(encoding="utf-8")
        for token in ("youtube.upload", "requests.post(", "OPENAI_API_KEY"):
            self.assertNotIn(token, source)
        for case in physical.CASES:
            layer = physical.render_physical_sequence(case, 3, 1)
            self.assertEqual(layer.size, physical.SIZE)
            self.assertEqual(layer.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()
