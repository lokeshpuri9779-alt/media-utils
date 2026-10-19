"""Regression: released props must stop dragging the character's hand."""
import unittest
from unittest.mock import patch
from PIL import Image
from astra_v2 import pillow_duo_scene as scene

class ReleaseHandTests(unittest.TestCase):
    def test_release_detaches_hand_after_prop_falls(self):
        shot = {"story_cast": ("fox", "rabbit"),
                "speech": "The fox and rabbit release the gift box.",
                "story_action": "release"}
        strengths = []
        original = scene._actor
        def capture(*args, **kwargs):
            strengths.append(kwargs["hand_strength"])
            return []
        with patch.object(scene, "_actor", side_effect=capture):
            for t in (0.8, 1.0, 1.2):
                self.assertTrue(scene.draw_duo(Image.new("RGB", (1080, 1920)), shot, t))
        self.assertGreater(strengths[0], 0)
        self.assertGreater(strengths[0], strengths[2])
        self.assertGreater(strengths[2], strengths[4])
        self.assertEqual(strengths[4], 0)
        self.assertEqual(strengths[5], 0)

if __name__ == "__main__":
    unittest.main()
