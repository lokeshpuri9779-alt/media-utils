import os
import unittest
from unittest.mock import patch
from astra_v2.openai_creative import enabled, generate


class OpenAICreativeSafetyTests(unittest.TestCase):
    def test_off_by_default(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=True):
            self.assertFalse(enabled())
            self.assertIsNone(generate(set(), set()))

    def test_requires_both_explicit_flags(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test",
                                     "ASTRA_OPENAI_ENABLED": "1"}, clear=True):
            self.assertFalse(enabled())
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test",
                                     "ASTRA_OPENAI_ALLOW_PAID_API": "1"}, clear=True):
            self.assertFalse(enabled())

    def test_explicit_flags_and_key_enable(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test",
                                     "ASTRA_OPENAI_ENABLED": "1",
                                     "ASTRA_OPENAI_ALLOW_PAID_API": "1"}, clear=True):
            self.assertTrue(enabled())


if __name__ == "__main__":
    unittest.main()
