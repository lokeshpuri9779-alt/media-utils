"""Regression tests for exact-shot, review-only renderer repair packets."""
import unittest
from unittest.mock import patch

from astra_v2.renderer_repair_queue import build_renderer_repair_gap


class RendererRepairQueueTests(unittest.TestCase):
    def test_captures_exact_rejected_shot_and_preserves_authored_context(self):
        story = {
            "content_id": "story-fox-17",
            "title": "The Fox and the Signal Bell",
            "genre": "fiction",
            "story_environment": "A misty railway clearing",
            "visual_style": "soft painted storybook",
            "visual_bible": {"fox": "russet fur and white chest"},
            "story_cast": [{"character_id": "fox-1", "name": "Pip",
                            "appearance": "russet fur", "clothing": "blue scarf"}],
            "story_beats": [{"speech": "The bell rang twice.",
                             "action": "Pip turns toward the signal.",
                             "visual_prompt": "A fox beside a brass railway bell."}],
        }
        plan = [
            {"scene_id": "scene-opening", "visual": "A quiet forest"},
            {"scene_id": "scene-signal-bell", "visual": "railway clearing",
             "speech": "The bell rang twice.", "action": "Pip turns toward the signal.",
             "visual_prompt": "A fox beside a brass railway bell."},
            {"scene_id": "scene-ending", "visual": "sunrise"},
        ]
        with patch("studio_renderer.make_plan", return_value=plan) as make_plan:
            result = build_renderer_repair_gap(
                story, "renderer_incompatible: shot 2: signal_graphic_does_not_depict_narrated_event"
            )

        make_plan.assert_called_once()
        self.assertEqual(result["content_id"], "story-fox-17")
        self.assertEqual(result["shot_count"], 3)
        self.assertEqual(len(result["missing_shots"]), 1)
        shot = result["missing_shots"][0]
        self.assertEqual(shot["shot"], 2)
        self.assertEqual(shot["scene_id"], "scene-signal-bell")
        self.assertEqual(shot["renderer_issue"], "signal_graphic_does_not_depict_narrated_event")
        self.assertEqual(shot["reason"], "scene_unresolved")
        self.assertEqual(shot["authored_context"]["authored_fields"]["speech"],
                         "The bell rang twice.")
        self.assertEqual(result["story_context"]["visual_bible"]["fox"],
                         "russet fur and white chest")
        self.assertEqual(result["story_context"]["story_cast"][0]["name"], "Pip")
        self.assertEqual(result["story_context"]["story_beats"][0]["action"],
                         "Pip turns toward the signal.")

    def test_uses_deterministic_scene_id_only_when_plan_has_none(self):
        story = {"content_id": "story-9"}
        with patch("studio_renderer.make_plan", return_value=[{"visual": "forest"}]):
            result = build_renderer_repair_gap(
                story, "renderer_incompatible: shot 1: unsupported_scene_action"
            )
        self.assertEqual(result["missing_shots"][0]["scene_id"], "story-9:shot:1")

    def test_rejects_non_renderer_and_malformed_rejections_without_planning(self):
        story = {"content_id": "story-1"}
        cases = (
            "policy_rejected: unsafe",
            "renderer_incompatible: shot 0: invalid",
            "renderer_incompatible: shot 257: invalid",
            "renderer_incompatible: shot 1:",
            "renderer_incompatible: shot 1: issue\nextra",
            "renderer_incompatible: shot one: issue",
        )
        for rejection in cases:
            with self.subTest(rejection=rejection):
                with patch("studio_renderer.make_plan") as make_plan:
                    self.assertIsNone(build_renderer_repair_gap(story, rejection))
                    make_plan.assert_not_called()

    def test_missing_story_identity_or_unavailable_exact_shot_is_not_queued(self):
        with patch("studio_renderer.make_plan", return_value=[{}]) as make_plan:
            self.assertIsNone(build_renderer_repair_gap(
                {}, "renderer_incompatible: shot 1: unsupported_action"
            ))
            self.assertIsNone(build_renderer_repair_gap(
                {"content_id": "story-1"},
                "renderer_incompatible: shot 2: unsupported_action"
            ))
        self.assertEqual(make_plan.call_count, 1)

    def test_packet_is_review_only_and_never_an_approval_or_asset_receipt(self):
        with patch("studio_renderer.make_plan", return_value=[
            {"scene_id": "exact-scene", "visual": "forest"}
        ]):
            result = build_renderer_repair_gap(
                {"content_id": "story-1"},
                "renderer_incompatible: shot 1: unsupported_action"
            )
        self.assertFalse(result["publication_approval"])
        self.assertEqual(result["semantic_quality"], "not_verified")
        self.assertEqual(result["repair_status"], "manual_scene_and_art_review_required")
        self.assertNotIn("production_ready", result)
        self.assertNotIn("approval_receipt", result)
        self.assertNotIn("hmac", result)
        self.assertEqual(result["missing_shots"][0]["authored_context"]["review_only"], True)


if __name__ == "__main__":
    unittest.main()
