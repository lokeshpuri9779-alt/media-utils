"""Tests for durable mechanism novelty ledger."""
import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.story_mechanism_ledger import (
    load_mechanisms, save_mechanisms, queue_from_ledger, record_reviewed)


class MechanismLedgerTests(unittest.TestCase):
    def test_persist_and_exclude_reviewed_mechanism(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mechanisms.json"
            first = queue_from_ledger(path, limit=1)
            key = first["review_queue"][0]["mechanism"]
            self.assertEqual(record_reviewed(path, key), 1)
            self.assertEqual(record_reviewed(path, key), 1)
            self.assertEqual(load_mechanisms(path), {key})
            following = queue_from_ledger(path)
            self.assertNotIn(key, {x["mechanism"] for x in following["review_queue"]})
            self.assertFalse(following["publication_enabled"])

    def test_invalid_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mechanisms.json"
            path.write_text(json.dumps({"schema_version": 999,
                                        "reviewed_mechanisms": []}))
            with self.assertRaises(ValueError):
                queue_from_ledger(path)

    def test_save_is_sorted_and_validated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mechanisms.json"
            save_mechanisms(path, {"z", "a"})
            self.assertEqual(json.loads(path.read_text())["reviewed_mechanisms"], ["a", "z"])
            with self.assertRaises(ValueError):
                save_mechanisms(path, {"", "a"})


if __name__ == "__main__":
    unittest.main()
