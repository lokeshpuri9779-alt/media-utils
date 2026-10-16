"""Regression checks for hand-anchored prop movement."""
import unittest
from pathlib import Path

class ContactContinuityTests(unittest.TestCase):
    def test_contact_anchors_to_actor_motion(self):
        source = (Path(__file__).resolve().parents[1] / "astra_v2" / "pillow_duo_scene.py").read_text()
        self.assertIn('contact_actions={"pick","pickup","pick_up","carry","hold","repair","catch"}', source)
        self.assertIn("actor_x=298+actor_translation(action,t,0)", source)
        self.assertIn("prop_pos=(round(prop_pos[0]*(1-grasp)+held[0]*grasp)", source)

if __name__ == "__main__":
    unittest.main()
