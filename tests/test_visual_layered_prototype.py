"""Offline quality and determinism checks for the experimental layered painter."""
import unittest
from PIL import Image
from astra_v2.visual_layered_prototype import render_layered_scene
from astra_v2.visual_artifact_library import SCENES


class LayeredPrototypeTests(unittest.TestCase):
    def test_all_scenes_have_correct_dimensions(self):
        for scene in SCENES:
            with self.subTest(scene=scene):
                result = render_layered_scene(scene, "qa")
                self.assertEqual(result.size, (1080, 1920))
                self.assertEqual(result.mode, "RGB")

    def test_deterministic(self):
        a = render_layered_scene("forest", "same")
        b = render_layered_scene("forest", "same")
        self.assertEqual(a.tobytes(), b.tobytes())

    def test_scene_distinction(self):
        forest = render_layered_scene("forest", "same")
        snow = render_layered_scene("snowfield", "same")
        self.assertNotEqual(forest.tobytes(), snow.tobytes())

    def test_invalid_scene_fails_closed(self):
        with self.assertRaises(ValueError):
            render_layered_scene("unknown", "qa")


if __name__ == "__main__":
    unittest.main()
