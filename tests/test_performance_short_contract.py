import unittest
import json
from pathlib import Path

from astra_v2.story_planning import planning_issues

from astra_v2.performance_short_contract import (
    SCENE_ROLES, premise_fingerprint, renderer_outline_from_story, to_renderer_beats, validate_rendered_duration, validate_short_outline
)


def sample_outline():
    prompts = [
        "A tiny fox discovers a glass jar glowing under moonlight in the forest. Character: a small russet fox with a white chest and amber eyes.",
        "The fox sees a firefly trapped inside the glass jar in the forest. Character: a small russet fox with a white chest and amber eyes.",
        "The fox nudges the glass jar toward a flat stone in the forest. Character: a small russet fox with a white chest and amber eyes.",
        "The fox watches as the glass jar rolls toward a shallow stream and the firefly flickers in the forest. Character: a small russet fox with a white chest and amber eyes.",
        "The fox notices a loose cork beside the glass jar in the forest. Character: a small russet fox with a white chest and amber eyes.",
        "The fox removes the cork and opens the glass jar in the forest. Character: a small russet fox with a white chest and amber eyes.",
        "The firefly flies free and lights the fox's path home through the forest. Character: a small russet fox with a white chest and amber eyes.",
    ]
    scenes = []
    for i, role in enumerate(SCENE_ROLES):
        scenes.append({
            "role": role,
            "duration_seconds": 4.5,
            "narration": f"Scene {i+1} advances the rescue with a clear consequence.",
            "speech": f"Scene {i+1} advances the rescue with a clear consequence.",
            "headline": f"RESCUE BEAT {i+1}",
            "visual": "fox",
            "label": "ORIGINAL STORY",
            "story_environment": "forest",
            "story_beat": "reveal" if i == 0 else "payoff" if i == 6 else "build",
            "action": ["looks", "watches", "pushes", "catches", "looks", "opens", "runs"][i],
            "visual_prompt": prompts[i],
            "camera": "clear medium shot with readable subject action",
            "environment": "moonlit forest clearing",
            "required_props": ["glass jar"] if i in (0, 1, 2, 3, 5) else [],
            "story_prop": "none",
            "transition_question": "What will happen next?" if i < 6 else "",
        })
    return {
        "character_bible": "a small russet fox with a white chest and amber eyes",
        "premise": {
            "central_conflict": "a firefly is trapped inside a sealed glass jar",
            "failed_attempt": "the fox pushes the jar but it rolls toward water",
            "causal_discovery": "a loose cork is the only thing sealing the jar",
            "resolution": "the fox removes the cork and frees the firefly",
        },
        "scenes": scenes,
        "scorecard": {
            "originality": 22, "hook": 18, "emotional_payoff": 14,
            "progression": 14, "visual_clarity": 14, "audience_fit": 9,
        },
        "hard_failures": [],
    }


