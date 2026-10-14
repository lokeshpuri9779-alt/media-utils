import unittest
from astra_v2.story_action_motion import choose_action,offset

class StoryActionMotionTests(unittest.TestCase):
    def test_action_from_scene(self):
        self.assertEqual(choose_action({"action":"Fox jumps over the fence"}),"jump")
        self.assertEqual(choose_action({"visual_prompt":"The owl runs home"}),"run")
        self.assertEqual(choose_action({"speech":"The room is quiet"}),"idle")
    def test_past_tense_story_dialogue(self):
        self.assertEqual(choose_action({"speech":"The fox repaired carefully."}),"repair")
        self.assertEqual(choose_action({"speech":"The fox carried carefully."}),"carry")
        self.assertEqual(choose_action({"speech":"The fox threw carefully."}),"throw")
        self.assertEqual(choose_action({"speech":"The fox picked up carefully."}),"pick")
        self.assertEqual(choose_action({"speech":"The fox waved carefully."}),"wave")
        self.assertEqual(choose_action({"speech":"The fox ran carefully."}),"run")
        self.assertEqual(choose_action({"speech":"The fox jumped carefully."}),"jump")
        self.assertEqual(choose_action({"speech":"The fox danced carefully."}),"dance")
        self.assertEqual(choose_action({"speech":"The fox hid carefully."}),"hide")
        self.assertEqual(choose_action({"speech":"The fox walked carefully."}),"walk")
        self.assertEqual(choose_action({"speech":"The fox looked carefully."}),"look")
    def test_motion_is_deterministic(self):
        for action in ("run","jump","dance","hide","walk","look","idle"):
            self.assertEqual(offset(action,1.25),offset(action,1.25))
            self.assertEqual(len(offset(action,1.25)),2)
    def test_invalid_time(self):
        with self.assertRaises(ValueError):
            offset("walk",float("nan"))
if __name__=="__main__":
    unittest.main()
