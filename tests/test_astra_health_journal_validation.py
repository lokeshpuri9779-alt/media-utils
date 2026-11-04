"""Fail-closed publisher journal validation regression tests."""
import unittest
from datetime import datetime, timezone
from astra_v2.health import assess


class PublisherHealthJournalTests(unittest.TestCase):
    def test_non_mapping_state_fails_closed(self):
        for value in (None, [], "broken", 1):
            with self.subTest(value=value):
                self.assertEqual(assess(value)[0], "unhealthy")

    def test_pending_entry_must_be_mapping(self):
        state = {"version": 2, "pending": {"upload": "broken"}, "published": {}}
        self.assertEqual(assess(state)[1], "pending_entry_invalid")

    def test_published_entry_must_be_mapping(self):
        state = {"version": 2, "pending": {}, "published": {"id": None}}
        self.assertEqual(assess(state)[1], "published_journal_invalid")

    def test_missing_pending_is_valid_empty_journal(self):
        state = {"version": 2, "published": {}, "created_at": datetime.now(timezone.utc).isoformat()}
        self.assertNotEqual(assess(state)[0], "unhealthy")


if __name__ == "__main__":
    unittest.main()
