"""Offline regression tests for story subject/cast alignment."""
import unittest
from astra_v2.coordinated_development import build_story_plan, build_narrated_plan, build_ensemble_plan, verify_story_cast, frame, render
from astra_v2.character_object_catalog import character

class StoryCastAlignmentTests(unittest.TestCase):
    def test_all_supported_subjects_match(self):
        from astra_v2.character_object_catalog import SPECIES
        plan = build_story_plan("alignment-regression", list(SPECIES))
        self.assertTrue(verify_story_cast(plan))
        for scene in plan["scenes"]:
            self.assertEqual(scene["subject"], character(scene["character_id"])[0])
            self.assertFalse(plan["publication_allowed"])

    def test_unsupported_subject_fails_closed(self):
        with self.assertRaises(ValueError):
            build_story_plan("alignment-regression", ["hedgehog"])

    def test_tampered_cast_is_rejected(self):
        plan = build_story_plan("alignment-regression", ["fox"])
        plan["scenes"][0]["character_id"] = 0
        with self.assertRaises(ValueError):
            verify_story_cast(plan)

    def test_narration_selects_correct_species(self):
        plan = build_narrated_plan("narration-test", ["The fox found a key.", "The fox opened the door."])
        self.assertEqual([scene["subject"] for scene in plan["scenes"]], ["fox", "fox"])
        self.assertTrue(verify_story_cast(plan))

    def test_protagonist_persists_across_unnamed_scenes(self):
        plan = build_narrated_plan("continuity-test", [
            "A fox found a mysterious box.",
            "It carried the box into the forest.",
            "The fox finally opened it.",
        ])
        self.assertEqual([scene["subject"] for scene in plan["scenes"]], ["fox", "fox", "fox"])
        self.assertTrue(verify_story_cast(plan))

    def test_unannounced_protagonist_switch_fails(self):
        with self.assertRaises(ValueError):
            build_narrated_plan("continuity-test", ["The fox entered.", "The dog escaped."])

    def test_first_scene_must_identify_protagonist(self):
        with self.assertRaises(ValueError):
            build_narrated_plan("continuity-test", ["It was a dark night.", "The fox appeared."])

    def test_narration_rejects_hedgehog_and_ambiguity(self):
        for narration in ("A hedgehog crossed the road.", "The turtle met a fox.", "Suddenly the lights went out."):
            with self.assertRaises(ValueError):
                build_narrated_plan("narration-test", [narration])

    def test_ensemble_cast_is_stable_across_scenes(self):
        plan = build_ensemble_plan("ensemble-test", [["fox", "dog"], ["dog"], ["fox", "dog"]])
        self.assertTrue(verify_story_cast(plan))
        first = plan["scenes"][0]["actors"]
        last = plan["scenes"][2]["actors"]
        self.assertEqual([a["character_id"] for a in first], [a["character_id"] for a in last])
        self.assertFalse(plan["publication_allowed"])

    def test_ensemble_rejects_invalid_cast(self):
        for cast in ([["hedgehog"]], [["fox", "fox"]], [[]], [["fox"] * 5]):
            with self.assertRaises(ValueError):
                build_ensemble_plan("ensemble-test", cast)

    def test_ensemble_frame_has_multiple_visible_actors(self):
        from PIL import ImageChops
        plan = build_ensemble_plan("ensemble-frame-test", [["fox", "dog"]])
        scene = plan["scenes"][0]
        both = frame(scene, 0.4)
        solo = frame({**scene, "actors": [scene["actors"][0]]}, 0.4)
        self.assertEqual(both.size, (540, 960))
        self.assertIsNotNone(ImageChops.difference(both, solo).getbbox())
        self.assertIsNotNone(ImageChops.difference(both, frame(scene, 1.1)).getbbox())

    def test_render_rejects_cast_mismatch_without_trusting_flag(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        plan = build_ensemble_plan("render-gate-test", [["fox", "dog"]])
        plan.pop("story_subjects_verified")
        plan["scenes"][0]["actors"][1]["character_id"] = 0
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                render(plan, Path(tmp))

    def test_render_rejects_missing_ensemble_cast(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        plan = build_ensemble_plan("render-gate-test", [["fox"]])
        plan["scenes"][0].pop("actors")
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                render(plan, Path(tmp))

    def test_ensemble_tampering_is_rejected(self):
        plan = build_ensemble_plan("ensemble-test", [["fox", "dog"]])
        plan["scenes"][0]["actors"][1]["character_id"] = 0
        with self.assertRaises(ValueError):
            verify_story_cast(plan)

    def test_invalid_input_is_rejected(self):
        for subjects in ([], ["fox"] * 121, "fox", [None]):
            with self.assertRaises(ValueError):
                build_story_plan("alignment-regression", subjects)

if __name__ == "__main__":
    unittest.main()
