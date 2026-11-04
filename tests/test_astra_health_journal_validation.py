"""Production health journal safety regression tests."""
import unittest
from datetime import datetime, timezone
from astra_v2.health import assess


class PublisherJournalHealthTests(unittest.TestCase):
    def test_pending_entry_must_be_a_mapping(self):
        now = datetime(2026, 10, 17, tzinfo=timezone.utc)
        state = {"version": 2, "created_at": now.isoformat(), "pending": {"video": ["malformed"]}}
        self.assertEqual(assess(state, now), ("unhealthy", "pending_journal_invalid"))


if __name__ == "__main__":
    unittest.main()
