"""Consequences and verification must be grounded in the story problem."""
import unittest
from astra_v2.plot_first_proposals import consequence_for, proposals


class ConsequenceTests(unittest.TestCase):
    def test_specific_consequences_differ(self):
        self.assertNotEqual(consequence_for("broken bridge"), consequence_for("stalled ferry"))

    def test_cost_and_verification_are_narrated(self):
        stories = proposals(limit=10)
        self.assertEqual(len(stories), 10)
        for story in stories:
            self.assertIn(story["consequence"], story["story_beats"][1]["speech"])
            self.assertIn(story["verification"], story["story_beats"][3]["speech"])
            self.assertFalse(story["production_ready"])


if __name__ == "__main__":
    unittest.main()
