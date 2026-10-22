import unittest
from pathlib import Path


class ArtReviewBindingContract(unittest.TestCase):
    def test_restores_persisted_editorial_pair(self):
        workflow = Path(".github/workflows/astra-gemini-art-staging.yml").read_text()
        self.assertIn("runtime-health/ai-reviewed-stories.json", workflow)
        self.assertIn("runtime-health/ai-reviewed-decisions.json", workflow)
        self.assertIn("Require complete persisted editorial review pair", workflow)

    def test_semantic_review_rejects_scene_order_mismatch(self):
        source = Path("astra_v2/gemini_art_semantic_review.py").read_text()
        self.assertIn("story_scene_order_mismatch", source)
        self.assertIn("invalid_story_beat", source)


if __name__ == "__main__":
    unittest.main()
