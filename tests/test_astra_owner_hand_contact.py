"""Explicit duo owner determines the held object's visible hand position."""
import unittest
from PIL import Image
from astra_v2.pillow_duo_scene import draw_duo


class OwnerAwareContactTests(unittest.TestCase):
    def render(self, owner):
        image = Image.new("RGB", (1080, 1920), (255, 255, 255))
        shot = {"story_cast": ["fox", "rabbit"], "story_prop": "box",
                "story_action": "hold", "story_visual_seed": "owner-test",
                "story_prop_owner": owner}
        self.assertTrue(draw_duo(image, shot, 1.5))
        return image.tobytes()

    def test_named_second_character_changes_contact_position(self):
        self.assertNotEqual(self.render("fox"), self.render("rabbit"))

    def test_unrecognized_owner_uses_legacy_placement(self):
        self.assertEqual(self.render("unknown"), self.render(None))


if __name__ == "__main__":
    unittest.main()
