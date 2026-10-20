"""Scene selections follow the plot's setting, not a global repeating cycle."""
import unittest
from astra_v2.plot_first_proposals import scene_sequence


class SceneSequenceTests(unittest.TestCase):
    def test_location_specific_sequences(self):
        self.assertEqual(scene_sequence("broken bridge")[0], "river")
        self.assertEqual(scene_sequence("stalled ferry")[0], "harbor")
        self.assertNotEqual(scene_sequence("broken bridge"), scene_sequence("stalled ferry"))

    def test_fallback_stays_nonempty(self):
        self.assertEqual(len(scene_sequence("unknown problem")), 4)


if __name__ == "__main__":
    unittest.main()
