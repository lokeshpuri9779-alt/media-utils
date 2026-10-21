import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from astra_v2.github_ledger_cas import GitHubLedgerCAS
from astra_v2.github_storage_ledger import SCHEMA, reserve


class GitHubLedgerCASTests(unittest.TestCase):
    def setUp(self):
        self.adapter = GitHubLedgerCAS("example/repo", token="test-token")
        self.state = {"schema": SCHEMA, "capacity_bytes": 100,
                      "used_bytes": 0, "reservations": {}}

    def test_rejects_missing_credentials(self):
        with patch.dict("os.environ", {"GH_TOKEN": ""}):
            with self.assertRaises(RuntimeError):
                GitHubLedgerCAS("example/repo")

    def test_read_requires_initialized_ledger(self):
        responses = [
            {"object": {"sha": "parent"}},
            {"tree": {"sha": "tree"}},
            {"tree": []},
        ]
        with patch.object(self.adapter, "_api", side_effect=responses):
            with self.assertRaisesRegex(RuntimeError, "not_initialized"):
                self.adapter.read()

    def test_compare_and_swap_nonforce(self):
        calls = []
        responses = [{"tree": {"sha": "old-tree"}}, {"sha": "blob"},
                     {"sha": "new-tree"}, {"sha": "new-commit"}, {}]
        def api(method, path, payload=None):
            calls.append((method, path, payload))
            return responses.pop(0)
        with patch.object(self.adapter, "_api", side_effect=api):
            self.assertTrue(self.adapter.compare_and_swap("parent", self.state))
        self.assertEqual(calls[3][2]["parents"], ["parent"])
        self.assertEqual(calls[4][2]["force"], False)

    def test_conflict_fails_closed(self):
        responses = [{"tree": {"sha": "old-tree"}}, {"sha": "blob"},
                     {"sha": "new-tree"}, {"sha": "new-commit"}]
        def api(method, path, payload=None):
            if method == "PATCH":
                raise HTTPError("https://api.github.com", 422, "conflict", {}, io.BytesIO())
            return responses.pop(0)
        with patch.object(self.adapter, "_api", side_effect=api):
            self.assertFalse(self.adapter.compare_and_swap("parent", self.state))

    def test_transaction_delegates(self):
        with patch.object(self.adapter, "read", return_value=("parent", self.state)):
            with patch.object(self.adapter, "compare_and_swap", return_value=True):
                result = self.adapter.transaction(lambda s: reserve(s, "video-1", 30))
        self.assertEqual(result["reservations"], {"video-1": 30})


if __name__ == "__main__":
    unittest.main()
