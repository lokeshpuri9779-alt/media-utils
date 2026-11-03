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
    def test_signal_noun_is_not_a_pointing_action(self):
        # Pip's narrated signal lever is a noun, not a gesture.
        self.assertEqual(choose_action({
            "speech": "The railway signal lever is stuck.",
            "visual_prompt": "A mouse stands beside an iron signal lever.",
        }), "idle")
        self.assertEqual(choose_action({
            "speech": "The radio signal grows stronger.",
        }), "idle")
        self.assertEqual(choose_action({
            "speech": "The fox points toward the clearing.",
        }), "point")
        self.assertEqual(choose_action({
            "speech": "The fox signals to its partner.",
        }), "point")

    def test_explicit_action_outweighs_incidental_other_verbs(self):
        self.assertEqual(choose_action({
            "action": "The lynx jumps over a wooden box.",
            "visual_prompt": "The lynx carries the compass.",
            "speech": "The owl repairs the clock.",
        }), "jump")
        self.assertEqual(choose_action({
            "action": "The mouse opens the door.",
            "visual_prompt": "The mouse waves to a friend.",
            "speech": "The mouse repairs the latch.",
        }), "open")

    def test_visual_prompt_outweighs_narration_and_generic_visual(self):
        self.assertEqual(choose_action({
            "visual_prompt": "The fox jumps over a small box.",
            "visual": "A fox carries a lantern.",
            "speech": "The fox carried a lantern to the gate.",
        }), "jump")
        self.assertEqual(choose_action({
            "visual": "A rabbit runs across a small field.",
            "speech": "The rabbit looks at the horizon.",
        }), "run")

    def test_valid_narration_only_actions_are_unchanged(self):
        self.assertEqual(choose_action({"speech": "The otter carries a box."}), "carry")
        self.assertEqual(choose_action({"speech": "The fox repairs a clock."}), "repair")
        self.assertEqual(choose_action({"speech": "The owl looks up."}), "look")
        self.assertEqual(choose_action({"speech": "The room is quiet."}), "idle")

    def test_motion_is_deterministic(self):
        for action in ("run","jump","dance","hide","walk","look","idle"):
            self.assertEqual(offset(action,1.25),offset(action,1.25))
            self.assertEqual(len(offset(action,1.25)),2)
    def test_invalid_time(self):
        with self.assertRaises(ValueError):
            offset("walk",float("nan"))
if __name__=="__main__":
    unittest.main()
