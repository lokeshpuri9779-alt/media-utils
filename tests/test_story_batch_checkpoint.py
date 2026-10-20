"""Checkpoint contract regression tests: no approval, corruption fails closed."""
import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.story_batch_checkpoint import (
    checkpoint_record, read_checkpoint, write_checkpoint,
)


class StoryBatchCheckpointTests(unittest.TestCase):
    def test_round_trip_is_not_publication_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "checkpoint.json"
            original = checkpoint_record("run-42-worker-3", "generated", ["a", "b"], complete=True)
            write_checkpoint(path, original)
            self.assertEqual(read_checkpoint(path, batch_id="run-42-worker-3", stage="generated"), original)
            self.assertEqual(original["approved_count"], 0)
            self.assertFalse(original["publication_triggered"])

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            checkpoint_record("batch", "generated", ["same", "same"])

    def test_wrong_batch_or_stage_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            write_checkpoint(path, checkpoint_record("batch", "generated", ["a"]))
            with self.assertRaises(ValueError):
                read_checkpoint(path, batch_id="other")
            with self.assertRaises(ValueError):
                read_checkpoint(path, stage="reviewed")

    def test_tampered_approval_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            write_checkpoint(path, checkpoint_record("batch", "generated", ["a"]))
            tampered = json.loads(path.read_text())
            tampered["approved_count"] = 1
            path.write_text(json.dumps(tampered))
            with self.assertRaises(ValueError):
                read_checkpoint(path)

    def test_incomplete_or_corrupt_checkpoint_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            path.write_text('{"schema_version":1')
            with self.assertRaises(json.JSONDecodeError):
                read_checkpoint(path)


if __name__ == "__main__":
    unittest.main()
