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
        self.assertGreaterEqual(match["jaccard_similarity"], match["jaccard_threshold"])

    def test_fingerprint_match_is_reported_even_without_text_overlap(self):
        first = {"content_id": "story-fp", "title": "Earlier", "plot_fingerprint": "same-plot", "story_beats": [{"speech": "blue"}]}
        second = {"content_id": "story-fp-new", "title": "New", "plot_fingerprint": "same-plot", "story_beats": [{"speech": "orange"}]}
        from astra_v2.story_editorial import semantic_duplicate_match
        match = semantic_duplicate_match(second, [first])
        self.assertTrue(match["plot_fingerprint_match"])
        self.assertEqual(match["matched_content_id"], "story-fp")

    def test_high_overlap_plot_is_flagged_below_old_threshold(self):
        first = {"story_beats": [{"speech": "A curious fox investigates a broken bridge light before winter. The fox compares the wiring with a metal part and discovers the cause."}]}
        second = {"story_beats": [{"speech": "A curious fox investigates a broken bridge light before winter. The fox compares the wiring with a metal part and discovers the cause, then repairs it."}]}
        from astra_v2.story_editorial import is_semantic_near_duplicate
        self.assertTrue(is_semantic_near_duplicate(second, [first]))

    def test_same_animal_tag_can_have_three_distinct_visual_shots(self):
        from astra_v2.story_editorial import visual_prompt_variety_count
        story = {"story_beats": [
            {"visual": "fox", "speech": "A fox finds a bell beside the forest stream before the evening rain arrives.",
             "visual_prompt": "A fox finds a brass bell beside a forest stream."},
            {"visual": "fox", "speech": "The fox follows the sound along a narrow forest trail toward the old marker.",
             "visual_prompt": "A fox follows the ringing bell along a winding forest trail."},
            {"visual": "fox", "speech": "The fox pauses beneath a branch and listens before choosing the safer route.",
             "visual_prompt": "A fox listens beneath a high forest branch as leaves move overhead."},
            {"visual": "fox", "speech": "The fox returns the bell to its marker and guides the others home safely.",
             "visual_prompt": "A fox places the bell beside a wooden marker in a forest clearing."},
        ]}
        self.assertEqual(visual_prompt_variety_count(story["story_beats"]), 4)
        self.assertNotIn("insufficient_visual_variety", editorial_issues(story))

    def test_identical_shots_fail_visual_variety_even_with_valid_animal_tags(self):
        from astra_v2.story_editorial import visual_prompt_variety_count
        prompt = "A fox stands beside a forest stream and looks toward the moonlight."
        story = {"story_beats": [
            {"visual": "fox", "speech": "A fox watches the quiet forest stream while the evening light fades away.",
             "visual_prompt": prompt}
            for _ in range(4)
        ]}
        self.assertEqual(visual_prompt_variety_count(story["story_beats"]), 1)
        self.assertIn("insufficient_visual_variety", editorial_issues(story))

    def test_distinct_story_text_is_not_automatically_duplicate(self):
        first = proposal(21)
        second = proposal(88)
        self.assertNotIn("narrative_duplicate", editorial_issues(second, [first]))


if __name__ == "__main__":
    unittest.main()
