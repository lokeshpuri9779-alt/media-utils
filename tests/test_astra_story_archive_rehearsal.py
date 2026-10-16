import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from astra_v2.story_archive_rehearsal import rehearse_state_restore
from astra_v2.story_ledger import StoryLedgerError, archive_fingerprints, read_ledger


FP_A = "a" * 64
FP_B = "b" * 64


class StoryArchiveRehearsalTests(unittest.TestCase):
    def test_rehearsal_does_not_modify_source_files(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "astra_v2_state.json"
            archive = Path(directory) / "archive.json"
            state.write_text(json.dumps({
                "reserved": {"new": {"plot_fingerprint": FP_A}},
                "published": {"legacy": {"content_id": "old"}},
            }), encoding="utf-8")
            archive_fingerprints(archive, [FP_B])
            before_state = state.read_bytes()
            before_archive = archive.read_bytes()
            result = rehearse_state_restore(state, archive)
            self.assertTrue(result["simulated_restart_verified"])
            self.assertFalse(result["historical_coverage_complete"])
            self.assertEqual(result["coverage"]["missing"], 1)
            self.assertEqual(result["archived_count"], 2)
            self.assertEqual(result["source_state_sha256"], hashlib.sha256(before_state).hexdigest())
            self.assertEqual(result["source_archive_sha256"], hashlib.sha256(before_archive).hexdigest())
            self.assertEqual(state.read_bytes(), before_state)
            self.assertEqual(archive.read_bytes(), before_archive)

    def test_rehearsal_fails_closed_on_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            state.write_text(json.dumps({"published": {"x": {
                "plot_fingerprint": FP_A, "plot_hash": FP_B}}}), encoding="utf-8")
            with self.assertRaisesRegex(StoryLedgerError, "history_untrusted"):
                rehearse_state_restore(state)

    def test_missing_archive_path_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            state.write_text('{"published": {}}', encoding="utf-8")
            with self.assertRaisesRegex(StoryLedgerError, "restore_missing"):
                rehearse_state_restore(state, Path(directory) / "absent.json")


if __name__ == "__main__":
    unittest.main()
