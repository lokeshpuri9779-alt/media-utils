"""Regression checks for opt-in visual-artifact backdrop integration."""
import unittest
from PIL import Image
from astra_v2.visual_artifact_backdrop import choose_scene, apply_backdrop


class ArtifactBackdropTests(unittest.TestCase):
    def test_known_story_locations(self):
        for term, expected in (
            ("The lighthouse keeper", "lighthouse"),
            ("A mystery inside the museum", "museum"),
            ("The train station signal", "railway"),
            ("A fox in the forest", "forest"),
            ("Underwater rescue", "underwater"),
        ):
            with self.subTest(term=term):
                self.assertEqual(choose_scene({"speech": term}), expected)

    def test_unknown_scene_does_not_add_unrelated_art(self):
        image = Image.new("RGB", (1080, 1920), (10, 20, 30))
        self.assertIs(apply_backdrop(image, {"speech": "A surprising discovery"}, "story"), image)
        self.assertEqual(image.getpixel((500, 500)), (10, 20, 30))

    def test_scene_is_deterministic_and_changes_pixels(self):
        shot = {"story_environment": "forest"}
        def draw():
            image = Image.new("RGB", (1080, 1920), (10, 20, 30))
            return apply_backdrop(image, shot, "unique-story-id")
        first, second = draw(), draw()
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertNotEqual(first.getpixel((100, 800)), (10, 20, 30))
        self.assertEqual(first.getpixel((500, 1500)), (10, 20, 30))

    def test_story_identity_changes_composition(self):
        shot = {"story_environment": "city"}
        a = apply_backdrop(Image.new("RGB", (1080, 1920)), shot, "story-alpha")
        b = apply_backdrop(Image.new("RGB", (1080, 1920)), shot, "story-beta")
        self.assertNotEqual(a.tobytes(), b.tobytes())

    def test_invalid_dimensions_fail_closed(self):
        with self.assertRaises(ValueError):
            apply_backdrop(Image.new("RGB", (540, 720)), {"speech": "forest"}, "id")


if __name__ == "__main__":
    unittest.main()
