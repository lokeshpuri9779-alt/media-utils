import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.story_ledger import StoryLedgerError, archive_fingerprints, archive_lifecycle_record, read_ledger


FP_A = "a" * 64
FP_B = "b" * 64


class DurableStoryLedgerTests(unittest.TestCase):
    def test_archive_is_durable_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            archive_fingerprints(path, [FP_A])
            archive_fingerprints(path, [FP_A, FP_B])
            self.assertEqual(read_ledger(path)["archived"], [FP_A, FP_B])

    def test_existing_archive_is_never_dropped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            path.write_text(json.dumps({"version": 1, "archived": [FP_A]}), encoding="utf-8")
            archive_fingerprints(path, [FP_B])
            self.assertEqual(read_ledger(path)["archived"], [FP_A, FP_B])

    def test_corrupt_ledger_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(StoryLedgerError, "unreadable"):
                archive_fingerprints(path, [FP_A])
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")

    def test_invalid_fingerprint_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            with self.assertRaisesRegex(StoryLedgerError, "invalid_fingerprint"):
                archive_fingerprints(path, ["not-a-sha256"])
            self.assertFalse(path.exists())


    def test_episode_planner_excludes_archived_fingerprint_after_restart(self):
        from astra_v2.episode_planner import fingerprint, plan_episode_with_ledger

        scenes = [
            {"cause": "Gate jams", "action": "Inspect hinge", "consequence": "Pin bent"},
            {"cause": "Pin bent", "action": "Straighten pin", "consequence": "Hinge moves"},
            {"cause": "Hinge moves", "action": "Open gate", "consequence": "Village passes"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            archive_fingerprints(path, [fingerprint({"scenes": scenes})])
            with self.assertRaisesRegex(ValueError, "already_used"):
                plan_episode_with_ledger("village", 2, scenes, path)

    def test_episode_planner_fails_closed_if_ledger_corrupt(self):
        from astra_v2.episode_planner import plan_episode_with_ledger

        scenes = [
            {"cause": "Gate jams", "action": "Inspect hinge", "consequence": "Pin bent"},
            {"cause": "Pin bent", "action": "Straighten pin", "consequence": "Hinge moves"},
            {"cause": "Hinge moves", "action": "Open gate", "consequence": "Village passes"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ledger_unavailable"):
                plan_episode_with_ledger("village", 2, scenes, path)


    def test_only_explicit_consumed_lifecycle_states_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            with self.assertRaisesRegex(StoryLedgerError, "not_archivable"):
                archive_lifecycle_record(path, {"plot_fingerprint": FP_A}, "draft")
            self.assertFalse(path.exists())
            archive_lifecycle_record(path, {"plot_fingerprint": FP_A}, "reserved")
            self.assertEqual(read_ledger(path)["archived"], [FP_A])

    def test_lifecycle_archival_rejects_missing_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            with self.assertRaisesRegex(StoryLedgerError, "fingerprint_missing"):
                archive_lifecycle_record(path, {}, "published")

    def test_invalid_existing_archive_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            original = json.dumps({"version": 1, "archived": ["not-a-sha256"]})
            path.write_text(original, encoding="utf-8")
            with self.assertRaisesRegex(StoryLedgerError, "invalid_archive"):
                archive_fingerprints(path, [FP_A])
            self.assertEqual(path.read_text(encoding="utf-8"), original)
