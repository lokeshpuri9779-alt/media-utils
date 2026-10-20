"""Verify handoffs require two named duo participants."""
import unittest
from PIL import Image
from astra_v2.pillow_duo_scene import draw_duo


class ExplicitHandoffTests(unittest.TestCase):
    def render(self, action="handoff", sender=None, receiver=None, t=0.7):
        shot = {"story_cast": ["fox", "rabbit"], "story_prop": "box",
                "story_action": action, "story_visual_seed": "handoff-test"}
        if sender is not None:
            shot["story_prop_handoff_from"] = sender
        if receiver is not None:
            shot["story_prop_handoff_to"] = receiver
        frame = Image.new("RGB", (1080, 1920), "white")
        self.assertTrue(draw_duo(frame, shot, t))
        return frame.tobytes()

    def test_authored_handoff_changes_frame(self):
        self.assertNotEqual(self.render(sender="fox", receiver="rabbit"),
                            self.render())

    def test_handoff_moves_over_time(self):
        self.assertNotEqual(self.render(sender="fox", receiver="rabbit", t=.2),
                            self.render(sender="fox", receiver="rabbit", t=1.3))

    def test_invalid_endpoint_preserves_legacy_behavior(self):
        self.assertEqual(self.render(sender="fox", receiver="bear"),
                         self.render())
        self.assertEqual(self.render(sender="fox", receiver="fox"),
                         self.render())

    def test_handoff_requires_explicit_action(self):
        self.assertEqual(self.render(action="idle", sender="fox", receiver="rabbit"),
                         self.render(action="idle"))


if __name__ == "__main__":
    unittest.main()
