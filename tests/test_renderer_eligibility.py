"""Regression tests for unified renderer publication eligibility."""
import os
import unittest
from unittest.mock import patch

from astra_v2.renderer_eligibility import (
    check_renderer_eligibility, publication_renderer_rejection,
)


class RendererEligibilityTests(unittest.TestCase):
    def test_empty_plan_rejected(self):
        with patch("astra_v2.renderer_eligibility.make_plan", return_value=[]):
            ok, reason, modes = check_renderer_eligibility({"genre": "fiction"})
        self.assertFalse(ok)
        self.assertIn("Empty directed plan", reason)
        self.assertEqual(modes, ())

    def test_invalid_scene_rejected_with_index(self):
        shot = {"speech": "a story"}
        with patch("astra_v2.renderer_eligibility.make_plan", return_value=[shot]), \
             patch("astra_v2.renderer_eligibility.scene_layers", return_value={"draw_visual": True}), \
             patch("astra_v2.renderer_eligibility.validate_story_shot", side_effect=ValueError("bad cast")):
            ok, reason, _ = check_renderer_eligibility({"genre": "fiction"})
        self.assertFalse(ok)
        self.assertIn("shot 1: bad cast", reason)

    def test_compatible_scene_accepted(self):
        with patch("astra_v2.renderer_eligibility.make_plan", return_value=[{}]), \
             patch("astra_v2.renderer_eligibility.scene_layers", return_value={"draw_visual": True}), \
             patch("astra_v2.renderer_eligibility.validate_story_shot", return_value="solo"):
            self.assertEqual(check_renderer_eligibility({"genre": "fiction"}), (True, None, ("solo",)))

    def test_publication_gate_rechecks_queued_fiction(self):
        from astra_v2.publication_quality import publication_rejection
        story = {"genre": "fiction", "content_id": "story-1", "title": "A Story", "production_ready": True}
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}), \
             patch("astra_v2.renderer_eligibility.make_plan", return_value=[]):
            self.assertIn("renderer_incompatible", publication_rejection(story))

    def test_other_engine_not_blocked_by_unified_preflight(self):
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "0"}):
            self.assertIsNone(publication_renderer_rejection({"genre": "fiction"}))


if __name__ == "__main__":
    unittest.main()
