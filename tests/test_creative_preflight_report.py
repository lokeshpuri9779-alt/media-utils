"""Regression coverage for read-only creative preflight diagnostics."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from astra_v2.creative_preflight_report import analyze_batch, main, scene_taxonomy_diagnostic
from astra_v2.editorial_approval_manifest import story_digest


def sample_story(text="A robot reaches for the amber orb."):
    return {
        "genre": "fiction", "kind": "microfiction", "content_id": "test-story",
        "title": "The Copper Keeper",
        "production_ready": True,
        "story_beats": [
            {"speech": text, "visual": "robot", "story_beat": "reveal"},
            {"speech": "The robot tests the lantern.", "visual": "door", "story_beat": "build"},
        ],
    }


class CreativePreflightReportTests(unittest.TestCase):
    def test_structural_eligibility_is_not_semantic_or_publication_approval(self):
        story = sample_story()
        before = json.dumps(story, sort_keys=True)
        report = analyze_batch({"status": "unreviewed", "stories": [story]},
                               checker=lambda _: (True, None, ("solo", "solo")))
        self.assertEqual(report["renderer_status_counts"], {"structurally_eligible": 1})
        self.assertEqual(report["candidates"][0]["renderer_shot_count"], 2)
        self.assertEqual(report["candidates"][0]["story_sha256"], story_digest(story))
        self.assertFalse(report["candidates"][0]["semantic_visual_approval"])
        self.assertFalse(report["publication_triggered"])
        self.assertFalse(report["editorial_approval"])
        self.assertEqual(json.dumps(story, sort_keys=True), before)


    def test_planned_scene_taxonomy_resolves_only_known_labels(self):
        story = sample_story()
        before = json.dumps(story, sort_keys=True)
        plan = [
            {"story_environment": "forest", "speech": "A fox sees a lantern."},
            {"visual_prompt": "An indoor cabin with a wooden hearth"},
            {"visual_prompt": "A telescope in an observatory"},
        ]
        with patch("studio_renderer.make_plan", return_value=plan) as make_plan:
            result = scene_taxonomy_diagnostic(story)
        self.assertEqual(result["status"], "partially_recognized")
        self.assertEqual(result["shot_count"], 3)
        self.assertEqual(result["recognized_shots"], 2)
        self.assertEqual(result["unresolved_shots"], 1)
        make_plan.assert_called_once()
        self.assertEqual(json.dumps(story, sort_keys=True), before)

    def test_diagnostic_does_not_claim_artwork_or_editorial_approval(self):
        story = sample_story()
        with patch("studio_renderer.make_plan", return_value=[
            {"story_environment": "forest"}, {"visual_prompt": "underwater reef"}]):
            report = analyze_batch({"status": "unreviewed", "stories": [story]},
                                   checker=lambda _: (True, None, ("solo", "solo")))
        self.assertEqual(report["scene_taxonomy_status_counts"],
                         {"all_shots_recognized": 1})
        self.assertEqual(report["scene_taxonomy_recognized_shots"], 2)
        self.assertEqual(report["scene_taxonomy_unresolved_shots"], 0)
        self.assertEqual(report["scene_taxonomy_scope"],
                         "planning_only_no_verified_artwork_or_semantic_approval")
        self.assertFalse(report["candidates"][0]["publication_approved"])
        self.assertFalse(report["editorial_approval"])

    def test_unknown_scene_or_failure_never_becomes_recognized(self):
        story = sample_story()
        with patch("studio_renderer.make_plan", return_value=[
            {"visual_prompt": "A meadow and a wooden courtyard"}]):
            result = scene_taxonomy_diagnostic(story)
        self.assertEqual(result["status"], "no_shots_recognized")
        self.assertEqual(result["unresolved_shots"], 1)
        with patch("studio_renderer.make_plan", side_effect=RuntimeError("PRIVATE_TOKEN")):
            failed = scene_taxonomy_diagnostic(story)
        self.assertEqual(failed["status"], "unavailable")
        self.assertNotIn("PRIVATE_TOKEN", str(failed))
        self.assertEqual(failed["recognized_shots"], 0)
        with patch("studio_renderer.make_plan") as build:
            non_fiction = {**story, "genre": "documentary"}
            self.assertEqual(scene_taxonomy_diagnostic(non_fiction)["status"],
                             "not_applicable")
            build.assert_not_called()

    def test_scene_diagnostic_batch_remains_bounded_and_separate_from_approval(self):
        rows = [
            {"visual_prompt": "in a forest"},
            {"visual_prompt": "on a grassland"},
            {"visual_prompt": "on a city street"},
        ]
        with patch("studio_renderer.make_plan", return_value=rows):
            report = analyze_batch({"status": "unreviewed",
                                    "stories": [sample_story()]},
                                   checker=lambda _: (False, "cast mismatch", ()))
        self.assertEqual(report["scene_taxonomy_status_counts"],
                         {"partially_recognized": 1})
        self.assertEqual(report["scene_taxonomy_recognized_shots"], 2)
        self.assertEqual(report["scene_taxonomy_unresolved_shots"], 1)
        self.assertEqual(report["renderer_status_counts"], {"incompatible": 1})
        self.assertFalse(report["publication_triggered"])

    def test_unsupported_human_actor_is_classified_without_leaking_reason(self):
        story = sample_story("Delve deep as a keeper unlocks the lighthouse.")
        report = analyze_batch({"status": "unreviewed", "stories": [story]},
                               checker=lambda _: (False, "shot 2: human_actor_private_secret", ()))
        item = report["candidates"][0]
        self.assertEqual(item["renderer_status"], "incompatible")
        self.assertEqual(item["renderer_reason_category"], "unsupported_human_actor")
        self.assertEqual(item["script"]["status"], "review_suggested")
        self.assertNotIn("private_secret", str(report))
        self.assertFalse(item["publication_approved"])

    def test_failed_diagnostics_do_not_become_approval_or_leak(self):
        story = sample_story()
        def fail(_):
            raise RuntimeError("PRIVATE_KEY_DO_NOT_LOG")
        report = analyze_batch({"status": "unreviewed", "stories": [story]}, checker=fail)
        self.assertEqual(report["renderer_status_counts"], {"unavailable": 1})
        self.assertNotIn("PRIVATE_KEY", str(report))
        self.assertFalse(report["publication_triggered"])

    def test_nonfiction_skips_directed_renderer(self):
        story = sample_story()
        story["genre"] = "documentary"
        report = analyze_batch({"status": "unreviewed", "stories": [story]},
                               checker=lambda _: self.fail("Must not call renderer"))
        self.assertEqual(report["renderer_status_counts"], {"not_applicable": 1})

    def test_bad_input_fails_closed(self):
        for data in (None, {}, {"status": "approved", "stories": []},
                     {"status": "unreviewed", "stories": ["invalid"]},
                     {"status": "unreviewed", "stories": [{}] * 51}):
            with self.subTest(data=str(data)[:40]):
                with self.assertRaises(ValueError):
                    analyze_batch(data, checker=lambda _: (True, None, ()))

    def test_narration_diagnostics_do_not_mutate_history_or_story(self):
        story = sample_story("A door opens. A door opens.")
        before = story_digest(story)
        report = analyze_batch({"status": "unreviewed", "stories": [story]},
                               checker=lambda _: (False, "Empty directed plan", ()))
        self.assertEqual(report["renderer_reason_counts"], {"empty_storyboard": 1})
        self.assertEqual(report["candidates"][0]["script"]["repeated_sentence_count"], 1)
        self.assertEqual(before, story_digest(story))

    def test_cli_serializes_counts_without_original_script_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "input.json", Path(tmp) / "report.json"
            story = sample_story("PRIVATE_SCRIPT_SENTINEL")
            source.write_text(json.dumps({"status": "unreviewed", "stories": [story]}))
            stream = io.StringIO()
            with patch("astra_v2.renderer_eligibility.check_renderer_eligibility",
                       return_value=(False, "private secret error", ())), \
                 contextlib.redirect_stdout(stream):
                main(["--input", str(source), "--output", str(target)])
            report = json.loads(target.read_text())
            self.assertNotIn("PRIVATE_SCRIPT_SENTINEL", target.read_text())
            self.assertNotIn("private secret", target.read_text())
            self.assertNotIn("PRIVATE_SCRIPT_SENTINEL", stream.getvalue())
            self.assertEqual(report["generated"], 1)
            self.assertFalse(report["publication_triggered"])
            self.assertIn("scene_taxonomy_status_counts", report)
            self.assertNotIn("PRIVATE_SCRIPT_SENTINEL", stream.getvalue())

    def test_empty_batch_is_not_approval(self):
        report = analyze_batch({"status": "unreviewed", "stories": []},
                               checker=lambda _: self.fail("unexpected check"))
        self.assertEqual(report["generated"], 0)
        self.assertEqual(report["renderer_status_counts"], {})
        self.assertFalse(report["editorial_approval"])


if __name__ == "__main__":
    unittest.main()
