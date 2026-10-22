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


    def test_missing_primary_model_uses_free_fallback(self):
        import io
        import json
        import urllib.error
        from unittest.mock import Mock
        requested = []
        def fake_urlopen(request, timeout):
            requested.append(request.full_url)
            if "gemini-3.1-flash-lite" in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)
            return io.BytesIO(json.dumps({"candidates": []}).encode())
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1",
            "ASTRA_GEMINI_MODEL": "gemini-3.1-flash-lite",
            "ASTRA_GEMINI_FALLBACK_MODEL": "gemini-2.5-flash-lite",
        }, clear=True), patch.object(omniroute_gemini.urllib.request, "urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(ValueError, "no candidates"):
                omniroute_gemini.generate(set(), set())
        self.assertEqual(len(requested), 2)
        self.assertIn("gemini-2.5-flash-lite", requested[-1])

    def test_authentication_error_never_falls_back(self):
        import urllib.error
        requested = []
        def fake_urlopen(request, timeout):
            requested.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 403, "forbidden", {}, None)
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1",
            "ASTRA_GEMINI_MODEL": "gemini-3.1-flash-lite",
            "ASTRA_GEMINI_FALLBACK_MODEL": "gemini-2.5-flash-lite",
        }, clear=True), patch.object(omniroute_gemini.urllib.request, "urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(RuntimeError, "Gemini HTTP 403"):
                omniroute_gemini.generate(set(), set())
        self.assertEqual(len(requested), 1)

if __name__ == "__main__":
    unittest.main()
