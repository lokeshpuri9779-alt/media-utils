import unittest
from astra_v2.shorts_novelty import is_near_duplicate, structural_signature


class StructuralNoveltyTests(unittest.TestCase):
    def test_rejects_same_premise_outcome_despite_rewording(self):
        first = {"genre": "comedy", "plot_structure": "quest", "premise_id": "lost-prize", "outcome_id": "shared-win", "story_beats": [{"speech": "A fox chased a missing prize."}]}
        second = {"genre": "comedy", "plot_structure": "quest", "premise_id": "lost-prize", "outcome_id": "shared-win", "story_beats": [{"speech": "A penguin found a very unusual solution."}]}
        self.assertTrue(is_near_duplicate(second, [first]))

    def test_distinct_outcome_not_structural_duplicate(self):
        first = {"genre": "comedy", "plot_structure": "quest", "premise_id": "lost-prize", "outcome_id": "shared-win"}
        second = dict(first, outcome_id="surprise-gift")
        self.assertNotEqual(structural_signature(first), structural_signature(second))

    def test_legacy_stories_remain_supported(self):
        self.assertIsNone(structural_signature({"story_beats": []}))


if __name__ == "__main__":
    unittest.main()
