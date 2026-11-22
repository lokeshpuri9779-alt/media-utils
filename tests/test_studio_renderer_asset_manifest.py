"""Regression tests for story artwork acquisition briefs."""
import unittest
from studio_renderer import asset_manifest


class StoryArtworkManifestTests(unittest.TestCase):
    def test_story_illustration_requires_one_continuous_composition(self):
        story = {"genre": "fiction", "title": "The Tomorrow Signal"}
        plan = [{
            "director_asset": "editorial-illustration",
            "story_environment": "underwater",
            "visual_prompt": "Mara discovers a second sea door beside her brother's notebook.",
            "director_semantics": ["clock"],
        }]
        item = asset_manifest(story, plan)[0]
        self.assertEqual(item["strategy"], "original-illustration")
        for required in (
            "single full-bleed camera view",
            "no collage",
            "no panels",
        ):
            with self.subTest(required=required):
                self.assertIn(required, item["query"].lower())

    def test_episode_four_uses_authored_underwater_notebook_composition(self):
        story = {"genre": "fiction", "title": "The Tomorrow Signal"}
        plan = [{
            "director_asset": "editorial-illustration",
            "story_environment": "underwater",
            "speech": "The door sealed and stars returned. Her brother's notebook contained a new page.",
            "story_human_action": "seal_and_reveal_sea_door",
        }]
        item = asset_manifest(story, plan)[0]
        query = item["query"].lower()
        self.assertIn("mara holds her brother", query)
        self.assertIn("open notebook", query)
        self.assertIn("underwater door", query)
        self.assertIn("tomorrow's date", query)
        self.assertLessEqual(len(item["query"]), 240)

    def test_episode_four_action_briefs_are_not_truncated_by_composition_rules(self):
        story = {"genre": "fiction", "title": "The Tomorrow Signal"}
        actions = [
            ("face_duplicate_at_countdown", "two distinct versions of mara"),
            ("warn_parallel_cities", "two cities"),
            ("split_glass_key", "breaking a blue glass key"),
        ]
        for action, expected in actions:
            with self.subTest(action=action):
                item = asset_manifest(story, [{
                    "director_asset": "editorial-illustration",
                    "story_environment": "observatory",
                    "story_human_action": action,
                    "speech": "Long narration that should not replace authored composition.",
                }])[0]
                self.assertIn(expected, item["query"].lower())
                self.assertLessEqual(len(item["query"]), 240)

    def test_non_story_artwork_brief_is_not_rewritten_as_story_illustration(self):
        story = {"genre": "current", "title": "Market update"}
        plan = [{"director_asset": "source-document",
                 "director_semantics": ["evidence"]}]
        item = asset_manifest(story, plan)[0]
        self.assertEqual(item["strategy"], "original-motion")
        self.assertNotIn("no split-screen", item["query"].lower())


if __name__ == "__main__":
    unittest.main()
