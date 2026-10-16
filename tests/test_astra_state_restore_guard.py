"""Offline tests for fail-closed ASTRA publisher journal restoration."""
import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.state_restore_guard import (
    UnsafePublisherState, validate_file, validate_state,
)


def valid_state():
    return {
        "version": 2,
        "day": "2026-10-17",
        "attempts": 3,
        "confirmed_today": 2,
        "published": {"story-1": {"video_id": "abc123"}},
        "pending": {"upload-2": {"content_id": "story-2"}},
        "reserved": {"story-3": {"result": "transfer_pending"}},
    }


class RestoreGuardTests(unittest.TestCase):
    def test_valid_journal_keeps_pending_and_reserved(self):
        state = valid_state()
        self.assertIs(validate_state(state, require_history=True), state)

    def test_missing_or_corrupt_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            with self.assertRaises(UnsafePublisherState):
                validate_file(path, require_history=True)
            path.write_text("{truncated", encoding="utf-8")
            with self.assertRaises(UnsafePublisherState):
                validate_file(path, require_history=True)
            path.write_text(json.dumps(valid_state()), encoding="utf-8")
            self.assertEqual(validate_file(path, require_history=True)["attempts"], 3)

    def test_missing_history_rejected_in_production(self):
        state = valid_state()
        state["published"] = {}
        with self.assertRaises(UnsafePublisherState):
            validate_state(state, require_history=True)
        validate_state(state, require_history=False)

    def test_wrong_version_and_bad_journal_rejected(self):
        for field, value in (
            ("version", 1),
            ("published", []),
            ("pending", None),
            ("reserved", []),
            ("attempts", -1),
            ("confirmed_today", "2"),
            ("day", "not-a-date"),
        ):
            with self.subTest(field=field):
                state = valid_state()
                state[field] = value
                with self.assertRaises(UnsafePublisherState):
                    validate_state(state, require_history=True)

    def test_invalid_entries_rejected(self):
        for field, value in (
            ("published", {"story-1": None}),
            ("published", {"story-1": {}}),
            ("pending", {"video-1": {}}),
            ("reserved", {"story-1": "accepted"}),
        ):
            with self.subTest(field=field):
                state = valid_state()
                state[field] = value
                with self.assertRaises(UnsafePublisherState):
                    validate_state(state, require_history=True)

    def test_legacy_valid_journal_without_reserved_accepted(self):
        state = valid_state()
        del state["reserved"]
        validate_state(state, require_history=True)


if __name__ == "__main__":
    unittest.main()
