"""Protect historical publication identities across publisher and preload lanes."""
import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.proposal_history import protected_content_ids


class ProtectedPublicationHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.publisher = self.root / "astra_v2_state.json"
        self.story = self.root / "astra_story_history.json"

    def write(self, filename, data):
        (self.root / filename).write_text(json.dumps(data), encoding="utf-8")

    def test_missing_pre_reset_ledger_fails_closed(self):
        self.write("astra_v2_state.json", {"version": 2, "published": {}})
        with self.assertRaises(FileNotFoundError):
            protected_content_ids(self.publisher, self.story)

    def test_protected_ids_union_and_canonical_published_key(self):
        self.write("astra_v2_state.json", {"version": 2, "pending": {"video-id": {"content_id": "pending-story"}}})
        self.write("astra_story_history.json", {"stories": [{"content_id": "historical-story"}]})
        self.write("astra_duplicate_protection.json", {
            "schema_version": 1,
            "published": {"protected-story": {"content_id": "wrong-metadata-id"}},
            "stories": [{"content_id": "backup-story"}],
        })
        result = protected_content_ids(self.publisher, self.story)
        self.assertTrue({"protected-story", "backup-story", "pending-story", "historical-story"} <= result)
        self.assertNotIn("wrong-metadata-id", result)

    def test_bad_ledger_structure_fails_closed(self):
        for bad in ({}, {"published": [] , "stories": []}, {"published": {"id": None}, "stories": []}):
            with self.subTest(bad=bad):
                self.write("astra_duplicate_protection.json", bad)
                with self.assertRaises(ValueError):
                    protected_content_ids(self.publisher, self.story)

    def test_both_workflows_restore_durable_ledger(self):
        root = Path(__file__).resolve().parents[1]
        required = "git show origin/astra-state:astra_duplicate_protection.json > astra_duplicate_protection.json"
        for path in (".github/workflows/astra-v2-publish.yml", ".github/workflows/astra-v2-preload.yml"):
            with self.subTest(path=path):
                source = (root / path).read_text(encoding="utf-8")
                self.assertIn(required, source)
                self.assertIn("test -s astra_duplicate_protection.json", source)

    def test_publisher_enforces_final_duplicate_guard(self):
        source = (Path(__file__).resolve().parents[1] / "astra_v2/run.py").read_text(encoding="utf-8")
        self.assertIn("protected_ids = protected_content_ids(*history_args)", source)
        self.assertIn("final_protected_ids = protected_content_ids(*history_args)", source)
        self.assertIn("previous_ids | final_protected_ids", source)


if __name__ == "__main__":
    unittest.main()
