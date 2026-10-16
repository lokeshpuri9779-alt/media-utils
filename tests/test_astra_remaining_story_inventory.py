import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.story_inventory import inventory


class RemainingStoryInventoryTests(unittest.TestCase):
    def test_counts_are_consistent(self):
        with tempfile.TemporaryDirectory() as root:
            result = inventory(Path(root) / "missing-state.json",
                               Path(root) / "missing-history.json")
            self.assertGreater(result["authored_candidates"], 0)
            self.assertEqual(result["eligible_after_history_and_editorial"] +
                             result["blocked"], result["authored_candidates"])
            self.assertFalse(result["automatic_publishing_changed"])

    def test_known_fingerprint_is_excluded(self):
        with tempfile.TemporaryDirectory() as root:
            before = inventory(Path(root) / "missing.json", Path(root) / "absent.json")
            if not before["eligible_content_ids"]:
                self.skipTest("No eligible authored story")
            from astra_v2.story_forge import catalog
            cid = before["eligible_content_ids"][0]
            story = next(s for s in catalog(limit=100000) if s["content_id"] == cid)
            state = Path(root) / "state.json"
            state.write_text(json.dumps({"published": {"prior": {
                "plot_fingerprint": story["plot_fingerprint"]}}}))
            after = inventory(state, Path(root) / "absent.json")
            self.assertNotIn(cid, after["eligible_content_ids"])


if __name__ == "__main__":
    unittest.main()
