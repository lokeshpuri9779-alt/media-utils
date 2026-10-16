import unittest
from astra_v2.autonomous_story_proposals import proposal
from astra_v2.production_story_gate import candidate_issues, approved_authored_candidates
from astra_v2.story_forge import catalog


class ProductionStoryGateTests(unittest.TestCase):
    def test_unreviewed_proposals_never_auto_approved(self):
        draft = proposal(0)
        self.assertIn("not_reviewed_authored_story", candidate_issues(draft))
        self.assertEqual(approved_authored_candidates([draft]), [])

    def test_reviewed_forge_story_can_pass_without_bypassing_gates(self):
        stories = catalog(limit=256)
        approved = approved_authored_candidates(stories)
        self.assertTrue(all(s["kind"] == "authored_causal_story" and
                            s["production_ready"] is True for s in approved))
        self.assertTrue(all(not candidate_issues(s) for s in approved))

    def test_novelty_excludes_published_fingerprint(self):
        approved = approved_authored_candidates(catalog(limit=256))
        if not approved:
            self.skipTest("No authored story passes editorial checks")
        story = approved[0]
        self.assertIn("narrative_duplicate",
                      candidate_issues(story, [{"plot_fingerprint": story["plot_fingerprint"]}]))
        self.assertEqual(approved_authored_candidates([story],
                         [{"plot_fingerprint": story["plot_fingerprint"]}]), [])


if __name__ == "__main__":
    unittest.main()
