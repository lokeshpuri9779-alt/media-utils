import os
import unittest
from unittest.mock import patch
from astra_v2.openai_creative import enabled, generate
from astra_v2.spending_policy import policy, assert_no_paid_api


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
            self.assertFalse(enabled())  # ₹0 policy overrides every opt-in flag

    def test_paid_request_is_blocked_even_with_key_and_flags(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test",
                                     "ASTRA_OPENAI_ENABLED": "1",
                                     "ASTRA_OPENAI_ALLOW_PAID_API": "1"}, clear=True):
            with patch("urllib.request.urlopen") as network:
                self.assertIsNone(generate(set(), set()))
                network.assert_not_called()

    def test_budget_is_zero_and_fail_closed(self):
        self.assertEqual(policy()["monthly_openai_budget_inr"], "0")
        self.assertFalse(policy()["paid_openai_allowed"])
        with self.assertRaises(PermissionError):
            assert_no_paid_api()


if __name__ == "__main__":
    unittest.main()
