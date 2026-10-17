"""Regression coverage for the existing ASTRA causal planning and novelty gates.

No publication decisions are modified by these tests.
"""
import unittest

from astra_v2.story_planning import planning_issues
from astra_v2.story_editorial import editorial_issues, semantic_duplicate_match


def story(identity, suffix=""):
    texts = [
        "A careful fox found a broken bridge beside the river " + suffix,
        "The fox tried a rope but the current pulled it away " + suffix,
        "After noticing strong roots the fox anchored a safer crossing " + suffix,
        "The villagers crossed safely and repaired the old bridge together " + suffix,
    ]
    return {
        "content_id": identity,
        "title": "The River Crossing",
        "plot_fingerprint": identity,
        "story_beats": [
            {"story_beat": role, "speech": text,
             "visual": "distinct scene " + str(i)}
            for i, (role, text) in enumerate(zip(
                ("reveal", "build", "twist", "payoff"), texts))
        ],
    }


class EditorialRegression(unittest.TestCase):
    def test_valid_four_beat_story(self):
        self.assertEqual(planning_issues(story("original")), [])

    def test_invalid_causal_order(self):
        candidate = story("wrong-order")
        candidate["story_beats"][0]["story_beat"] = "payoff"
        self.assertIn("missing_causal_story_progression", planning_issues(candidate))

    def test_duplicate_fingerprint_is_detected(self):
        original = story("same-plot")
        candidate = story("same-plot", "with a different surface description")
        match = semantic_duplicate_match(candidate, [original])
        self.assertIsNotNone(match)
        self.assertTrue(match["plot_fingerprint_match"])

    def test_duplicate_story_is_flagged_for_review(self):
        original = story("same-plot")
        candidate = story("same-plot")
        self.assertIn("narrative_duplicate", editorial_issues(candidate, [original]))

    def test_no_history_does_not_create_duplicate(self):
        self.assertNotIn("narrative_duplicate", editorial_issues(story("new"), []))


if __name__ == "__main__":
    unittest.main()
