"""Plot-first proposals must remain quarantined."""
import unittest
from astra_v2.plot_first_proposals import proposals
from astra_v2.production_story_gate import candidate_issues


class PlotFirstProposalTests(unittest.TestCase):
    def test_proposals_are_distinct_and_never_approved(self):
        rows = proposals(limit=12)
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({r["content_id"] for r in rows}), 12)
        self.assertEqual(len({r["plot_fingerprint"] for r in rows}), 12)
        self.assertTrue(all(r["production_ready"] is False for r in rows))
        self.assertTrue(all(r["kind"] == "unreviewed_causal_draft" for r in rows))
        self.assertTrue(all("not_reviewed_authored_story" in candidate_issues(r) for r in rows))

    def test_history_fingerprint_exclusion(self):
        first = proposals(limit=1)[0]
        second = proposals(limit=1, excluded_plot_hashes=[first["plot_fingerprint"]])[0]
        self.assertNotEqual(first["plot_fingerprint"], second["plot_fingerprint"])


if __name__ == "__main__":
    unittest.main()
