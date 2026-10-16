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

    def test_semantic_duplicate_ignores_title_and_generated_id(self):
        original = proposal(17)
        changed = dict(original)
        changed["content_id"] = "different-id"
        changed["title"] = "A completely different title"
        self.assertIn("narrative_duplicate", editorial_issues(changed, [original]))

    def test_semantic_duplicate_reports_match_evidence(self):
        first = {"content_id": "story-a", "title": "First", "story_beats": [{"speech": "A curious fox investigates a broken bridge light before winter. The fox compares the wiring with a metal part and discovers the cause."}]}
        second = {"content_id": "story-b", "title": "Second", "story_beats": [{"speech": "A curious fox investigates a broken bridge light before winter. The fox compares the wiring with a metal part and discovers the cause, then repairs it."}]}
        from astra_v2.story_editorial import semantic_duplicate_match
        match = semantic_duplicate_match(second, [first])
        self.assertIsNotNone(match)
        self.assertEqual(match["matched_content_id"], "story-a")
        self.assertGreaterEqual(match["similarity"], match["threshold"])

    def test_high_overlap_plot_is_flagged_below_old_threshold(self):
        first = {"story_beats": [{"speech": "A curious fox investigates a broken bridge light before winter. The fox compares the wiring with a metal part and discovers the cause."}]}
        second = {"story_beats": [{"speech": "A curious fox investigates a broken bridge light before winter. The fox compares the wiring with a metal part and discovers the cause, then repairs it."}]}
        from astra_v2.story_editorial import is_semantic_near_duplicate
        self.assertTrue(is_semantic_near_duplicate(second, [first]))

    def test_distinct_story_text_is_not_automatically_duplicate(self):
        first = proposal(21)
        second = proposal(88)
        self.assertNotIn("narrative_duplicate", editorial_issues(second, [first]))


if __name__ == "__main__":
    unittest.main()
