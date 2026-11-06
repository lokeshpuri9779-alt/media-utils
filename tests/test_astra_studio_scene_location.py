"""Offline Studio scene-location regression; no render, model, or publication."""
import json
import os
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from studio_renderer import make_plan
from astra_v2.visual_artifact_backdrop import analyze_story_scene


def shot(speech, visual, prompt=None, **extra):
    value = {"headline": "Story beat", "speech": speech,
             "visual": visual, "story_beat": "build", "label": ""}
    if prompt is not None:
        value["visual_prompt"] = prompt
    value.update(extra)
    return value


def planned(beats, **story_details):
    story = {"genre": "fiction", "content_id": "offline-location-test",
             "title": "The Owl and the Clock", "story_beats": beats,
             **story_details}
    snapshot = json.dumps(beats, sort_keys=True)
    # Exercise the REAL make_plan scene-selection logic, isolating unrelated
    # creative-format and actor/render side effects.
    with ExitStack() as patches:
        patches.enter_context(patch.dict(os.environ, {
            "ASTRA_UNIFIED_STORY_ENGINE": "0"}))
        patches.enter_context(patch(
            "studio_renderer.direct_story", side_effect=lambda story, rows: rows))
        patches.enter_context(patch(
            "creative_formats.choose_format", return_value={"name": "test"}))
        patches.enter_context(patch(
            "creative_formats.apply_format", side_effect=lambda rows, fmt: rows))
        patches.enter_context(patch(
            "astra_v2.pillow_duo_scene.scene_pair", return_value=()))
        patches.enter_context(patch(
            "astra_v2.pillow_duo_scene.infer_story_prop", return_value=None))
        patches.enter_context(patch(
            "astra_v2.directed_scene_contract.named_human_characters",
            return_value=()))
        patches.enter_context(patch(
            "studio_renderer.select_subject", return_value=None))
        patches.enter_context(patch(
            "studio_renderer.choose_action", return_value="idle"))
        patches.enter_context(patch(
            "astra_v2.prop_state_continuity.assign_prop_states",
            side_effect=lambda rows: rows))
        plan = make_plan(story)
    assert json.dumps(beats, sort_keys=True) == snapshot
    return plan


class StudioAuthoredSceneLocationTests(unittest.TestCase):
    def test_opening_visual_prompt_sets_real_scene_not_generic_visual_label(self):
        plan = planned([
            shot("The owl examines a strange ticking object.", "signal",
                 "An owl stands in a stone observatory with a brass clock."),
            shot("It turns the clock slowly in its wings.", "door",
                 "The owl examines its clock beside a wooden table."),
        ])
        self.assertEqual([s["story_environment"] for s in plan],
                         ["observatory", "observatory"])
        self.assertTrue(all(analyze_story_scene(s)["scene"] == "observatory"
                            for s in plan))

    def test_explicit_later_visual_location_overrides_opening_fallback(self):
        plan = planned([
            shot("An owl discovers the puzzle.", "signal",
                 "An owl stands inside the observatory."),
            shot("It follows the clue.", "forest",
                 "The owl walks through a flower garden."),
            shot("The owl examines the result.", "door",
                 "The owl watches the clock beside a table."),
        ])
        self.assertEqual([s["story_environment"] for s in plan],
                         ["observatory", "garden", "observatory"])
        self.assertEqual([analyze_story_scene(s)["scene"] for s in plan],
                         ["observatory", "garden", "observatory"])

    def test_explicit_beat_setting_is_authoritative_over_visual_prompt(self):
        plan = planned([
            shot("The owl continues thinking.", "signal",
                 "The owl is pictured on a harbor dock.",
                 story_environment="library"),
        ], story_environment="village")
        self.assertEqual(plan[0]["story_environment"], "library")
        self.assertEqual(analyze_story_scene(plan[0])["scene"], "library")

    def test_legacy_visual_label_still_supplies_opening_setting_when_prompt_missing(self):
        plan = planned([
            shot("The rabbit reads the warning.", "forest"),
            shot("The rabbit checks the evidence.", "signal"),
        ])
        self.assertEqual([s["story_environment"] for s in plan],
                         ["forest", "forest"])

    def test_location_selection_is_not_editorial_or_publication_approval(self):
        plan = planned([shot("The owl looks around.", "signal",
                            "An owl inside the library.")])
        self.assertEqual(plan[0]["story_environment"], "library")
        self.assertFalse(any("approved_for_publication" in s or
                             "editorial_approval" in s for s in plan))


if __name__ == "__main__":
    unittest.main()
