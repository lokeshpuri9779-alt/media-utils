"""Offline regression checks for Gemini artwork quota handling."""
import io
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from astra_v2.gemini_art_staging import generate_staged_art

STORY = {"content_id": "quota-test", "story_beats": [{"scene_id": "scene-1", "visual_prompt": "A fox watching a lantern beneath a frozen lake"}]}


class QuotaHandlingTests(unittest.TestCase):
    def test_quota_failure_is_terminal_and_cleans_staging(self):
        calls = []

        def fake_opener(request, timeout):
            calls.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, io.BytesIO(b""))

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "ASTRA_GEMINI_ART_ENABLED": "1",
            "ASTRA_GEMINI_IMAGE_MODEL": "gemini-2.5-flash-image",
            "GEMINI_API_KEY": "test-key",
        }):
            destination = Path(tmp) / "staging"
            with self.assertRaisesRegex(ValueError, "gemini_image_quota_exhausted_no_retry"):
                generate_staged_art(STORY, destination, opener=fake_opener)
            self.assertEqual(len(calls), 1)
            self.assertFalse(destination.exists())

    def test_other_http_error_is_sanitized(self):
        def fake_opener(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 403, "secret provider text", {}, io.BytesIO(b"secret"))

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "ASTRA_GEMINI_ART_ENABLED": "1",
            "ASTRA_GEMINI_IMAGE_MODEL": "gemini-2.5-flash-image",
            "GEMINI_API_KEY": "test-key",
        }):
            with self.assertRaisesRegex(ValueError, "^gemini_image_http_403$"):
                generate_staged_art(STORY, Path(tmp) / "staging", opener=fake_opener)


if __name__ == "__main__":
    unittest.main()
