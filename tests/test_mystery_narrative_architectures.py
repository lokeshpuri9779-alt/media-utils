import unittest
from astra_v2.autonomous_story_proposals import EMOTIONAL_TURNS, NARRATIVE_ARCHITECTURES, PRESSURE_ARCS, proposal
from astra_v2.publication_quality import publication_rejection


class NarrativeArchitecturesTests(unittest.TestCase):
    def test_pressure_arc_coverage_and_safe_generation(self):
        seen = set()
        for index in range(320):
            story = proposal(index)
            narration = " ".join(beat["speech"] for beat in story["story_beats"])
            self.assertNotIn("..", narration)
            for number, (complication, reversal, payoff) in enumerate(PRESSURE_ARCS):
                if complication in narration:
                    seen.add(number)
                    self.assertIn(reversal, narration)
                    self.assertIn(payoff, narration)
            self.assertEqual(story, proposal(index))
            self.assertFalse(story["production_ready"])
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")
        self.assertEqual(seen, set(range(len(PRESSURE_ARCS))))

    def test_all_narrative_architectures_shape_the_four_beats(self):
        seen = set()
        for index in range(320):
            story = proposal(index)
            narration = " ".join(beat["speech"] for beat in story["story_beats"])
            self.assertEqual(len(story["story_beats"]), 4)
            for number, architecture in enumerate(NARRATIVE_ARCHITECTURES):
                if architecture[0] in narration:
                    seen.add(number)
                    for stage in architecture:
                        self.assertIn(stage, narration)
            self.assertFalse(story["production_ready"])
        self.assertEqual(seen, set(range(len(NARRATIVE_ARCHITECTURES))))

    def test_character_emotional_turns_are_used_without_new_mysteries(self):
        seen = set()
        for index in range(320):
            story = proposal(index)
            narration = " ".join(beat["speech"] for beat in story["story_beats"])
            for number, emotional_turn in enumerate(EMOTIONAL_TURNS):
                if emotional_turn in narration:
                    seen.add(number)
                    self.assertIn("The setback changed the team's mood", narration)
            self.assertEqual(story, proposal(index))
            self.assertFalse(story["production_ready"])
        self.assertEqual(seen, set(range(len(EMOTIONAL_TURNS))))


if __name__ == "__main__":
    unittest.main()
