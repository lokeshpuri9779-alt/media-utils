import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.proposal_history import load_history
from astra_v2.autonomous_story_proposals import proposal, replenish
from astra_v2.story_editorial_report import report


class ProposalHistoryTests(unittest.TestCase):
    def test_all_publication_buckets_and_story_history(self):
        with tempfile.TemporaryDirectory() as root:
            publisher = Path(root) / "state.json"
            stories = Path(root) / "stories.json"
            publisher.write_text(json.dumps({
                "published": {"pub": {"title": "Published"}},
                "pending": {"pen": {"plot_fingerprint": "pending-hash"}},
                "reserved": {"res": {"title": "Reserved"}},
                "rejected": {"rej": {"title": "Rejected"}}
            }))
            stories.write_text(json.dumps({"stories": [{"content_id": "historical"}]}))
            history = load_history(publisher, stories)
            self.assertEqual({x["content_id"] for x in history},
                             {"pub", "pen", "res", "rej", "historical"})

    def test_proposals_skip_known_publication_fingerprint(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "ledger.json"
            prior = proposal(0)
            self.assertEqual(replenish(target, count=1, history=[prior]), 1)
            data = json.loads(target.read_text())
            self.assertNotEqual(data["proposals"][0]["plot_fingerprint"],
                                prior["plot_fingerprint"])
            output = Path(root) / "report.json"
            result = report(target, output, history=[data["proposals"][0]])
            self.assertFalse(result["automatic_publication_enabled"])
            self.assertGreater(result["requires_editorial_review"], 0)

    def test_malformed_present_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            publisher = Path(root) / "state.json"
            publisher.write_text('{"published": []}')
            with self.assertRaises(ValueError):
                load_history(publisher, Path(root) / "absent.json")


if __name__ == "__main__":
    unittest.main()
