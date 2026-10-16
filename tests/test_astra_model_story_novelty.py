import unittest
from unittest.mock import patch
from astra_v2 import openai_creative


class ModelNoveltyTests(unittest.TestCase):
    def test_model_disabled_by_default(self):
        with patch.object(openai_creative, "enabled", return_value=False):
            self.assertIsNone(openai_creative.generate(set(), set(), []))

    def test_model_generation_receives_history_argument(self):
        import inspect
        params = inspect.signature(openai_creative.generate).parameters
        self.assertIn("prior_stories", params)
        source = inspect.getsource(openai_creative.generate)
        self.assertIn("is_near_duplicate(story, prior_stories)", source)
        self.assertIn("planning_issues(story)", source)


if __name__ == "__main__":
    unittest.main()
