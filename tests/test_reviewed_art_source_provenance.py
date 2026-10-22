import json
import unittest
from types import SimpleNamespace
from astra_v2.reviewed_art_source_provenance import verify_source_run


class ProducerSourceProvenanceTests(unittest.TestCase):
    def run_record(self, **changes):
        record = {"id": 123, "repository": {"full_name": "owner/repo"},
                  "head_repository": {"full_name": "owner/repo"},
                  "head_branch": "main", "status": "completed",
                  "conclusion": "success", "event": "workflow_dispatch",
                  "head_sha": "a" * 40,
                  "path": ".github/workflows/astra-approved-art-source.yml@refs/heads/main"}
        record.update(changes)
        return record

    def verify(self, record):
        def runner(*args, **kwargs):
            return SimpleNamespace(stdout=json.dumps(record))
        return verify_source_run("owner/repo", "123", runner=runner)

    def test_accept_successful_main_run(self):
        self.assertEqual(self.verify(self.run_record()), "a" * 40)

    def test_reject_failed_run(self):
        with self.assertRaisesRegex(ValueError, "untrusted"):
            self.verify(self.run_record(conclusion="failure"))

    def test_reject_fork_source(self):
        with self.assertRaisesRegex(ValueError, "untrusted"):
            self.verify(self.run_record(head_repository={"full_name": "fork/repo"}))

    def test_reject_unrelated_workflow(self):
        with self.assertRaisesRegex(ValueError, "untrusted"):
            self.verify(self.run_record(path=".github/workflows/astra-v2-publish.yml@refs/heads/main"))

    def test_reject_non_main(self):
        with self.assertRaisesRegex(ValueError, "untrusted"):
            self.verify(self.run_record(head_branch="feature"))


if __name__ == "__main__":
    unittest.main()
