import os
import unittest
from unittest.mock import patch
from astra_v2 import omniroute, omniroute_gemini


class OmniRouteTests(unittest.TestCase):
    def test_subject_validation_does_not_import_pillow_or_renderer(self):
        import sys
        from astra_v2.openai_creative import visual_subject_matches
        with patch.dict(sys.modules, {"PIL": None}):
            self.assertTrue(visual_subject_matches(
                "fox", "A fox walks beside a forest stream."
            ))

    def test_all_story_providers_receive_real_scene_taxonomy_guidance(self):
        self.assertIn("background TAXONOMY", omniroute.PROMPT)
        self.assertIn("Do NOT mislabel grassland", omniroute.PROMPT)
        self.assertIn("story_environment", omniroute.PROMPT)
        self.assertIn("three genuinely different shots", omniroute.PROMPT)

    def test_all_provider_prompts_require_fast_suspense_and_fuller_narration(self):
        self.assertIn("cold-open", omniroute.PROMPT)
        self.assertIn("24-38 spoken words per beat", omniroute.PROMPT)
        self.assertIn("fair but surprising", omniroute.PROMPT)
        self.assertIn("consequence of each beat must directly cause the next beat", omniroute.PROMPT)
        self.assertIn("seed the twist clue before revealing it", omniroute.PROMPT)
        self.assertIn("rather than coincidence or a new object", omniroute.PROMPT)
        self.assertIn("consequence of each beat must directly cause the next beat's action", omniroute.PROMPT)
        self.assertIn("seed the twist clue before revealing it", omniroute.PROMPT)
        self.assertIn("rather than coincidence or a new object", omniroute.PROMPT)

    def test_prompts_require_dialogue_cliffhangers_and_grounded_sound(self):
        self.assertIn("brief, natural spoken line", omniroute.PROMPT)
        self.assertIn("stable personality trait", omniroute.PROMPT)
        self.assertIn("one immediate want", omniroute.PROMPT)
        self.assertIn("one pressure-triggered flaw", omniroute.PROMPT)
        self.assertIn("recognizable decision-making habit", omniroute.PROMPT)
        self.assertIn("what they avoid saying", omniroute.PROMPT)
        self.assertIn("generic inspirational lines and repeated catchphrases", omniroute.PROMPT)
        self.assertIn("change the relationship, reveal a motive or force a choice", omniroute.PROMPT)
        self.assertIn("distinct speech signature", omniroute.PROMPT)
        self.assertIn("distinguishable without dialogue tags", omniroute.PROMPT)
        self.assertIn("force a choice", omniroute.PROMPT)
        self.assertIn("speech signatures and relationships consistent", omniroute.PROMPT)
        self.assertIn("End beats one, two and", omniroute.PROMPT)
        self.assertIn("sound cues only when caused by visible action", omniroute.PROMPT)

    def test_generated_story_length_is_bounded_and_not_thin(self):
        from astra_v2.story_pacing import validate_generated_story
        beats = [{"speech": " ".join(["word"] * 25) + (" only then" if i < 2 else ".")}
                 for i in range(4)]
        beats[2]["speech"] = '"Stay close!" ' + beats[2]["speech"]
        result = validate_generated_story(beats)
        self.assertEqual(result["word_count"], 106)
        self.assertEqual(result["dialogue_beat_count"], 1)
        self.assertEqual(result["cliffhanger_beat_count"], 2)
        self.assertFalse(result["approval"])
        without_dialogue = [dict(beat) for beat in beats]
        without_dialogue[2]["speech"] = " ".join(["word"] * 25) + "."
        with self.assertRaisesRegex(ValueError, "dialogue line"):
            validate_generated_story(without_dialogue)
        without_hooks = [dict(beat) for beat in beats]
        without_hooks[0]["speech"] = " ".join(["word"] * 25) + "."
        without_hooks[1]["speech"] = " ".join(["word"] * 25) + "."
        with self.assertRaisesRegex(ValueError, "scene-ending hooks"):
            validate_generated_story(without_hooks)
        with self.assertRaisesRegex(ValueError, "24-38 words"):
            validate_generated_story([{"speech": "too short"}] * 4)

    def test_story_quality_requires_scene_and_subject_consistency(self):
        beats = [
            {"speech": "A curious fox discovers a bright blue feather beside the old forest stream.",
             "visual": "fox", "visual_prompt": "A curious fox studies a bright blue feather beside a forest stream.",
             "story_environment": "forest"},
            {"speech": "The fox follows the feather trail toward a quiet mossy clearing nearby.",
             "visual": "fox", "visual_prompt": "The fox follows a feather trail through the forest clearing.",
             "story_environment": "forest"},
            {"speech": "An owl notices the feather caught safely inside a low hanging branch.",
             "visual": "owl", "visual_prompt": "An owl looks at a blue feather caught in a low branch in the forest.",
             "story_environment": "forest"},
            {"speech": "The fox returns the feather to its nest before the evening rain arrives.",
             "visual": "fox", "visual_prompt": "A fox places the blue feather beside a nest in the forest.",
             "story_environment": "forest"},
        ]
        omniroute.validate_beat_quality(beats)
        unique = []
        for beat, visual, original in zip(
                beats, ("fox", "owl", "dog", "rabbit"),
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

    def test_gemini_scene_token_is_repaired_without_changing_natural_prompt(self):
        beat = {"story_environment": "forest",
                "visual_prompt": "A fox studies a glowing seed beside a quiet stream."}
        original = beat["visual_prompt"]
        omniroute_gemini._ensure_environment_token(beat)
        self.assertIn(original, beat["visual_prompt"])
        self.assertIn("Environment tag: forest.", beat["visual_prompt"])
        omniroute.validate_beat_quality([
            {"speech": "A curious fox follows the bright seed into the quiet forest clearing.",
             "visual": "fox", "visual_prompt": beat["visual_prompt"],
             "story_environment": "forest"},
            {"speech": "The fox finds the seed resting beneath a fern in the forest today.",
             "visual": "fox", "visual_prompt": "A fox finds a seed beneath a fern in the forest.",
             "story_environment": "forest"},
            {"speech": "An owl watches the seed glow softly among the forest roots nearby.",
             "visual": "owl", "visual_prompt": "An owl watches a glowing seed among forest roots.",
             "story_environment": "forest"},
            {"speech": "The fox returns the seed to the forest floor before dawn today.",
             "visual": "fox", "visual_prompt": "A fox places the seed on the forest floor.",
             "story_environment": "forest"},
        ])

    def test_gemini_scene_token_repair_rejects_conflicting_environment(self):
        beat = {"story_environment": "forest",
                "visual_prompt": "A fox crosses a busy city street beside tall buildings."}
        with self.assertRaisesRegex(ValueError, "conflicts with story_environment"):
            omniroute_gemini._ensure_environment_token(beat)

    def test_gemini_scene_token_repair_is_idempotent(self):
        beat = {"story_environment": "forest",
                "visual_prompt": "A fox waits quietly in the forest."}
        original = beat["visual_prompt"]
        omniroute_gemini._ensure_environment_token(beat)
        self.assertEqual(beat["visual_prompt"], original)

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
