"""Offline regression tests for story subject/cast alignment."""
import unittest
from astra_v2.coordinated_development import build_story_plan, build_narrated_plan, build_ensemble_plan, verify_story_cast, frame, render
from astra_v2.character_object_catalog import character

class StoryCastAlignmentTests(unittest.TestCase):
    def test_facial_expressions_change_character_pixels(self):
        from PIL import Image, ImageChops
        from astra_v2.character_object_catalog import draw_character
        # The isolated workflow intentionally substitutes its lightweight
        # silhouette renderer; test facial pixels only on the real renderer.
        import inspect
        if "expression" not in inspect.signature(draw_character).parameters:
            self.skipTest("facial renderer replaced by isolated silhouette fixture")
        samples = {}
        for expression in ("neutral", "surprised", "happy", "focused"):
            canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
            draw_character(canvas, 400, 0.4, 540, 900, expression=expression)
            samples[expression] = canvas.crop((465, 805, 615, 945))
        for expression in ("surprised", "happy", "focused"):
            self.assertIsNotNone(
                ImageChops.difference(samples["neutral"], samples[expression]).getbbox(),
                f"{expression} face must differ from neutral")
        with self.assertRaises(ValueError):
            draw_character(Image.new("RGBA", (1080, 1920)), 400, 0.4,
                           expression="unsupported")

    def test_story_action_changes_facial_artwork(self):
        from PIL import ImageChops
        plan = build_ensemble_plan("face-action-test", [["fox"]])
        scene = plan["scenes"][0]
        neutral = frame({**scene, "action": "approach"}, 0.4)
        surprised = frame({**scene, "action": "react"}, 0.4)
        self.assertIsNotNone(ImageChops.difference(neutral, surprised).getbbox())

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

    def test_ensemble_identity_drift_across_scenes_is_rejected(self):
        plan = build_ensemble_plan("identity-drift", [["fox", "dog"], ["dog", "fox"]])
        second = plan["scenes"][1]["actors"][0]
        second["character_id"] = (second["character_id"] // 100) * 100 + (second["character_id"] + 1) % 100
        plan["scenes"][1]["character_id"] = second["character_id"]
        with self.assertRaises(ValueError):
            verify_story_cast(plan)

    def test_primary_actor_mismatch_is_rejected(self):
        plan = build_ensemble_plan("primary-mismatch", [["fox", "dog"]])
        plan["scenes"][0]["character_id"] = plan["scenes"][0]["actors"][1]["character_id"]
        with self.assertRaises(ValueError):
            verify_story_cast(plan)

    def test_ensemble_layout_all_cast_sizes(self):
        from PIL import ImageChops
        for count in (1, 2, 3, 4):
            cast = ["fox", "dog", "cat", "rabbit"][:count]
            scene = build_ensemble_plan("layout-regression", [cast])["scenes"][0]
            before, after = frame(scene, 0.0), frame(scene, 0.8)
            self.assertEqual(before.size, (540, 960))
            self.assertIsNotNone(ImageChops.difference(before, after).getbbox(), count)

    def test_explicit_action_cues_change_rendered_frame(self):
        from PIL import ImageChops
        scene = build_ensemble_plan("action-cue", [["fox"]])["scenes"][0]
        scene["action"] = "approach"
        approach = frame(scene, 0.8)
        scene["action"] = "celebrate"
        celebrate = frame(scene, 0.8)
        self.assertIsNotNone(ImageChops.difference(approach, celebrate).getbbox())

    def test_carry_action_has_visible_motion(self):
        from PIL import ImageChops
        scene = build_ensemble_plan("carry-cue", [["fox"]])["scenes"][0]
        scene["action"] = "carry"
        a, b = frame(scene, 0.0), frame(scene, 0.8)
        self.assertIsNotNone(ImageChops.difference(a, b).getbbox())
        scene["action"] = "approach"
        self.assertIsNotNone(ImageChops.difference(b, frame(scene, 0.8)).getbbox())

    def test_carry_action_with_multiple_actors(self):
        from PIL import ImageChops
        for cast in (["fox"], ["fox", "dog"], ["fox", "dog", "cat", "rabbit"]):
            scene = build_ensemble_plan("carry-ensemble", [cast])["scenes"][0]
            scene["action"] = "carry"
            first, second = frame(scene, 0.0), frame(scene, 0.8)
            self.assertEqual(first.size, (540, 960))
            self.assertIsNotNone(ImageChops.difference(first, second).getbbox())

    def test_scaled_carry_prop_differs_from_static_prop(self):
        from PIL import ImageChops
        for cast in (["fox"], ["fox", "dog", "cat", "rabbit"]):
            scene = build_ensemble_plan("carry-prop-size", [cast])["scenes"][0]
            scene["action"] = "carry"
            carrying = frame(scene, 0.5)
            scene["action"] = "react"
            static = frame(scene, 0.5)
            self.assertEqual(carrying.size, (540, 960))
            self.assertIsNotNone(ImageChops.difference(carrying, static).getbbox())

    def test_story_file_validates_explicit_ensemble(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from astra_v2.coordinated_development import load_story_file
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "story.json"
            path.write_text(json.dumps({"mode": "ensemble", "scenes": [
                {"actors": ["fox", "dog"], "action": "carry", "narration": "A fox carries a gift."},
                {"actors": ["fox"], "action": "react"}]}))
            plan = load_story_file(path, "test")
            self.assertEqual(plan["scenes"][0]["action"], "carry")
            self.assertEqual(len(plan["scenes"][0]["actors"]), 2)
            self.assertFalse(plan["publication_allowed"])
            path.write_text(json.dumps({"mode": "ensemble", "scenes": [
                {"actors": ["hedgehog"]}]}))
            with self.assertRaises(ValueError):
                load_story_file(path, "test")

    def test_story_file_rejects_malformed_actor_types(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from astra_v2.coordinated_development import load_story_file
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "story.json"
            for actors in ("fox", None, [], [42], ["fox"] * 5):
                path.write_text(json.dumps({"mode": "ensemble", "scenes": [
                    {"actors": actors}]}))
                with self.subTest(actors=actors), self.assertRaises(ValueError):
                    load_story_file(path, "invalid-cast")

    def test_narration_cannot_name_missing_ensemble_actor(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from astra_v2.coordinated_development import load_story_file
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "story.json"
            path.write_text(json.dumps({"mode": "ensemble", "scenes": [
                {"actors": ["fox"], "narration": "A fox and a dog discover a gift."}]}))
            with self.assertRaises(ValueError):
                load_story_file(path, "missing-dog")
            path.write_text(json.dumps({"mode": "ensemble", "scenes": [
                {"actors": ["fox", "dog"], "narration": "A fox and a dog discover a gift."}]}))
            self.assertTrue(load_story_file(path, "present-dog")["story_subjects_verified"])

    def test_authored_story_preserves_recurring_prop(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from astra_v2.coordinated_development import load_story_file
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "story.json"
            path.write_text(json.dumps({"mode": "ensemble", "scenes": [
                {"actors": ["fox"], "object_id": 1900},
                {"actors": ["fox", "dog"], "action": "carry"},
                {"actors": ["fox"], "action": "celebrate"}]}))
            plan = load_story_file(path, "prop-continuity")
            self.assertEqual([scene["object_id"] for scene in plan["scenes"]],
                             [1900, 1900, 1900])
            self.assertEqual(plan["scenes"][0]["object"][0], "gift")
            path.write_text(json.dumps({"mode": "ensemble", "scenes": [
                {"actors": ["fox"], "object_id": -1}]}))
            with self.assertRaises(ValueError):
                load_story_file(path, "invalid-prop")

    def test_authored_story_allows_same_prop_with_changing_cast(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from astra_v2.coordinated_development import build_ensemble_plan, render
        plan = build_ensemble_plan("continuity-regression", [
            ["fox"], ["fox", "dog"], ["fox", "dog", "cat"]
        ])
        for scene in plan["scenes"]:
            scene["object_id"] = plan["scenes"][0]["object_id"]
            scene["object"] = plan["scenes"][0]["object"]
        with TemporaryDirectory() as tmp:
            result = render(plan, Path(tmp), fps=2)
            self.assertFalse(result["publication_allowed"])
            self.assertTrue((Path(tmp) / "report.json").exists())

    def test_unsupported_action_fails_before_output(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        plan = build_ensemble_plan("action-cue", [["fox"]])
        plan["scenes"][0]["action"] = "fly"
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
