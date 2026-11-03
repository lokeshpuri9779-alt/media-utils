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

    def test_simultaneous_prop_and_jump_swim_not_renderable(self):
        from astra_v2.story_action_motion import unsupported_simultaneous_prop_motion
        examples = (
            "The fox jumps over a small box while holding a brass compass.",
            "The lynx leaps holding the compass in its teeth.",
            "A mouse swims while carrying a small lantern.",
            "The fox jumps with a key in its mouth.",
            "Holding a golden bell, the rabbit hops over a log.",
            "The otter swims with the flower in her paws.",
        )
        for prompt in examples:
            with self.subTest(prompt=prompt):
                self.assertTrue(unsupported_simultaneous_prop_motion({
                    "visual_prompt": prompt,
                }))

    def test_sequential_and_supported_prop_actions_remain_eligible(self):
        from astra_v2.story_action_motion import unsupported_simultaneous_prop_motion
        examples = (
            "The fox carried a compass and then jumped over the log.",
            "The fox carried a compass and jumped over a log.",
            "The fox jumps first, then holds the lantern.",
            "The fox walks while carrying a lantern.",
            "The lynx jumps over a wooden box.",
            "The otter swims near a book.",
            "The owl holds its breath as it swims.",
            "The fox carries a bell. Afterward it leaps.",
        )
        for prompt in examples:
            with self.subTest(prompt=prompt):
                self.assertFalse(unsupported_simultaneous_prop_motion({
                    "visual_prompt": prompt,
                }))

    def test_independent_fields_do_not_invent_simultaneity(self):
        from astra_v2.story_action_motion import unsupported_simultaneous_prop_motion
        self.assertFalse(unsupported_simultaneous_prop_motion({
            "action": "The fox jumps.",
            "visual_prompt": "The fox holds a bell.",
            "speech": "The fox carries a bell.",
        }))

    def test_motion_is_deterministic(self):
        for action in ("run","jump","dance","hide","walk","look","idle"):
            self.assertEqual(offset(action,1.25),offset(action,1.25))
            self.assertEqual(len(offset(action,1.25)),2)
    def test_invalid_time(self):
        with self.assertRaises(ValueError):
            offset("walk",float("nan"))
if __name__=="__main__":
    unittest.main()
