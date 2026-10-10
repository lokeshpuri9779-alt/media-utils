"""Regression checks for GitHub Actions preload artifact discovery."""
import os
import unittest
from unittest.mock import patch
from astra_v2 import preload_queue


class QueueDiscoveryTests(unittest.TestCase):
    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"})
    @patch.object(preload_queue, "_api")
    def test_pagination_and_null_metadata(self, api):
        first = [{"name": f"unrelated-{i}", "expired": False} for i in range(99)]
        first.append({"name": "astra-preloaded-bad", "expired": False, "workflow_run": None})
        second = [{"name": "astra-preloaded-good", "expired": False,
                   "workflow_run": {"head_branch": "main"}}]
        api.side_effect = [{"artifacts": first}, {"artifacts": second}]
        self.assertEqual([a["name"] for a in preload_queue.artifacts()],
                         ["astra-preloaded-good"])
        self.assertEqual(api.call_count, 2)

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"})
    @patch.object(preload_queue, "_api")
    def test_single_page(self, api):
        api.return_value = {"artifacts": [{"name": "astra-preloaded-yes",
                           "expired": False, "workflow_run": {"head_branch": "main"}}]}
        self.assertEqual(preload_queue.candidate_ids(), {"yes"})
        api.assert_called_once()


if __name__ == "__main__":
    unittest.main()
