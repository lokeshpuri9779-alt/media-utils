"""Prevent misleading generic visuals for named unsupported protagonists."""
import unittest
from unittest.mock import patch

from astra_errors import CreativeReject
from astra_v2.unified_story_engine import validate_title_subject


class NamedCharacterVisualTests(unittest.TestCase):
    def test_screenshot_species_supported(self):
        for animal in ("Tapir", "Pangolin", "Stoat", "Lynx", "Ferret", "Marten"):
            with self.subTest(animal=animal):
                validate_title_subject({"genre": "fiction", "title": "The "+animal+" and the Mangrove Bell"})

    def test_new_species_resolve_to_solo_actors(self):
        from astra_v2.unified_story_engine import validate_story_shot
        for animal in ("tapir", "pangolin", "stoat", "lynx", "ferret", "marten"):
            with self.subTest(animal=animal):
                self.assertEqual(validate_story_shot({"speech": "The "+animal+" found a lantern"}), "solo")

    def test_supported_cast_still_allowed(self):
        for animal in ("Fox", "Rabbit", "Otter", "Owl"):
            validate_title_subject({"genre": "fiction", "title": "The "+animal+" and the Lantern"})

    def test_nonfiction_not_affected(self):
        validate_title_subject({"genre": "news", "title": "A Tapir Conservation Report"})

    def test_not_triggered_by_partial_word(self):
        validate_title_subject({"genre": "fiction", "title": "The Lynxwood Clock"})


if __name__ == "__main__":
    unittest.main()
