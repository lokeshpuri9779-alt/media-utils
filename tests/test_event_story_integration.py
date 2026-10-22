"""Offline end-to-end tests for the opt-in story event pipeline.

Uses an in-memory fake ledger only; no PostgreSQL, YouTube, or external API.
"""
import tempfile
import threading
import unittest
from pathlib import Path

from astra_v2.event_story_stripes import (
    run_parallel_story_stripes, combine_completed_stripes,
)


class MemoryLedger:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = {}

    def states(self, content_id):
        with self.lock:
            return {"story": self.state.get(content_id, "pending")}

    def claim(self, content_id, stage):
        with self.lock:
            if stage != "story" or self.state.get(content_id, "pending") != "pending":
                return None
            self.state[content_id] = "running"
            return {"lease_token": "0" * 32}

    def finish(self, content_id, stage, token, *, status, result_ref=None, error_code=None):
        with self.lock:
            assert self.state[content_id] == "running"
            self.state[content_id] = status


class StoryCoordinatorIntegrationTests(unittest.TestCase):
    def test_two_workers_generate_and_consolidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = MemoryLedger()
            results = run_parallel_story_stripes(
                ledger, batch_id="integration", output_root=tmp,
                start_index=10000, workers=2, total=4, max_workers=2)
            self.assertEqual(len(results), 2)
            self.assertTrue(all(r.status == "succeeded" for r in results))
            merged = combine_completed_stripes("integration", tmp, workers=2, total=4)
            self.assertEqual(merged["count"], 4)
            self.assertEqual(merged["approved_count"], 0)
            self.assertFalse(merged["publication_triggered"])
            self.assertEqual(len({s["content_id"] for s in merged["stories"]}), 4)

    def test_repeated_dispatch_cannot_repeat_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = MemoryLedger()
            run_parallel_story_stripes(ledger, batch_id="repeat", output_root=tmp,
                                       start_index=10000, workers=1, total=1)
            repeated = run_parallel_story_stripes(
                ledger, batch_id="repeat", output_root=tmp,
                start_index=10000, workers=1, total=1)
            self.assertEqual(repeated, ())


if __name__ == "__main__":
    unittest.main()
