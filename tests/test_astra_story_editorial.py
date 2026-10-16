import unittest
from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_editorial import editorial_issues, triage


class StoryEditorialTests(unittest.TestCase):
    def test_proposals_never_auto_approved(self):
        story = proposal(0)
        result = triage([story])
        self.assertEqual(len(result["ready_for_review"]), 1)
        self.assertEqual(result["needs_work"], [])
        self.assertTrue(result["ready_for_review"][0]["publication_blocked"])
        self.assertTrue(result["ready_for_review"][0]["awaiting_editorial_decision"])
        self.assertIn("human_or_model_editorial_review_required", result["ready_for_review"][0]["issues"])
        self.assertFalse(story["production_ready"])

    def test_repeated_story_rejected(self):
        story = proposal(1)
        self.assertIn("narrative_duplicate", editorial_issues(story, [story]))


if __name__ == "__main__":
    unittest.main()
