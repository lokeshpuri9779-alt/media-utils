"""Quota cooldown regression coverage for the free-image preproduction route."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from astra_v2 import omniroute_image_assets as images


class ProviderCooldownTests(unittest.TestCase):
    def test_http_429_is_recorded_and_skipped_on_next_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            config = ("https://example.test/free-image", "free-model")
            calls = []
            def quota(_prompt, **kwargs):
                calls.append(kwargs["config"])
                raise ValueError("Image provider HTTP 429")
            with patch.object(images, "configured_free_image_providers", return_value=[(config, "")]), \
                 patch.object(images, "generate_image", side_effect=quota):
                with self.assertRaisesRegex(ValueError, "429"):
                    images._free_image_with_cooldown("safe prompt", directory, max_attempts=1, attempt_counter=[])
                self.assertEqual(len(calls), 1)
                with self.assertRaisesRegex(ValueError, "429"):
                    images._free_image_with_cooldown("another prompt", directory, max_attempts=1, attempt_counter=[])
                self.assertEqual(len(calls), 1)
            self.assertIn(images._provider_cooldown_key(config), images._load_cooldowns(directory))

    def test_fallback_only_after_429(self):
        with tempfile.TemporaryDirectory() as directory:
            one = ("https://example.test/one", "free-one")
            two = ("https://example.test/two", "free-two")
            calls = []
            def request(_prompt, **kwargs):
                calls.append(kwargs["config"])
                if kwargs["config"] == one:
                    raise ValueError("Image provider HTTP 429")
                return b"fake-image"
            with patch.object(images, "configured_free_image_providers", return_value=[(one, ""), (two, "")]), \
                 patch.object(images, "generate_image", side_effect=request):
                attempts = []
                result = images._free_image_with_cooldown("prompt", directory, max_attempts=2, attempt_counter=attempts)
                self.assertEqual(result, b"fake-image")
                self.assertEqual(len(attempts), 2)
                self.assertEqual(calls, [one, two])

    def test_nonquota_error_does_not_trigger_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            one = ("https://example.test/one", "free-one")
            two = ("https://example.test/two", "free-two")
            with patch.object(images, "configured_free_image_providers", return_value=[(one, ""), (two, "")]), \
                 patch.object(images, "generate_image", side_effect=ValueError("Image provider HTTP 401")) as request:
                with self.assertRaisesRegex(ValueError, "401"):
                    images._free_image_with_cooldown("prompt", directory, max_attempts=2, attempt_counter=[])
                self.assertEqual(request.call_count, 1)

    def test_expired_and_malformed_cooldowns_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            state = images._cooldown_path(directory)
            state.parent.mkdir(parents=True, exist_ok=True)
            state.write_text('{"expired": "2000-01-01T00:00:00+00:00", "broken": "bad-date"}')
            self.assertEqual(images._load_cooldowns(directory), {})


if __name__ == "__main__":
    unittest.main()
