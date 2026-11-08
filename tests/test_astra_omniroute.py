import os
import unittest
from unittest.mock import patch
from astra_v2 import omniroute


class OmniRouteTests(unittest.TestCase):
    def test_all_story_providers_receive_real_scene_taxonomy_guidance(self):
        self.assertIn("background TAXONOMY", omniroute.PROMPT)
        self.assertIn("Do NOT mislabel grassland", omniroute.PROMPT)
        self.assertIn("story_environment", omniroute.PROMPT)

    def test_story_quality_requires_scene_and_subject_consistency(self):
        beats = [
            {"speech": "A curious fox discovers a bright blue feather beside the old forest stream.",
             "visual": "fox", "visual_prompt": "A curious fox studies a bright blue feather beside a forest stream.",
             "story_environment": "forest"},
            {"speech": "The fox follows the feather trail toward a quiet mossy clearing nearby.",
             "visual": "fox", "visual_prompt": "The fox follows a feather trail through the forest clearing.",
             "story_environment": "forest"},
            {"speech": "An owl notices the feather caught safely inside a low hanging branch.",
             "visual": "owl", "visual_prompt": "An owl looks at a blue feather caught in a low branch.",
             "story_environment": "forest"},
            {"speech": "The fox returns the feather to its nest before the evening rain arrives.",
             "visual": "fox", "visual_prompt": "A fox places the blue feather beside a nest in the forest.",
             "story_environment": "forest"},
        ]
        omniroute.validate_beat_quality(beats)
        unique = []
        for beat, visual, original in zip(
                beats, ("fox", "owl", "duck", "rabbit"),
                ("fox", "fox", "owl", "fox")):
            unique.append({**beat, "visual": visual,
                           "visual_prompt": beat["visual_prompt"].replace(original, visual)})
        with self.assertRaisesRegex(ValueError, "at most two animal"):
            omniroute.validate_beat_quality(unique)
        with self.assertRaisesRegex(ValueError, "does not match"):
            omniroute.validate_beat_quality([{**beat, "visual": "owl"}
                if index == 0 else beat for index, beat in enumerate(beats)])
        third_species = [{**beat, "speech": beat["speech"] + " A rabbit watches nearby."}
                         if index == 0 else beat for index, beat in enumerate(beats)]
        with self.assertRaisesRegex(ValueError, "third animal species"):
            omniroute.validate_beat_quality(third_species)
        with self.assertRaisesRegex(ValueError, "story_environment"):
            omniroute.validate_beat_quality([{**beat, "story_environment": "unknown"}
                if index == 0 else beat for index, beat in enumerate(beats)])
        with self.assertRaisesRegex(ValueError, "must appear in visual_prompt"):
            omniroute.validate_beat_quality([{**beat, "story_environment": "city"}
                if index == 0 else beat for index, beat in enumerate(beats)])
        with self.assertRaisesRegex(ValueError, "12 words"):
            omniroute.validate_beat_quality([{**beat, "speech": "Too short narration."}
                if index == 0 else beat for index, beat in enumerate(beats)])

    def test_disabled_without_provider_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(omniroute.enabled())
            self.assertIsNone(omniroute.generate(set(), set()))

    def test_openrouter_paid_model_rejected(self):
        with patch.dict(os.environ, {
            "ASTRA_OPENROUTER_ENABLED": "1", "OPENROUTER_API_KEY": "test",
            "ASTRA_OMNIROUTE_ORDER": "openrouter",
            "ASTRA_OPENROUTER_MODEL": "some/model"}, clear=True):
            with self.assertRaises(RuntimeError):
                omniroute.generate(set(), set())

    def test_groq_not_called_without_secret(self):
        with patch.dict(os.environ, {"ASTRA_GROQ_ENABLED": "1"}, clear=True):
            self.assertFalse(omniroute.enabled())


if __name__ == "__main__":
    unittest.main()
