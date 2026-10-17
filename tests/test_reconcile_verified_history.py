import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.reconcile_verified_history import reconcile_verified_history

class ReconcileHistoryTests(unittest.TestCase):
    def test_adds_verified_only_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d) / "state.json"
            history = Path(d) / "history.json"
            state.write_text(json.dumps({"published": {
                "verified": {"video_id": "abc", "confirmed_at": "2026-10-17", "title": "A title"},
                "incomplete": {"video_id": "xyz"}
            }}))
            result = reconcile_verified_history(state, history)
            self.assertEqual(result["added"], 1)
            self.assertEqual(result["skipped_unverified"], 1)
            self.assertEqual(result["unknown_plot_fingerprint"], 1)
            self.assertEqual(reconcile_verified_history(state, history)["added"], 0)
            self.assertNotIn("plot_fingerprint", json.loads(history.read_text())["stories"][0])

    def test_does_not_overwrite_corrupt_history(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d) / "state.json"
            history = Path(d) / "history.json"
            state.write_text(json.dumps({"published": {"a": {"video_id": "a", "confirmed_at": "now"}}}))
            history.write_text("invalid")
            with self.assertRaises(ValueError):
                reconcile_verified_history(state, history)
            self.assertEqual(history.read_text(), "invalid")
