"""Read-only Actions listing tests: no token leakage or write actions."""
import io
import json
import unittest
from tools.astra_publisher_actions_probe import collect, WORKFLOWS


class ActionsMetadataProbeTests(unittest.TestCase):
    def test_three_workflows_return_bounded_run_ids(self):
        observed = []
        def fake(request, timeout):
            observed.append((request.full_url, request.get_header("Authorization")))
            return io.BytesIO(json.dumps({"workflow_runs": [
                {"id": 41830012345, "status": "completed",
                 "conclusion": "failure", "event": "schedule",
                 "created_at": "2026-11-04T12:30:00Z",
                 "updated_at": "2026-11-04T12:35:00Z",
                 "head_sha": "0"*40},
            ]}).encode())
        report = collect("example/repo", "never-print-me", transport=fake)
        self.assertEqual(set(report["workflows"]), set(WORKFLOWS))
        self.assertEqual(len(observed), 3)
        self.assertTrue(all("/actions/workflows/" in url and "per_page=5" in url
                            for url, _ in observed))
        self.assertTrue(all(header == "Bearer never-print-me" for _, header in observed))
        self.assertNotIn("never-print-me", json.dumps(report))
        self.assertFalse(report["workflow_dispatched"])
        self.assertFalse(report["production_modified"])
        self.assertTrue(report["only_metadata_accessed"])

    def test_missing_or_invalid_token_or_repo_fails_before_network(self):
        for repo, token in [("untrusted", "secret"), ("x/y", ""),
                            ("owner/repo?q=leak", "secret")]:
            calls = []
            with self.subTest(repo=repo), self.assertRaises(ValueError):
                collect(repo, token, transport=lambda *args, **kwargs: calls.append(1))
            self.assertEqual(calls, [])

    def test_invalid_run_payload_does_not_claim_success(self):
        for payload in ({}, {"workflow_runs": [{}]},
                        {"workflow_runs": [{"id": "not-integer"}]},
                        {"workflow_runs": [None]}, {"workflow_runs": [{}]*6}):
            with self.subTest(data=repr(payload)), self.assertRaises(ValueError):
                collect("owner/repo", "token",
                        transport=lambda request, timeout:
                        io.BytesIO(json.dumps(payload).encode()))

    def test_exception_never_leaks_private_message(self):
        def bad(request, timeout):
            raise OSError("SECRET_TOKEN_SENTINEL")
        with self.assertRaisesRegex(RuntimeError, "Workflow run metadata unavailable") as exc:
            collect("owner/repo", "token", transport=bad)
        self.assertNotIn("SECRET_TOKEN_SENTINEL", str(exc.exception))


if __name__ == "__main__":
    unittest.main()
