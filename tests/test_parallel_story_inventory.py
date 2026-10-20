import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.parallel_story_inventory import replenish_parallel


class ParallelStoryInventoryTests(unittest.TestCase):
    def test_isolated_workers_write_once_without_approval(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "ledger.json"
            with patch("astra_v2.parallel_story_inventory.load_history", return_value=[]):
                accepted = replenish_parallel(ledger, batch_id="test", workers=8, total=16)
            state = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(state["next_index"], 16)
            self.assertEqual(len(state["proposals"]), accepted)
            self.assertEqual(state["parallel_batch_last"]["proposed"], 16)
            self.assertEqual(state["parallel_batch_last"]["approved_count"], 0)
            self.assertFalse(state["parallel_batch_last"]["publication_triggered"])
            self.assertTrue(all(item["production_ready"] is False for item in state["proposals"]))


if __name__ == "__main__":
    unittest.main()
