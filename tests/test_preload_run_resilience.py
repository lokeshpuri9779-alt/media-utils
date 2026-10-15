"""Regression tests for preload run metadata caching and failure isolation."""
import os
import subprocess
import unittest
from unittest.mock import patch

from astra_v2 import preload_queue as queue


class RunMetadataResilienceTests(unittest.TestCase):
    def setUp(self):
        self.entries = [
            {"id": 1, "name": "astra-preloaded-first", "created_at": "2026-10-16T00:00:00Z",
             "workflow_run": {"head_branch": "main", "id": 41}},
            {"id": 2, "name": "astra-preloaded-second", "created_at": "2026-10-15T23:00:00Z",
             "workflow_run": {"head_branch": "main", "id": 41}},
            {"id": 3, "name": "astra-preloaded-third", "created_at": "2026-10-15T22:00:00Z",
             "workflow_run": {"head_branch": "main", "id": 42}},
        ]

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo",
                             "ASTRA_PRELOAD_MAX_AGE_HOURS": "0",
                             "ASTRA_SERIES_PUBLICATION": "0"})
    def test_failed_run_lookup_does_not_block_next_run(self):
        calls = []
        def lookup(path):
            calls.append(path)
            if path.endswith("/41"):
                raise subprocess.CalledProcessError(1, ["gh", "api", path])
            return {"conclusion": "failure", "head_branch": "main",
                    "name": "ASTRA V2 - Preload Approved Videos"}
        with patch.object(queue, "artifacts", return_value=self.entries):
            with patch.object(queue, "_api", side_effect=lookup):
                with patch("subprocess.run") as download:
                    self.assertIsNone(queue.take(set(), set(), "/tmp/unused-queue-test.mp4"))
                    download.assert_not_called()
        self.assertEqual(calls, ["repos/owner/repo/actions/runs/41",
                                 "repos/owner/repo/actions/runs/42"])

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo",
                             "ASTRA_PRELOAD_MAX_AGE_HOURS": "0",
                             "ASTRA_SERIES_PUBLICATION": "0"})
    def test_untrusted_shared_run_looked_up_once(self):
        with patch.object(queue, "artifacts", return_value=self.entries[:2]):
            with patch.object(queue, "_api", return_value={
                "conclusion": "failure", "head_branch": "main",
                "name": "ASTRA V2 - Preload Approved Videos"}) as api:
                with patch("subprocess.run") as download:
                    self.assertIsNone(queue.take(set(), set(), "/tmp/unused-queue-test.mp4"))
                    download.assert_not_called()
                    api.assert_called_once_with("repos/owner/repo/actions/runs/41")


if __name__ == "__main__":
    unittest.main()
