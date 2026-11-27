"""The long-form selector must enforce exclusions before returning an episode."""
from __future__ import annotations

import contextlib
import io
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from longform import EPISODE_ID, choose_episode


class LongformSelectorExclusionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 27, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        self.episode_id = "trend-brief-2026-11-27-am"
        self.data = {
            "videos": {
                "planet-clocks": {
                    "content_id": EPISODE_ID,
                    "format": "long",
                    "published_at": "2026-11-20T09:00:00+05:30",
                }
            },
            "trend_snapshot": {
                "checked_at": self.now.isoformat(),
                "items": [{"topic": "space exploration"}],
            },
        }

    @patch("longform_trends.available", return_value=True)
    def test_excluded_trend_episode_is_not_returned(self, _available):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            selected = choose_episode(self.data, self.now, excluded_ids={self.episode_id})
        self.assertIsNone(selected)
        self.assertIn("ASTRA_LONGFORM_SUPPLY=episode_already_excluded", output.getvalue())

    @patch("longform_trends.available", return_value=True)
    def test_non_excluded_trend_episode_remains_selectable(self, _available):
        self.assertEqual(choose_episode(self.data, self.now), self.episode_id)


if __name__ == "__main__":
    unittest.main()
