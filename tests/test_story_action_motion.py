import unittest
from astra_v2.story_action_motion import choose_action,offset

class StoryActionMotionTests(unittest.TestCase):
    def test_action_from_scene(self):
        self.assertEqual(choose_action({"action":"Fox jumps over the fence"}),"jump")
        self.assertEqual(choose_action({"visual_prompt":"The owl runs home"}),"run")
        self.assertEqual(choose_action({"speech":"The room is quiet"}),"idle")
    def test_motion_is_deterministic(self):
        for action in ("run","jump","dance","hide","walk","look","idle"):
            self.assertEqual(offset(action,1.25),offset(action,1.25))
            self.assertEqual(len(offset(action,1.25)),2)
    def test_invalid_time(self):
        with self.assertRaises(ValueError):
            offset("walk",float("nan"))
if __name__=="__main__":
    unittest.main()
