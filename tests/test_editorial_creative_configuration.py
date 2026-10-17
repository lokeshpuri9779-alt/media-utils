"""Regression tests for opt-in editorial source configuration."""
import os
import unittest
from unittest.mock import patch

from astra_v2.creative import CreativeSkip
from astra_v2.editorial_creative_source import load_editorial_stories


class EditorialCreativeConfigurationTests(unittest.TestCase):
    def test_partial_editorial_configuration_fails_closed(self):
        with patch.dict(os.environ, {
            "ASTRA_EDITORIAL_STORIES_FILE": "missing-stories.json",
            "ASTRA_EDITORIAL_REVIEWS_FILE": "",
        }):
            with self.assertRaisesRegex(CreativeSkip, "editorial_intake_incomplete_configuration"):
                load_editorial_stories()

    def test_missing_history_fails_closed(self):
        with patch.dict(os.environ, {
            "ASTRA_EDITORIAL_STORIES_FILE": "/tmp/absent-editorial-stories.json",
            "ASTRA_EDITORIAL_REVIEWS_FILE": "/tmp/absent-editorial-reviews.json",
            "ASTRA_PUBLISHER_STATE_PATH": "/tmp/absent-editorial-state.json",
            "ASTRA_STORY_HISTORY_PATH": "/tmp/absent-editorial-history.json",
        }):
            with self.assertRaisesRegex(CreativeSkip, "editorial_intake_unavailable"):
                load_editorial_stories()


if __name__ == "__main__":
    unittest.main()
