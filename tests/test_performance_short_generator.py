import io
import json
import os
import unittest
from unittest.mock import patch

from astra_v2.performance_short_generator import _prompt, _schema, generate
from astra_v2.performance_short_contract import SCENE_ROLES


def valid_payload():
    prompts = [
        "A fox discovers a glass jar glowing under moonlight in the forest.",
        "The fox sees a firefly trapped inside the glass jar in the forest.",
        "The fox nudges the glass jar toward a flat stone in the forest.",
        "The fox watches as the glass jar rolls toward a shallow stream and the firefly flickers in the forest.",
        "The fox notices a loose cork beside the glass jar in the forest.",
        "The fox removes the cork and opens the glass jar in the forest.",
        "The firefly flies free and lights the fox's path home through the forest.",
    ]
    scenes = []
    for i, role in enumerate(SCENE_ROLES):
        scenes.append({
            "role": role, "duration_seconds": 4.5,
            "narration": f"Scene {i+1} changes the rescue in a visible way.",
            "speech": f"Scene {i+1} changes the rescue in a visible way.",
            "headline": f"RESCUE BEAT {i+1}", "visual": "fox",
            "label": "ORIGINAL STORY", "story_environment": "forest",
            "story_beat": "reveal" if i == 0 else "payoff" if i == 6 else "build",
            "action": f"The fox performs a clear action during the {role} scene.",
            "visual_prompt": prompts[i],
            "camera": "Medium shot, clear readable subject action",
            "environment": "moonlit forest clearing",
            "required_props": ["glass jar"] if i in (0, 1, 2, 3, 5) else [],
            "transition_question": "What happens next?" if i < 6 else "",
        })
    return {
        "title": "The Firefly in the Jar",
        "question": "Can the fox free the firefly before the jar reaches the stream?",
        "answer": "The fox spots the loose cork and opens the jar.",
        "premise": {
            "central_conflict": "A firefly is trapped inside a sealed glass jar",
            "failed_attempt": "The fox pushes the jar and it rolls toward water",
            "causal_discovery": "A loose cork is the only thing sealing the jar",
            "resolution": "The fox removes the cork and frees the firefly",
        },
        "scenes": scenes,
        "scorecard": {
            "originality": 22, "hook": 18, "emotional_payoff": 14,
            "progression": 14, "visual_clarity": 14, "audience_fit": 9,
        },
        "hard_failures": [],
    }


class PerformanceShortGeneratorTests(unittest.TestCase):
    def test_schema_requires_exactly_seven_scenes(self):
        schema = _schema()
        self.assertEqual(schema["properties"]["scenes"]["minItems"], 7)
        self.assertEqual(schema["properties"]["scenes"]["maxItems"], 7)

    def test_prompt_includes_recent_story_exclusions_and_new_plot_rule(self):
        prompt = _prompt([{"title": "Earlier tale", "central_conflict": "A bell went missing"}])
        self.assertIn("Earlier tale", prompt)
        self.assertIn("different cause-and-effect chain", prompt)
        self.assertIn("required_props", prompt)

    def test_generator_returns_review_only_candidate(self):
        payload = valid_payload()
        response = {"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": json.dumps(payload)}]
        }}]}
        with patch.dict(os.environ, {"ASTRA_GEMINI_ENABLED": "1", "GEMINI_API_KEY": "test-key",
                                     "ASTRA_GEMINI_MODEL": "gemini-test"}, clear=False):
            with patch("astra_v2.performance_short_generator.urllib.request.urlopen",
                       return_value=io.BytesIO(json.dumps(response).encode())) as mocked:
                story = generate()
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(len(story["performance_scenes"]), 7)
        self.assertEqual(len(story["story_beats"]), 7)
        self.assertFalse(story["production_ready"])
        self.assertFalse(story["approved"])
        self.assertFalse(story["eligible_for_automatic_publishing"])
        self.assertFalse(story["published"])
        self.assertEqual(story["format_profile"], "shorts_v2_7scene")

    def test_generator_stays_off_without_explicit_enablement(self):
        with patch.dict(os.environ, {"ASTRA_GEMINI_ENABLED": "0"}, clear=False):
            self.assertIsNone(generate())


if __name__ == "__main__":
    unittest.main()
