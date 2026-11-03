"""Regression tests for unified renderer publication eligibility."""
import os
import unittest
from unittest.mock import patch

from astra_v2.renderer_eligibility import (
    check_renderer_eligibility, publication_renderer_rejection,
)


class RendererEligibilityTests(unittest.TestCase):
    def test_empty_plan_rejected(self):
        with patch("studio_renderer.make_plan", return_value=[]):
            ok, reason, modes = check_renderer_eligibility({"genre": "fiction"})
        self.assertFalse(ok)
        self.assertIn("Empty directed plan", reason)
        self.assertEqual(modes, ())

    def test_invalid_scene_rejected_with_index(self):
        shot = {"speech": "a story"}
        with patch("studio_renderer.make_plan", return_value=[shot]), \
             patch("astra_v2.layer_contract.scene_layers", return_value={"draw_visual": True}), \
             patch("astra_v2.unified_story_engine.validate_story_shot", side_effect=ValueError("bad cast")):
            ok, reason, _ = check_renderer_eligibility({"genre": "fiction"})
        self.assertFalse(ok)
        self.assertIn("shot 1: bad cast", reason)

    def test_compatible_scene_accepted(self):
        with patch("studio_renderer.make_plan", return_value=[{}]), \
             patch("astra_v2.layer_contract.scene_layers", return_value={"draw_visual": True}), \
             patch("astra_v2.unified_story_engine.validate_story_shot", return_value="solo"):
            self.assertEqual(check_renderer_eligibility({"genre": "fiction"}), (True, None, ("solo",)))

    def test_publication_gate_rechecks_queued_fiction(self):
        from astra_v2.publication_quality import publication_rejection
        story = {"genre": "fiction", "content_id": "story-1", "title": "A Story", "production_ready": True}
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}), \
             patch("studio_renderer.make_plan", return_value=[]):
            self.assertIn("renderer_incompatible", publication_rejection(story))

    def test_weaver_fiction_rejected_at_independent_and_publication_preflight(self):
        # Structural review must fail before voice/video generation; the
        # publisher rechecks the same eligibility even for queued candidates.
        from astra_v2.publication_quality import publication_rejection
        title = "The Weaver's Choice at Bramble Mill"
        story = {"genre": "fiction", "kind": "authored_causal_story",
                 "content_id": "rayvan-gemini-regression-weaver",
                 "title": title, "production_ready": True}
        shot = {"story_title": title, "visual": "forest",
                "visual_prompt": "Bram and Thomas hold the lantern at the village mill.",
                "speech": "We must protect our wool bales before the river rises."}
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}), \
             patch("studio_renderer.make_plan", return_value=[shot]):
            eligible, reason, modes = check_renderer_eligibility(story)
            self.assertFalse(eligible)
            self.assertIn("human_actor_not_supported_by_directed_icons", reason)
            self.assertEqual(modes, ())
            self.assertIn("renderer_incompatible", publication_rejection(story))

    def test_animal_cast_cannot_hide_a_miller_in_same_scene(self):
        from astra_errors import CreativeReject
        from astra_v2.unified_story_engine import validate_story_shot, draw_story_frame
        shot = {
            "story_title": "The Fox and the Miller",
            "story_cast": ("fox",),
            "visual": "forest",
            "speech": "The fox helps the miller lift the jammed sluice.",
            "visual_prompt": "Fox and miller heave the gate into place together.",
        }
        with self.assertRaisesRegex(CreativeReject, "human_actor_not_supported"):
            validate_story_shot(shot)
        directed = unittest.mock.Mock()
        with self.assertRaises(CreativeReject):
            draw_story_frame(object(), shot, 0.5, draw_directed=directed,
                             global_time=0.5, accent=(100, 100, 100))
        directed.assert_not_called()

    def test_two_supported_animals_cannot_hide_a_doctor(self):
        from astra_errors import CreativeReject
        from astra_v2.unified_story_engine import validate_story_shot
        shot = {"story_title": "The Fox and Rabbit Aid the Doctor",
                "story_cast": ("fox", "rabbit"), "visual": "forest",
                "speech": "The fox and rabbit carry the doctor's medicine.",
                "visual_prompt": "The doctor gives the medicine to the two animals."}
        with self.assertRaisesRegex(CreativeReject, "human_actor_not_supported"):
            validate_story_shot(shot)

    def test_named_human_in_bible_still_blocks_animal_puppet(self):
        from astra_errors import CreativeReject
        from astra_v2.unified_story_engine import validate_story_shot
        shot = {"story_title": "The Fox's Promise",
                "story_cast": ("fox",), "visual": "forest",
                "story_named_humans": ("Thomas",),
                "visual_prompt": "Thomas carries a box as the fox follows."}
        with self.assertRaisesRegex(CreativeReject, "human_actor_not_supported"):
            validate_story_shot(shot)

    def test_animal_wardrobe_action_requires_verified_art(self):
        from astra_errors import CreativeReject
        from astra_v2.unified_story_engine import validate_story_shot
        shot = {"story_title": "The Fox's Coat",
                "story_cast": ("fox",), "visual": "forest",
                "visual_prompt": "The fox wears a green coat and holds a copper hammer."}
        with self.assertRaisesRegex(CreativeReject, "embodied_character_not_supported"):
            validate_story_shot(shot)

    def test_recorded_pip_railway_story_mechanics_rejected_before_render(self):
        """Real decoded MP4 sample showed mouse, not narrated gearbox work.

        This tests scene capability, NOT the visual semantics of a full MP4.
        """
        from astra_errors import CreativeReject
        from astra_v2.unified_story_engine import validate_story_shot
        shots = [
            {
                "story_title": "Pip and the Midnight Railway Signal",
                "story_cast": ("mouse",), "visual": "forest",
                "speech": "Oh dear, the signal lever is utterly stuck!",
                "visual_prompt": "Pip the mouse looks at the stuck iron signal lever.",
            },
            {
                "story_title": "Pip and the Midnight Railway Signal",
                "story_cast": ("mouse",), "visual": "door",
                "speech": "If I jam this wrench into the gear teeth, it will break free.",
                "visual_prompt": "Pip the mouse shoving a brass wrench into the iron gear box.",
            },
        ]
        for shot in shots:
            with self.subTest(prompt=shot["visual_prompt"]):
                with self.assertRaisesRegex(
                    CreativeReject, "unsupported_mechanical_rig_action_requires_scene_art"
                ):
                    validate_story_shot(shot)

    def test_pip_mechanical_rig_rejected_by_publication_preflight(self):
        from astra_v2.publication_quality import publication_rejection
        story = {
            "content_id": "pip-rig-regression", "genre": "fiction",
            "kind": "authored_causal_story", "title": "Pip and the Midnight Railway Signal",
            "production_ready": True,
        }
        shot = {
            "story_title": story["title"], "story_cast": ("mouse",),
            "speech": "The switch is jammed and the gears cannot turn.",
            "visual_prompt": "Pip the mouse shoving a wrench into the signal lever.",
            "visual": "forest",
        }
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}), \
             patch("studio_renderer.make_plan", return_value=[shot]), \
             patch("astra_v2.layer_contract.scene_layers",
                   return_value={"draw_visual": True}):
            eligible, reason, modes = check_renderer_eligibility(story)
            rejection = publication_rejection(story)
        self.assertFalse(eligible)
        self.assertIn("unsupported_mechanical_rig_action_requires_scene_art", reason)
        self.assertEqual(modes, ())
        self.assertIn("renderer_incompatible", rejection)

    def test_simple_animal_wrench_and_signal_are_still_eligible(self):
        from astra_v2.unified_story_engine import validate_story_shot
        examples = (
            {"story_cast": ("mouse",), "visual": "forest",
             "speech": "The mouse carries a brass wrench toward the garden.",
             "visual_prompt": "A mouse walking with a wrench."},
            {"story_cast": ("fox",), "visual": "forest",
             "speech": "The radio signal rises as the fox watches the moon.",
             "visual_prompt": "A fox watches a lantern glow."},
            {"story_cast": ("owl",), "visual": "forest",
             "speech": "The owl notices a stationary old gear without touching it.",
             "visual_prompt": "An owl watches a motionless clock."},
        )
        for shot in examples:
            with self.subTest(shot=shot["speech"]):
                self.assertEqual(validate_story_shot(shot), "solo")

    def test_verified_mechanical_scene_art_routes_to_directed(self):
        from astra_v2.unified_story_engine import validate_story_shot
        shot = {
            "story_cast": ("mouse",), "visual": "forest",
            "speech": "The signal lever is stuck.",
            "visual_prompt": "Pip the mouse pushes the rusty signal lever.",
        }
        with patch("astra_v2.directed_scene_contract.validate_directed_scene",
                   return_value=None) as art:
            self.assertEqual(validate_story_shot(shot), "directed")
        art.assert_called_once_with(shot)

    def test_valid_supported_animal_puppet_unchanged(self):
        from astra_v2.unified_story_engine import validate_story_shot
        self.assertEqual(validate_story_shot({
            "story_title": "The Fox's Clock", "story_cast": ("fox",),
            "visual": "forest", "speech": "The fox looks at a ticking clock."
        }), "solo")
        self.assertEqual(validate_story_shot({
            "story_title": "The Fox and the Rabbit",
            "story_cast": ("fox", "rabbit"), "visual": "forest",
            "speech": "The fox and the rabbit look at the river."
        }), "duo")

    def test_verified_scene_art_routes_mixed_cast_to_directed_not_solo(self):
        from astra_v2.unified_story_engine import validate_story_shot
        shot = {"story_title": "The Fox and the Miller",
                "story_cast": ("fox",), "visual": "forest",
                "speech": "The miller and the fox lift the gate."}
        with patch("astra_v2.directed_scene_contract.validate_directed_scene",
                   return_value=None) as verified:
            mode = validate_story_shot(shot)
        self.assertEqual(mode, "directed")
        verified.assert_called_once_with(shot)

    def test_mixed_cast_is_rechecked_at_publication_boundary(self):
        from astra_v2.publication_quality import publication_rejection
        shot = {"story_title": "The Fox and the Miller",
                "story_cast": ("fox",), "visual": "forest",
                "speech": "The fox brings tools to the miller."}
        story = {"content_id": "mixed-cast-test", "title": "The Fox and the Miller",
                 "genre": "fiction", "production_ready": True}
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}), \
             patch("studio_renderer.make_plan", return_value=[shot]), \
             patch("astra_v2.layer_contract.scene_layers",
                   return_value={"draw_visual": True}):
            eligible, reason, _ = check_renderer_eligibility(story)
            rejection = publication_rejection(story)
        self.assertFalse(eligible)
        self.assertIn("human_actor_not_supported", reason)
        self.assertIn("renderer_incompatible", rejection)

    def test_reviewed_human_renderer_path_stays_separate(self):
        from astra_v2.unified_story_engine import validate_story_shot
        shot = {"story_human_actor": "mara", "story_cast": ("fox",),
                "story_title": "Mara Meets the Fox",
                "visual_prompt": "Mara takes the fox's lantern."}
        with patch("astra_v2.human_story_performance.validate_human_scene",
                   return_value="human") as allowed:
            self.assertEqual(validate_story_shot(shot), "human")
        allowed.assert_called_once_with(shot)

    def test_other_engine_not_blocked_by_unified_preflight(self):
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "0"}):
            self.assertIsNone(publication_renderer_rejection({"genre": "fiction"}))


if __name__ == "__main__":
    unittest.main()
