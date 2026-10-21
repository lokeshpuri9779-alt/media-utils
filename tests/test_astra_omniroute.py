import os
import unittest
from unittest.mock import patch
from astra_v2 import omniroute


class OmniRouteTests(unittest.TestCase):
    def test_story_quality_requires_detail_and_visual_variety(self):
        beats = [
            {"speech": "A curious astronaut discovers an unusual signal beyond the quiet planet.", "visual": "planet"},
            {"speech": "A small repair robot follows the signal through an abandoned station.", "visual": "robot"},
            {"speech": "The signal reveals that the station is protecting a lost forest.", "visual": "forest"},
            {"speech": "The astronaut restores the signal and helps the forest awaken again.", "visual": "signal"},
        ]
        omniroute.validate_beat_quality(beats)
        with self.assertRaisesRegex(ValueError, "three distinct visual"):
            omniroute.validate_beat_quality([{**beat, "visual": "planet"} for beat in beats])
        with self.assertRaisesRegex(ValueError, "12 words"):
            omniroute.validate_beat_quality([{**beat, "speech": "Too short narration."} for beat in beats])

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
