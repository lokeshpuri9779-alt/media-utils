"""Actual scene-link negative controls for bounded ASTRA action previews."""
from __future__ import annotations

import unittest
from PIL import Image, ImageDraw

from tools import astra_offline_action_links as links
from tools import astra_offline_procedural_preview as preview
from tools.astra_offline_character_rig import actor_grip_position


class ActionLinkTests(unittest.TestCase):
    def test_six_attempt_and_payoff_interactions_have_shared_grips(self):
        for case in preview.KINDS:
            for stage in links.ACTION_STAGES:
                with self.subTest(case=case, stage=stage):
                    path = links.connection_path(case, stage, 1.0)
                    self.assertEqual(
                        path[0], actor_grip_position(case, stage, 1.0))
                    self.assertGreaterEqual(len(path), 2)
                    frame = preview.render_frame(case, stage, 1.0)
                    report = links.audit_action_link(case, stage, 1.0, frame)
                    self.assertTrue(report["passed"], report)
                    self.assertTrue(report["grip_is_exact_actor_rig_endpoint"])
                    self.assertEqual(report["prop_interaction_semantics"],
                                     "not_verified")
                    self.assertFalse(report["approved"])
                    self.assertFalse(report["production_ready"])
                    self.assertFalse(report["published"])

    def test_links_are_physically_animated_with_grip_or_prop(self):
        for case in preview.KINDS:
            for stage in links.ACTION_STAGES:
                first = links.connection_path(case, stage, 0.0)
                last = links.connection_path(case, stage, 1.0)
                with self.subTest(case=case, stage=stage):
                    self.assertNotEqual(first, last)
                    self.assertNotEqual(
                        links.render_action_link(case, stage, 0.0).tobytes(),
                        links.render_action_link(case, stage, 1.0).tobytes())

    def test_no_link_in_setup_or_setback(self):
        for case in preview.KINDS:
            for stage in (0, 2):
                with self.subTest(case=case, stage=stage):
                    layer = links.render_action_link(case, stage, 0.5)
                    self.assertIsNone(layer.getchannel("A").getbbox())

    def test_missing_colored_link_fails_even_if_character_moves(self):
        for case in preview.KINDS:
            for stage in links.ACTION_STAGES:
                with self.subTest(case=case, stage=stage):
                    frame = preview.render_frame(case, stage, 1.0).copy()
                    path = links.connection_path(case, stage, 1.0)
                    a, b = path[0], path[1]
                    midpoint = (round((a[0]+b[0])/2),
                                round((a[1]+b[1])/2))
                    ImageDraw.Draw(frame).rectangle(
                        (midpoint[0]-7, midpoint[1]-7,
                         midpoint[0]+7, midpoint[1]+7),
                        fill=(10, 12, 16))
                    audit = links.audit_action_link(case, stage, 1.0, frame)
                    self.assertFalse(audit["passed"])

    def test_titles_only_are_not_action_proof(self):
        blank = Image.new("RGB", links.SIZE, (8, 8, 14))
        ImageDraw.Draw(blank).rectangle(
            (0, 0, 319, 27), fill=links.LINK_COLOR
        )
        for case in links.CASES:
            self.assertFalse(links.audit_action_link(
                case, 1, 1.0, blank)["passed"])

    def test_materials_replace_oversized_orange_debug_guides(self):
        self.assertEqual(links.LINE_WIDTH, 4)
        self.assertEqual(set(links.MATERIALS), set(links.CASES))
        for case in links.CASES:
            for stage in links.ACTION_STAGES:
                with self.subTest(case=case, stage=stage):
                    pal = links.MATERIALS[case]
                    self.assertIn(pal["kind"], (
                        "hemp_pulley_cord", "reed_binding_rope",
                        "steel_adjustment_link"))
                    self.assertNotEqual(pal["stroke"], links.LINK_COLOR)
                    layer = links.render_action_link(case, stage, 1.0)
                    self.assertNotIn(
                        (*links.LINK_COLOR, 255), set(layer.getdata()))
                    frame = preview.render_frame(case, stage, 1.0)
                    report = links.audit_action_link(case, stage, 1.0, frame)
                    self.assertTrue(report["passed"], report)
                    self.assertEqual(report["material"], pal["kind"])
                    self.assertFalse(report["diagnostic_orange_is_rendered"])
                    self.assertEqual(report["prop_interaction_semantics"],
                                     "not_verified")

    def test_unrelated_material_patch_cannot_replace_a_real_connection(self):
        for case in links.CASES:
            wrong_color = ((160, 216, 231) if case != "moon-mirror-garden"
                           else (130, 93, 57))
            for stage in links.ACTION_STAGES:
                with self.subTest(case=case, stage=stage):
                    frame = preview.render_frame(case, stage, 1.0).copy()
                    path = links.connection_path(case, stage, 1.0)
                    a, b = path[0], path[1]
                    midpoint = (round((a[0]+b[0])/2),
                                round((a[1]+b[1])/2))
                    ImageDraw.Draw(frame).rectangle(
                        (midpoint[0]-8, midpoint[1]-8,
                         midpoint[0]+8, midpoint[1]+8),
                        fill=wrong_color)
                    self.assertFalse(
                        links.audit_action_link(case, stage, 1.0, frame)["passed"])

    def test_invalid_parameters_fail_closed(self):
        for bad in ("invalid-case", "", "production-story"):
            with self.assertRaisesRegex(ValueError, "unsupported"):
                links.connection_path(bad, 1, 0.5)
        for bad_stage in (-1, 0, 2, 4, True):
            with self.assertRaises(ValueError):
                links.connection_path(links.CASES[0], bad_stage, 0.5)
        for bad_progress in (-0.1, 1.1, float("nan")):
            with self.assertRaisesRegex(ValueError, "progress"):
                links.connection_path(links.CASES[0], 1, bad_progress)
        with self.assertRaisesRegex(ValueError, "RGB"):
            links.audit_action_link(
                links.CASES[0], 1, 1.0,
                Image.new("RGBA", links.SIZE))


if __name__ == "__main__":
    unittest.main()
