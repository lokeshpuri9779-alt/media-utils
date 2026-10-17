import unittest
from astra_v2.autonomous_story_proposals import proposal
from astra_v2.proposal_novelty_index import NoveltyIndex
from astra_v2.shorts_novelty import is_near_duplicate


class ProposalNoveltyIndexTests(unittest.TestCase):
    def test_matches_reference_for_generated_inventory(self):
        prior = [proposal(i) for i in range(120)]
        index = NoveltyIndex(prior)
        for i in range(130):
            candidate = proposal(i)
            self.assertEqual(index.is_near_duplicate(candidate),
                             is_near_duplicate(candidate, prior))

    def test_incremental_add_and_validation(self):
        index = NoveltyIndex()
        story = proposal(7)
        self.assertFalse(index.is_near_duplicate(story))
        index.add(story)
        self.assertTrue(index.is_near_duplicate(story))
        with self.assertRaises(ValueError):
            index.is_near_duplicate(story, threshold=0)


if __name__ == "__main__":
    unittest.main()
