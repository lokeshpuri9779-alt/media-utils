import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.global_story_novelty import filter_global_novelty
from astra_v2.single_writer_story_ledger import commit_screened_batch, snapshot_token


class SingleWriterStoryLedgerTests(unittest.TestCase):
    def test_screened_unreviewed_candidates_committed_once(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.json"
            screened = filter_global_novelty({
                "batch_id": "b", "stories": [proposal(5)], "count": 1,
                "approved_count": 0, "publication_triggered": False})
            initial = snapshot_token(ledger)
            self.assertEqual(commit_screened_batch(ledger, screened,
                                                   expected_snapshot=initial, next_index=6), screened["accepted"])
            state = json.loads(ledger.read_text())
            self.assertEqual(state["next_index"], 6)
            self.assertFalse(state["proposals"][0]["production_ready"])
            with self.assertRaises(ValueError):
                commit_screened_batch(ledger, screened, expected_snapshot=initial, next_index=6)

    def test_reject_approved_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.json"
            payload = {"stories": [dict(proposal(1), production_ready=True)], "accepted": 1,
                       "approved_count": 0, "publication_triggered": False}
            with self.assertRaises(ValueError):
                commit_screened_batch(ledger, payload, expected_snapshot=snapshot_token(ledger), next_index=2)

    def test_reject_existing_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.json"
            item = proposal(1)
            ledger.write_text(json.dumps({"next_index": 2, "proposals": [item]}))
            payload = {"stories": [item], "accepted": 1,
                       "approved_count": 0, "publication_triggered": False}
            with self.assertRaises(ValueError):
                commit_screened_batch(ledger, payload, expected_snapshot=snapshot_token(ledger), next_index=3)


if __name__ == "__main__":
    unittest.main()
