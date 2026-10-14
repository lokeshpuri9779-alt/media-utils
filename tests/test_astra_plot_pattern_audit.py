import unittest
from astra_v2.plot_pattern_audit import plot_signature, plot_repetition
from astra_v2.story_diversity_audit import audit_history

def story(*beats):
    return {"scenes": [{"narration": beat, "action": "react"} for beat in beats]}

class PlotPatternTests(unittest.TestCase):
    def test_repeated_plot_different_props(self):
        first = story("The cat finds a missing cake.", "Together they discover a clue.", "The friends celebrate.")
        second = story("The dog finds a missing key.", "Together they discover a clue.", "The friends celebrate.")
        self.assertTrue(plot_repetition(first, second))
        result = audit_history([second], history=[first])
        self.assertEqual(result["near_duplicates"], 1)
        self.assertTrue(result["results"][0]["repeated_plot_pattern"])

    def test_different_plot_not_flagged(self):
        first = story("A missing cake.", "The friends find a clue.", "They return it.")
        second = story("A broken clock.", "They repair it.", "The clock works.")
        self.assertFalse(plot_repetition(first, second))

    def test_empty_stories_not_plot_duplicates(self):
        self.assertFalse(plot_repetition(story(), story()))
        self.assertEqual(plot_signature(story()), ())

    def test_generic_cooperation_alone_not_duplicate(self):
        self.assertFalse(plot_repetition(story("Friends gather.", "Together they laugh."),
                                         story("Friends gather.", "Together they laugh.")))

    def test_single_conflict_cue_not_sufficient(self):
        self.assertFalse(plot_repetition(story("A missing lamp.", "The sun rises."),
                                         story("A missing bell.", "The rain falls.")))

    def test_different_beat_count_not_flagged(self):
        self.assertFalse(plot_repetition(story("A missing key."), story("A missing key.", "A clue.")))

    def test_common_unclassified_words_not_duplicate(self):
        self.assertFalse(plot_repetition(story("The sun rises."), story("The rain falls.")))

if __name__ == "__main__":
    unittest.main()
