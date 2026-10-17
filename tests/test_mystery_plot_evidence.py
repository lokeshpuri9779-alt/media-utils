import unittest
from astra_v2.autonomous_story_proposals import PLOT_EVIDENCE, PLOT_ENGINES, proposal
from astra_v2.publication_quality import publication_rejection


class PlotEvidenceTests(unittest.TestCase):
    def test_evidence_and_verification_match_each_plot(self):
        self.assertEqual(len(PLOT_EVIDENCE), len(PLOT_ENGINES))
        for i in range(176):
            story = proposal(i)
            evidence, verification = PLOT_EVIDENCE[(i // 11) % len(PLOT_EVIDENCE)]
            self.assertIn(evidence, story["story_beats"][1]["speech"])
            self.assertIn(verification, story["story_beats"][2]["speech"])
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")


if __name__ == "__main__":
    unittest.main()
