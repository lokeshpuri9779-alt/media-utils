import os
import unittest
from unittest.mock import patch
from astra_v2 import omniroute


class OmniRouteTests(unittest.TestCase):
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
