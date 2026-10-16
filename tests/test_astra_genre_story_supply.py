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

    def test_balances_underrepresented_structures(self):
        from astra_v2.genre_story_supply import balanced_structure_index, NARRATIVE_STRUCTURES
        recent = [{"plot_structure": row[0]} for row in NARRATIVE_STRUCTURES[:-1] for _ in range(4)]
        selected = balanced_structure_index(123, recent)
        self.assertEqual(NARRATIVE_STRUCTURES[selected][0], NARRATIVE_STRUCTURES[-1][0])
        story = genre_proposal(123, structure_index=selected)
        self.assertEqual(story["plot_structure"], NARRATIVE_STRUCTURES[-1][0])

    def test_expanded_scenario_catalog(self):
        self.assertGreaterEqual(len(SCENARIOS), 24)
        self.assertEqual(len({(item[0], item[3]) for item in SCENARIOS}), len(SCENARIOS))

    def test_character_decision_variety(self):
        from astra_v2.genre_story_supply import INNER_CONFLICTS, CHARACTER_DECISIONS
        self.assertGreaterEqual(len(INNER_CONFLICTS), 8)
        self.assertGreaterEqual(len(CHARACTER_DECISIONS), 8)
        speeches = [genre_proposal(i)["story_beats"][1]["speech"] for i in range(256)]
        self.assertTrue(all(any(choice in speech for choice in CHARACTER_DECISIONS) for speech in speeches))

    def test_character_arc_is_causally_linked(self):
        from astra_v2.genre_story_supply import CHARACTER_ARCS
        for index in range(256):
            story = genre_proposal(index)
            opening, choice, growth = CHARACTER_ARCS[(index // 19) % len(CHARACTER_ARCS)]
            self.assertIn(opening, story["story_beats"][0]["speech"])
            self.assertIn(choice, story["story_beats"][1]["speech"])
            self.assertIn(growth, story["story_beats"][3]["speech"])
            self.assertEqual(story["character_arc_id"], opening)

    def test_character_choice_unlocks_external_plot(self):
        from astra_v2.genre_story_supply import ARC_PLOT_BRIDGES, CHARACTER_ARCS
        self.assertEqual(len(ARC_PLOT_BRIDGES), len(CHARACTER_ARCS))
        for index in range(512):
            story = genre_proposal(index)
            arc_index = (index // 19) % len(ARC_PLOT_BRIDGES)
            blocked, unlocked = ARC_PLOT_BRIDGES[arc_index]
            build = story["story_beats"][1]["speech"]
            self.assertLess(build.index(blocked), build.index(CHARACTER_ARCS[arc_index][1]))
            self.assertLess(build.index(CHARACTER_ARCS[arc_index][1]), build.index(unlocked))
            self.assertEqual(story["plot_dependency_id"], arc_index)
            self.assertFalse(story["production_ready"])
            self.assertTrue(publication_rejection(story))

    def test_reject_negative_index(self):
        with self.assertRaises(ValueError):
            genre_proposal(-1)


if __name__ == "__main__":
    unittest.main()
