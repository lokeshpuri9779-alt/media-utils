"""Regression checks for pinned remote reviewed-art restoration."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.preload_art_receipt import restore_for_preload


class ScheduledArtRestoreTests(unittest.TestCase):
    def test_index_requires_exact_story_id(self):
        with tempfile.TemporaryDirectory() as temp:
            index = Path(temp) / "index.json"
            index.write_text(json.dumps({"schema": "astra.reviewed-art.index.v1"}))
            env = {"ASTRA_REVIEWED_ART_INDEX_RECEIPT_FILE": str(index)}
            with self.assertRaisesRegex(ValueError, "reviewed_art_content_id_required"):
                restore_for_preload(environ=env, store=object())

    def test_missing_story_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            index = Path(temp) / "index.json"
            index.write_text(json.dumps({"schema": "astra.reviewed-art.index.v1"}))
            env = {"ASTRA_REVIEWED_ART_INDEX_RECEIPT_FILE": str(index),
                   "ASTRA_REVIEWED_ART_CONTENT_ID": "story-1"}
            with patch("astra_v2.reviewed_art_receipt_index.lookup", return_value=None):
                with self.assertRaisesRegex(ValueError, "reviewed_art_story_receipt_missing"):
                    restore_for_preload(environ=env, store=object())

    def test_receipt_source_conflict_fails_closed(self):
        env = {"ASTRA_REVIEWED_ART_RECEIPT_FILE": "one.json",
               "ASTRA_REVIEWED_ART_INDEX_RECEIPT_FILE": "two.json"}
        with self.assertRaisesRegex(ValueError, "conflicting_art_receipt_sources"):
            restore_for_preload(environ=env, store=object())


if __name__ == "__main__":
    unittest.main()
