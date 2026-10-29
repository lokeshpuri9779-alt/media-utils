"""Dependency-free regression for visible character actions in directed scenes."""
import unittest

from astra_v2.directed_scene_contract import directed_scene_issue


class HumanoidSceneFidelityTests(unittest.TestCase):
    def test_clothed_character_cannot_be_replaced_by_forest_backdrop(self):
        shot = {
            "visual": "forest",
            "speech": "Look at the central leaves, Rowan!",
            "visual_prompt": (
                "Bramble pointing at a withered root system. "
                "Bramble has messy auburn hair and a moss-green tunic. "
                "Rowan stands beside him holding a rusted trowel."
            ),
        }
        self.assertEqual(
            directed_scene_issue(shot),
            "embodied_character_not_supported_by_directed_icons",
        )

    def test_natural_landscape_does_not_need_character_art(self):
        self.assertIsNone(directed_scene_issue({
            "visual": "forest",
            "speech": "The forest glows after rain.",
            "visual_prompt": "Sunlight filters through the forest canopy.",
        }))

    def test_appearance_without_action_does_not_trigger_two_cue_rule(self):
        self.assertIsNone(directed_scene_issue({
            "visual": "forest",
            "speech": "The forest is quiet.",
            "visual_prompt": "A coat hangs from a branch above the moss.",
        }))


if __name__ == "__main__":
    unittest.main()
