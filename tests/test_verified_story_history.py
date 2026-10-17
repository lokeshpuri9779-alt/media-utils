import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.verified_story_history import record_confirmed

class VerifiedStoryHistoryTests(unittest.TestCase):
    def test_confirmed_is_persisted_once(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "history.json"
            item = {"video_id": "verified123", "confirmed_at": "2026-10-17T00:00:00Z",
                    "plot_key": "unique-plot", "plot_fingerprint": "sha-example"}
            self.assertTrue(record_confirmed(p, "story-1", item))
            self.assertFalse(record_confirmed(p, "story-1", item))
            self.assertEqual(json.loads(p.read_text())["stories"][0]["plot_key"], "unique-plot")
            self.assertEqual(len(json.loads(p.read_text())["stories"]), 1)

    def test_unconfirmed_rejected_without_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "history.json"
            with self.assertRaises(ValueError):
                record_confirmed(p, "story-1", {"video_id": "not-verified"})
            self.assertFalse(p.exists())

    def test_corrupt_history_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "history.json"
            p.write_text("broken")
            with self.assertRaises(ValueError):
                record_confirmed(p, "story-1", {"video_id": "ok", "confirmed_at": "now"})
            self.assertEqual(p.read_text(), "broken")

if __name__ == "__main__":
    unittest.main()
