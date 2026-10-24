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

    def test_storyboard_visual_terms_match_space_artwork(self):
        for visual in ("orbit", "galaxy", "cosmos", "astronaut", "planet"):
            with self.subTest(visual=visual):
                self.assertEqual(choose_scene({"visual": visual}), "space")

    def test_explicit_scene_beats_storyboard_and_narration(self):
        shot = {
            "story_environment": "forest",
            "visual_prompt": "planet",
            "visual": "orbit",
            "speech": "The astronaut visits a city",
        }
        self.assertEqual(choose_scene(shot), "forest")

    def test_unknown_storyboard_visual_does_not_guess(self):
        self.assertIsNone(choose_scene({"visual": "an unexpected discovery"}))

    def test_all_supported_environments_resolve_from_visual(self):
        from astra_v2.visual_artifact_library import SCENES
        for scene in SCENES:
            with self.subTest(scene=scene):
                self.assertEqual(choose_scene({"visual": scene}), scene)

    def test_visual_prompt_and_visual_field_priority(self):
        self.assertEqual(choose_scene({
            "visual_prompt": "forest", "visual": "space", "speech": "city"
        }), "forest")
        self.assertEqual(choose_scene({
            "visual": "underwater", "speech": "city"
        }), "underwater")

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
        self.assertNotEqual(first.tobytes(), Image.new("RGB", (1080, 1920), (10, 20, 30)).tobytes())
        self.assertEqual(first.getpixel((500, 1500)), (10, 20, 30))

    def test_story_identity_changes_composition(self):
        shot = {"story_environment": "city"}
        a = apply_backdrop(Image.new("RGB", (1080, 1920)), shot, "story-alpha")
        b = apply_backdrop(Image.new("RGB", (1080, 1920)), shot, "story-beta")
        self.assertNotEqual(a.tobytes(), b.tobytes())

    def test_authored_setting_overrides_incidental_narration(self):
        shot = {"story_environment": "forest", "speech": "The museum guide remembers the city"}
        self.assertEqual(choose_scene(shot), "forest")

    def test_no_pixels_change_in_caption_region(self):
        base = Image.new("RGB", (1080, 1920), (15, 25, 35))
        rendered = apply_backdrop(base.copy(), {"story_environment": "city"}, "scene")
        self.assertEqual(rendered.crop((0, 1100, 1080, 1920)).tobytes(),
                         base.crop((0, 1100, 1080, 1920)).tobytes())

    def test_every_supported_scene_has_a_distinct_backdrop(self):
        import hashlib
        from astra_v2.visual_artifact_library import SCENES
        seen = set()
        for scene in SCENES:
            with self.subTest(scene=scene):
                self.assertEqual(choose_scene({"story_environment": scene}), scene)
                image = Image.new("RGB", (1080, 1920), (10, 20, 30))
                rendered = apply_backdrop(image, {"story_environment": scene}, "stable-id")
                digest = hashlib.sha256(rendered.tobytes()).hexdigest()
                self.assertNotIn(digest, seen)
                seen.add(digest)

    def test_invalid_dimensions_fail_closed(self):
        with self.assertRaises(ValueError):
            apply_backdrop(Image.new("RGB", (540, 720)), {"speech": "forest"}, "id")


if __name__ == "__main__":
    unittest.main()
