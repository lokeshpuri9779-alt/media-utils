"""Regression checks for read-only runway reporting."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.story_runway import runway_report


class RunwayTests(unittest.TestCase):
    def test_missing_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                runway_report(str(Path(tmp) / "publisher.json"),
                              str(Path(tmp) / "stories.json"))

    def test_deficit_is_non_publishing(self):
        with tempfile.TemporaryDirectory() as tmp:
            publisher = Path(tmp) / "publisher.json"
            stories = Path(tmp) / "stories.json"
            publisher.write_text('{"published":{}}')
            stories.write_text('{"stories":[]}')
            with patch("astra_v2.story_runway.inventory", return_value={
                "eligible_after_history_and_editorial": 20,
                "history_records": 245,
                "block_reasons": {"duplicate": 4},
            }):
                result = runway_report(str(publisher), str(stories), 100, 30)
            self.assertEqual(result["deficit"], 2980)
            self.assertEqual(result["status"], "replenishment_required")
            self.assertTrue(result["read_only"])
            self.assertFalse(result["approval_or_publishing_changed"])

    def test_invalid_target_rejected(self):
        with self.assertRaises(ValueError):
            runway_report(daily_target=0)
