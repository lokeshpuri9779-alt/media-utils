"""Deterministic, non-publishing scale checks for ASTRA's existing quality reviewer."""
import random
import unittest

from astra_v2.unified_quality_review import review_storyboard

ACTIONS = ("pick", "carry", "repair", "open", "walk", "jump", "push", "catch")
SCENES = ("village", "harbor", "library", "forest", "museum", "observatory")


def sample_story(seed):
    rng = random.Random(seed)
    actions = rng.sample(ACTIONS, 3)
    scenes = rng.sample(SCENES, 3)
    return {"story_beats": [
        {"story_action": action, "story_environment": scene}
        for action, scene in zip(actions, scenes)
    ]}


class StoryQualityScaleAudit(unittest.TestCase):
    def test_thousand_deterministic_storyboards(self):
        """Stress diagnostic contract, not real story generation or creative quality."""
        for seed in range(1000):
            with self.subTest(seed=seed):
                story = sample_story(seed)
                first = review_storyboard(story)
                self.assertEqual(first, review_storyboard(story))
                self.assertEqual(first["publication_decision"], "unchanged")
                self.assertEqual(first["enforcement"], "diagnostic_only")
                self.assertEqual(first["findings"], [])
                self.assertEqual(first["actions"], 3)
                self.assertEqual(first["scenes"], 3)

    def test_repetitive_story_is_flagged_without_publication_override(self):
        story = {"story_beats": [
            {"story_action": "idle", "story_environment": "forest"}
            for _ in range(4)
        ]}
        result = review_storyboard(story)
        self.assertIn("limited_action_variety", result["findings"])
        self.assertIn("limited_scene_variety", result["findings"])
        self.assertEqual(result["publication_decision"], "unchanged")


if __name__ == "__main__":
    unittest.main()
