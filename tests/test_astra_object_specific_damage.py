"""Verify each illustrated prop has its own damaged appearance."""
import unittest
from PIL import Image, ImageDraw
from astra_v2.pillow_duo_scene import _prop


def render(name, condition):
    image = Image.new("RGB", (300, 300), (250, 250, 250))
    _prop(ImageDraw.Draw(image), name, 150, 150, 0, condition=condition)
    return image.tobytes()


class ObjectSpecificDamageTests(unittest.TestCase):
    def test_damage_differs_from_clean_for_every_illustrated_prop(self):
        for name in ("box", "book", "ball", "flower", "lantern"):
            with self.subTest(prop=name):
                self.assertNotEqual(render(name, "damaged"),
                                    render(name, "repaired"))

    def test_repaired_matches_intact_for_every_illustrated_prop(self):
        for name in ("box", "book", "ball", "flower", "lantern"):
            with self.subTest(prop=name):
                self.assertEqual(render(name, "repaired"),
                                 render(name, "intact"))

    def test_damage_looks_different_across_prop_types(self):
        self.assertNotEqual(render("box", "damaged"), render("book", "damaged"))


if __name__ == "__main__":
    unittest.main()
