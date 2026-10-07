import unittest

from character_pilot import dry_run


class CharacterPilotTests(unittest.TestCase):
    def test_dry_run_builds_reference_style_story_without_spend(self):
        result=dry_run()
        self.assertEqual(result["format"],"family_3d_animal_comedy")
        self.assertEqual(result["scene_count"],7)
        self.assertFalse(result["spend_attempted"])
        self.assertTrue(result["character_bible"])
        self.assertEqual(len(result["storyboard"]),7)


if __name__=="__main__":
    unittest.main()
