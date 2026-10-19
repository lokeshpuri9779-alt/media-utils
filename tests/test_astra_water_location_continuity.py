"""Keep the authored environment stable unless a water-body location is named."""
import unittest

from astra_v2.pillow_scene_direction import story_setting


class StoryLocationContinuityTests(unittest.TestCase):
    def test_water_props_do_not_move_village_to_river(self):
        for speech in ("She filled the fountain with water.",
                       "The floating gift drifted beside the fountain.",
                       "A sudden flood threatened the market."):
            with self.subTest(speech=speech):
                self.assertEqual(story_setting({"speech": speech,
                    "story_environment": "village"}), "village")

    def test_explicit_river_location_overrides_village(self):
        self.assertEqual(story_setting({"speech": "They reached the river bank.",
            "story_environment": "village"}), "river")

    def test_other_explicit_location_remains_authoritative(self):
        self.assertEqual(story_setting({"speech": "They entered the museum.",
            "story_environment": "village"}), "museum")


if __name__ == "__main__":
    unittest.main()
