import unittest

from astra_v2.performance_short_contract import (
    SCENE_ROLES, premise_fingerprint, validate_short_outline
)


def sample_outline():
    roles = SCENE_ROLES
    prompts = [
        "A tiny fox discovers a glass jar glowing under moonlight.",
        "The fox sees a firefly trapped inside the glass jar.",
        "The fox nudges the glass jar toward a flat stone.",
        "The jar rolls toward a shallow stream and the firefly flickers.",
        "The fox notices a loose cork beside the glass jar.",
        "The fox removes the cork and opens the glass jar.",
        "The firefly flies free and lights the fox's path home.",
    ]
    scenes = []
    for i, role in enumerate(roles):
        scenes.append({
            "role": role,
            "duration_seconds": 4.5,
            "narration": f"Scene {i+1} advances the rescue with a clear consequence.",
            "action": f"The fox performs a visible action for {role}.",
            "visual_prompt": prompts[i],
            "camera": "clear medium shot with readable subject action",
            "environment": "moonlit forest clearing",
            "required_props": ["glass jar"] if i in (0, 1, 2, 3, 5) else [],
            "transition_question": "What will happen next?" if i < 6 else "",
        })
    return {
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

    def test_rejects_four_beat_legacy_story(self):
        outline = sample_outline()
        outline["scenes"] = outline["scenes"][:4]
        with self.assertRaisesRegex(ValueError, "exactly_seven"):
            validate_short_outline(outline)

    def test_rejects_missing_required_prop_in_visual_prompt(self):
        outline = sample_outline()
        outline["scenes"][2]["visual_prompt"] = "A tiny fox nudges an empty wooden box."
        with self.assertRaisesRegex(ValueError, "required_prop_not_in_visual_prompt"):
            validate_short_outline(outline)

    def test_rejects_repeated_causal_mechanism_even_with_new_characters(self):
        outline = sample_outline()
        fp = premise_fingerprint(outline["premise"])
        with self.assertRaisesRegex(ValueError, "repeated_underlying_plot_mechanism"):
            validate_short_outline(outline, history=[fp])

    def test_rejects_duration_outside_short_target(self):
        outline = sample_outline()
        outline["scenes"][0]["duration_seconds"] = 7.0
        with self.assertRaisesRegex(ValueError, "duration_out_of_range"):
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
