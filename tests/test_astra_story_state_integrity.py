"""Regression tests for fail-closed publisher state restoration."""
import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.state_integrity import StateJournalError, validate_state_journal


class StateJournalIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "astra_v2_state.json"
        self.valid = {
            "version": 2, "day": "2026-10-17", "attempts": 3,
            "confirmed_today": 2,
            "published": {"story-1": {"video_id": "yt-1"}},
            "pending": {"yt-2": {"content_id": "story-2"}},
            "reserved": {"story-3": {"result": "transfer_pending"}},
        }

    def save(self, data):
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_preserves_valid_published_pending_and_reserved(self):
        self.save(self.valid)
        self.assertEqual(validate_state_journal(self.path), self.valid)

    def test_legacy_valid_journal_without_reserved_is_accepted(self):
        self.save({key: value for key, value in self.valid.items()
                   if key != "reserved"})
        self.assertEqual(len(validate_state_journal(self.path)["published"]), 1)

    def test_missing_file_is_not_treated_as_fresh_state(self):
        with self.assertRaises(StateJournalError):
            validate_state_journal(self.path)

    def test_corrupt_json_is_rejected(self):
        self.path.write_text("{", encoding="utf-8")
        with self.assertRaises(StateJournalError):
            validate_state_journal(self.path)

    def test_empty_or_wrong_version_is_rejected(self):
        for value in ({}, {"version": 1}, [], None):
            with self.subTest(value=value):
                self.save(value)
                with self.assertRaises(StateJournalError):
                    validate_state_journal(self.path)

    def test_invalid_identity_journal_is_rejected(self):
        for field in ("published", "pending", "reserved"):
            for value in (None, [], {"bad": None}, {"bad": "string"}):
                with self.subTest(field=field, value=value):
                    data = {**self.valid, field: value}
                    self.save(data)
                    with self.assertRaises(StateJournalError):
                        validate_state_journal(self.path)

    def test_invalid_counters_are_rejected(self):
        for field in ("attempts", "confirmed_today"):
            for value in (-1, "0", True, None):
                with self.subTest(field=field, value=value):
                    self.save({**self.valid, field: value})
                    with self.assertRaises(StateJournalError):
                        validate_state_journal(self.path)


if __name__ == "__main__":
    unittest.main()
