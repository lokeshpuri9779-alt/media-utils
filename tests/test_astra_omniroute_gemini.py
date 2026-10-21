"""Offline checks: free Gemini OmniRoute is opt-in and fails closed."""
import os
import unittest
from unittest.mock import patch
from astra_v2 import omniroute_gemini


class GeminiRouteTests(unittest.TestCase):
    def test_missing_key_disables_route(self):
        with patch.dict(os.environ, {"ASTRA_GEMINI_ENABLED": "1"}, clear=True):
            self.assertFalse(omniroute_gemini.enabled())
            self.assertIsNone(omniroute_gemini.generate(set(), set()))

    def test_explicit_enable_required(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}, clear=True):
            self.assertFalse(omniroute_gemini.enabled())

    def test_invalid_model_rejected_without_network(self):
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1",
            "ASTRA_GEMINI_MODEL": "../other"}, clear=True):
            with self.assertRaises(ValueError):
                omniroute_gemini.generate(set(), set())


if __name__ == "__main__":
    unittest.main()
