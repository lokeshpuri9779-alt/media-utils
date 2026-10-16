import unittest
from astra_v2.genre_story_supply import SCENARIOS, genre_proposal
from astra_v2.publication_quality import publication_rejection


class GenreStorySupplyTests(unittest.TestCase):
    def test_eight_genres_and_causal_beats(self):
        stories = [genre_proposal(i) for i in range(64)]
        self.assertEqual(len({item["genre"] for item in stories}), 8)
        self.assertEqual(len({item["plot_fingerprint"] for item in stories}), 64)
        for item in stories:
            self.assertEqual([beat["story_beat"] for beat in item["story_beats"]], ["reveal", "build", "twist", "payoff"])
            self.assertFalse(item["production_ready"])
            self.assertTrue(publication_rejection(item))

    def test_expanded_motivations_partners_and_payoffs(self):
        stories = [genre_proposal(i) for i in range(512)]
        self.assertEqual(len({story["plot_fingerprint"] for story in stories}), 512)
        self.assertGreaterEqual(len({story["story_beats"][0]["speech"] for story in stories}), 64)
        self.assertGreaterEqual(len({story["story_beats"][3]["speech"] for story in stories}), 64)
        self.assertTrue(all(not story["production_ready"] for story in stories))

    def test_eight_narrative_structures(self):
        stories = [genre_proposal(i) for i in range(128)]
        self.assertEqual(len({story["plot_structure"] for story in stories}), 8)
        self.assertTrue(all(story["premise_id"] and story["outcome_id"] for story in stories))

    def test_reject_negative_index(self):
        with self.assertRaises(ValueError):
            genre_proposal(-1)


if __name__ == "__main__":
    unittest.main()