class PerformanceShortContractTests(unittest.TestCase):
    def test_accepts_seven_scene_short_but_never_approves_it(self):
        result = validate_short_outline(sample_outline())
        self.assertTrue(result["valid"])
        self.assertEqual(result["scene_count"], 7)
        self.assertEqual(result["duration_seconds"], 31.5)
        self.assertFalse(result["approved"])
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["published"])

    def test_rejects_scene_without_a_renderer_supported_action(self):
        outline = sample_outline()
        outline["scenes"][3]["action"] = "The fox performs a visible action."
        with self.assertRaisesRegex(ValueError, "scene_4_action_not_animatable"):
            validate_short_outline(outline)

    def test_render_fixture_is_a_valid_seven_scene_story_with_explicit_props(self):
        story = json.loads(Path("tests/fixtures/performance_short_preview.json").read_text())
        outline = renderer_outline_from_story(story)
        result = validate_short_outline(outline)
        self.assertTrue(result["valid"])
        self.assertEqual(result["scene_count"], 7)
        beats = to_renderer_beats(outline)
        self.assertEqual([beat["story_prop"] for beat in beats],
                         ["lantern", "lantern", "key", "key", "box", "key", "box"])
        self.assertFalse(story["approved"])
        self.assertFalse(story["production_ready"])
        self.assertFalse(story["published"])

    def test_persisted_candidate_fields_normalize_for_studio_renderer(self):
        outline = sample_outline()
        story = {
            "premise": outline["premise"],
            "character_bible": outline["character_bible"],
            "performance_scenes": outline["scenes"],
            "performance_scorecard": outline["scorecard"],
            "performance_hard_failures": [],
        }
        normalized = renderer_outline_from_story(story)
        self.assertEqual(validate_short_outline(normalized)["scene_count"], 7)
        self.assertEqual(len(to_renderer_beats(normalized)), 7)

    def test_adapts_to_seven_studio_scenes_without_approval(self):
        beats = to_renderer_beats(sample_outline())
        self.assertEqual(len(beats), 7)
        self.assertEqual(beats[0]["duration"], 4.5)
        self.assertEqual(beats[0]["story_beat"], "reveal")
        self.assertEqual(beats[-1]["story_beat"], "payoff")

    def test_story_planning_accepts_seven_scene_performance_record(self):
        outline = sample_outline()
        beats = to_renderer_beats(outline)
        record = {
            "performance_scenes": outline["scenes"],
            "story_beats": beats,
        }
        self.assertEqual(planning_issues(record), [])

    def test_explicit_supported_prop_is_carried_to_renderer(self):
        outline = sample_outline()
        outline["scenes"][0]["visual_prompt"] += " beside a brass lantern."
        outline["scenes"][0]["required_props"].append("lantern")
        outline["scenes"][0]["story_prop"] = "lantern"
        beats = to_renderer_beats(outline)
        self.assertEqual(beats[0]["story_prop"], "lantern")
        self.assertEqual(beats[1]["story_prop"], "none")

    def test_unsupported_or_invisible_explicit_prop_is_rejected(self):
        outline = sample_outline()
        outline["scenes"][0]["story_prop"] = "glass_jar"
        with self.assertRaisesRegex(ValueError, "story_prop_unsupported"):
            validate_short_outline(outline)
        outline = sample_outline()
        outline["scenes"][0]["story_prop"] = "lantern"
        with self.assertRaisesRegex(ValueError, "story_prop_not_visible"):
            validate_short_outline(outline)

    def test_actual_rendered_duration_is_hard_limited(self):
        validate_rendered_duration(31.5)
        validate_rendered_duration(28)
        validate_rendered_duration(40)
        with self.assertRaisesRegex(ValueError, "rendered_duration_out_of_range"):
            validate_rendered_duration(40.1)
        with self.assertRaisesRegex(ValueError, "rendered_duration_out_of_range"):
            validate_rendered_duration(27.9)

    def test_rejects_four_beat_legacy_story(self):
        outline = sample_outline()
        outline["scenes"] = outline["scenes"][:4]
        with self.assertRaisesRegex(ValueError, "exactly_seven"):
            validate_short_outline(outline)

    def test_rejects_missing_required_prop_in_visual_prompt(self):
        outline = sample_outline()
        outline["scenes"][2]["visual_prompt"] = "A small russet fox with a white chest and amber eyes nudges an empty wooden box in the forest."
        with self.assertRaisesRegex(ValueError, "required_prop_not_in_visual_prompt"):
            validate_short_outline(outline)

    def test_rejects_repeated_causal_mechanism_even_with_new_characters(self):
        outline = sample_outline()
        fp = premise_fingerprint(outline["premise"])
        with self.assertRaisesRegex(ValueError, "repeated_underlying_plot_mechanism"):
            validate_short_outline(outline, history=[fp])

    def test_rejects_duration_outside_short_target(self):
        outline = sample_outline()
        for scene in outline["scenes"]:
            scene["duration_seconds"] = 7.0
        with self.assertRaisesRegex(ValueError, "short_duration_out_of_range"):
            validate_short_outline(outline)

    def test_rejects_low_score_and_hard_failures(self):
        outline = sample_outline()
        outline["scorecard"]["originality"] = 5
        outline["hard_failures"] = ["duplicate plot"]
        result = validate_short_outline(outline)
        self.assertFalse(result["valid"])
        self.assertFalse(result["approved"])


if __name__ == "__main__":
    unittest.main()
