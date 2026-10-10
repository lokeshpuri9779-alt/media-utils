"""Regression coverage for the independent long-form publishing interval."""
import unittest
from datetime import datetime, timedelta, timezone

from astra_v2.run import long_upload_due


class LongUploadCooldownTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)

    def entry(self, hours_ago, fmt="long", key="uploaded_at"):
        return {"format": fmt, key: (self.now - timedelta(hours=hours_ago)).isoformat()}

    def test_first_long_video_is_allowed(self):
        self.assertTrue(long_upload_due({}, self.now))

    def test_shorts_do_not_block_long_video(self):
        state = {"published": {"short-1": self.entry(1, "short")}}
        self.assertTrue(long_upload_due(state, self.now))

    def test_recent_published_long_blocks(self):
        state = {"published": {"long-1": self.entry(23)}}
        self.assertFalse(long_upload_due(state, self.now))
        self.assertTrue(long_upload_due(state, self.now + timedelta(hours=1)))

    def test_pending_long_blocks(self):
        state = {"pending": {"youtube-id": self.entry(2)}}
        self.assertFalse(long_upload_due(state, self.now))

    def test_reserved_long_blocks(self):
        state = {"reserved": {"long-1": self.entry(3, key="at")}}
        self.assertFalse(long_upload_due(state, self.now))

    def test_confirmed_at_fallback(self):
        state = {"published": {"long-1": self.entry(12, key="confirmed_at")}}
        self.assertFalse(long_upload_due(state, self.now))

    def test_latest_long_wins(self):
        state = {"published": {"old": self.entry(48), "new": self.entry(5)}}
        self.assertFalse(long_upload_due(state, self.now))


if __name__ == "__main__":
    unittest.main()
