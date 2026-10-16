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

    def test_compositional_dimensions_produce_distinct_story_fingerprints(self):
        candidates = [proposal(index) for index in range(300)]
        self.assertEqual(len({item["plot_fingerprint"] for item in candidates}), 300)
        self.assertGreaterEqual(len({item["story_beats"][0]["visual"] for item in candidates}), 8)
        self.assertGreaterEqual(len({item["story_beats"][2]["speech"] for item in candidates}), 8)
        self.assertTrue(all(item["kind"] == "unreviewed_causal_draft" for item in candidates))
        self.assertTrue(all(item["production_ready"] is False for item in candidates))
        self.assertTrue(all(item["title"] != f"Unreviewed story proposal {i + 1}"
                            for i, item in enumerate(candidates)))
        self.assertTrue(all(item["title"].startswith("The ") and "Mystery of the" in item["title"]
                            for item in candidates))

    def test_invalid_indices_and_batch_sizes_rejected(self):
        with self.assertRaises(ValueError):
            proposal(-1)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                replenish(Path(root) / "ledger.json", count=101)


if __name__ == "__main__":
    unittest.main()
