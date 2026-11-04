import unittest
from astra_v2.original_moral_story_patterns import PATTERNS, pattern_for, prompt_for
from astra_v2.plot_first_proposals import proposals


class MoralPatternTests(unittest.TestCase):
    def test_all_patterns_are_nonpublishing(self):
        for i in range(len(PATTERNS)):
            result = pattern_for(i)
            self.assertFalse(result["production_ready"])
            self.assertFalse(result["publication_approved"])
            self.assertIn("Consequence:", prompt_for(i))

    def test_invalid_index(self):
        with self.assertRaises(ValueError):
            pattern_for(-1)

    def test_plot_first_drafts_remain_unreviewed(self):
        candidates = proposals(limit=2)
        self.assertTrue(candidates)
        for story in candidates:
            self.assertIn(story["narrative_design"]["pattern_id"], PATTERNS)
            self.assertIs(story["production_ready"], False)
            self.assertIs(story["narrative_design"]["publication_approved"], False)


if __name__ == "__main__":
    unittest.main()
