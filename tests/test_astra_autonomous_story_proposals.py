import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.autonomous_story_proposals import replenish, proposal
from astra_v2.publication_quality import publication_rejection


class AutonomousStoryProposalTests(unittest.TestCase):
    def test_persistent_novelty_and_nonpublication(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "proposals.json"
            first = replenish(path, count=8)
            before = json.loads(path.read_text())
            second = replenish(path, count=8)
            after = json.loads(path.read_text())
            self.assertGreater(first, 0)
            self.assertGreaterEqual(second, 0)
            self.assertEqual(len(after["proposals"]), first + second)
            self.assertEqual(len({s["plot_fingerprint"] for s in after["proposals"]}), first + second)
            self.assertGreater(after["next_index"], before["next_index"])
            self.assertTrue(all(publication_rejection(s) for s in after["proposals"]))

    def test_invalid_indices_and_batch_sizes_rejected(self):
        with self.assertRaises(ValueError):
            proposal(-1)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                replenish(Path(root) / "ledger.json", count=101)


if __name__ == "__main__":
    unittest.main()
