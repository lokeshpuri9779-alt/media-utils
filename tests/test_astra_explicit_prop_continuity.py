"""Verify authored prop identity survives changing narration."""
import unittest

from astra_errors import CreativeReject
from astra_v2.pillow_duo_scene import scene_prop


class PropContinuityTests(unittest.TestCase):
    def test_explicit_prop_survives_other_object_mentions(self):
        beats = [
            {"story_prop": "box", "speech": "The fox picked up a gift."},
            {"story_prop": "box", "speech": "The fox found a key beside the gift."},
            {"story_prop": "box", "speech": "They carried it to the lantern."},
        ]
        self.assertEqual([scene_prop(s) for s in beats], ["box"] * 3)

    def test_legacy_inference_remains_available(self):
        self.assertEqual(scene_prop({"speech": "The fox found a key."}), "key")

    def test_unsupported_explicit_prop_fails_closed(self):
        with self.assertRaises(CreativeReject):
            scene_prop({"story_prop": "spaceship_engine", "speech": "A key."})


if __name__ == "__main__":
    unittest.main()
