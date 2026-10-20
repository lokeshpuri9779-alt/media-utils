"""Repair transition should visibly progress and preserve later clean frames."""
import unittest
from PIL import Image, ImageDraw
from astra_v2.pillow_duo_scene import _prop
from astra_v2.prop_state_continuity import assign_prop_states


def render(name, time, transition):
    image = Image.new("RGB", (320, 320), (250, 250, 250))
    _prop(ImageDraw.Draw(image), name, 160, 160, time,
          condition="repaired", repair_transition=transition)
    return image.tobytes()


class RepairAnimationTests(unittest.TestCase):
    def test_repair_beat_is_flagged_only_after_damage(self):
        shots = assign_prop_states([
            {"story_prop": "box", "speech": "The gift broke."},
            {"story_prop": "box", "speech": "They repaired the gift."},
            {"story_prop": "box", "speech": "They carried the gift."}])
        self.assertTrue(shots[1]["story_prop_repair_transition"])
        self.assertNotIn("story_prop_repair_transition", shots[2])

    def test_damage_contracts_into_clean_artwork(self):
        for name in ("box", "book", "ball", "flower", "lantern"):
            with self.subTest(name=name):
                early = render(name, 0, True)
                middle = render(name, .8, True)
                clean = render(name, 2, True)
                self.assertNotEqual(early, middle)
                self.assertNotEqual(middle, clean)
                self.assertEqual(clean, render(name, 2, False))


if __name__ == "__main__":
    unittest.main()
