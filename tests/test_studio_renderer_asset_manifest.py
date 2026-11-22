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
            "single continuous full-bleed scene",
            "one coherent camera view",
            "no split-screen",
            "no collage",
            "no storyboard grid",
            "no tiled panels",
            "no contact sheet",
        ):
            with self.subTest(required=required):
                self.assertIn(required, item["query"].lower())

    def test_non_story_artwork_brief_is_not_rewritten_as_story_illustration(self):
        story = {"genre": "current", "title": "Market update"}
        plan = [{"director_asset": "source-document",
                 "director_semantics": ["evidence"]}]
        item = asset_manifest(story, plan)[0]
        self.assertEqual(item["strategy"], "original-motion")
        self.assertNotIn("no split-screen", item["query"].lower())


if __name__ == "__main__":
    unittest.main()
