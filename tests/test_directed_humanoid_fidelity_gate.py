"""Dependency-free regression for visible character actions in directed scenes."""
import unittest

from astra_v2.directed_scene_contract import directed_scene_issue


class HumanoidSceneFidelityTests(unittest.TestCase):
    def test_clothed_character_cannot_be_replaced_by_forest_backdrop(self):
        shot = {
            "visual": "forest",
            "speech": "Look at the central leaves, Rowan!",
            "visual_prompt": (
                "Bramble pointing at a withered root system. "
                "Bramble has messy auburn hair and a moss-green tunic. "
                "Rowan stands beside him holding a rusted trowel."
            ),
        }
        self.assertEqual(
            directed_scene_issue(shot),
            "embodied_character_not_supported_by_directed_icons",
        )

    def test_real_preload_geode_and_rescue_beats_reject_icon_substitution(self):
        # Regressions from review of preload artifacts 12866267067 and 12865777422.
        # These clips decoded successfully but visually substituted icons for actions.
        cases = (
            ("planet", "Taran, a lean explorer with canvas trousers and a straw hat, holds an empty canteen."),
            ("signal", "Taran kneeling beside a quartz geode, eyes wide, holding a copper geological hammer."),
            ("robot", "Taran striking the geode with a hammer, sensors on his wrist."),
            ("forest", "Taran kneeling beside a spring and filling his canteen, smiling in relief."),
            ("signal", "Rescuer Marcus holding a blinking beacon while standing on a snowy overlook."),
            ("door", "Rescuer Marcus standing at a broken bridge, wearing a heavy parka and holding an ice axe."),
            ("forest", "Rescuer Marcus swinging an ice axe into a wall of ice, climbing in his blue parka."),
            ("ship", "Rescuer Marcus and a climber sitting inside a helicopter, smiling in red jackets."),
        )
        for visual, prompt in cases:
            with self.subTest(visual=visual, prompt=prompt):
                issue = directed_scene_issue({"visual": visual, "visual_prompt": prompt})
                self.assertIsNotNone(issue)

    def test_approved_glacial_doctor_is_not_a_signal_icon(self):
        # Approved Gemini batch #41321629328: the full character name
        # appears in the title, while each shot uses only "Dr. Vance".
        shot = {
            "story_title": "Dr. Aris Vance and the Glacial Crevasse Rescue",
            "visual": "signal",
            "speech": (
                "Look at the monitor, the seismic sensors indicate the "
                "entire eastern shelf is breaking apart right now beneath us."
            ),
            "visual_prompt": (
                "Dr. Vance stands in a frozen snowy wasteland looking at a "
                "flashing red seismic monitor showing an active signal spike."
            ),
            "story_named_humans": ("Dr. Aris Vance",),
        }
        self.assertEqual(directed_scene_issue(shot),
                         "human_actor_not_supported_by_directed_icons")
        self.assertIsNone(directed_scene_issue({
            "visual": "signal",
            "speech": "The radio signal grows stronger as the storm clears.",
        }))

    def test_recorded_bramble_mill_weaver_story_cannot_be_reduced_to_icons(self):
        # ASTRA publisher state recorded a 2026-11-02 upload with this title.
        # Its human character/action prompts had no reliably recognized human
        # occupation in the earlier renderer preflight. No assertion about
        # the actual uploaded pixels or independent human visual review.
        title = "The Weaver's Choice at Bramble Mill"
        beats = (
            ("forest", "Bram and Thomas examining damp wooden floorboards inside the rustic mill, holding a lantern."),
            ("door", "Thomas and Bram hoisting heavy wool bales toward the heavy oak storage door."),
            ("signal", "Bram struggling with a jammed metal crank lever while Thomas waves a warning red signal flag."),
            ("ship", "Bram and Thomas straining together to drop the heavy timber sluice gate."),
        )
        for visual, visual_prompt in beats:
            with self.subTest(visual=visual):
                self.assertEqual(directed_scene_issue({
                    "story_title": title,
                    "visual": visual,
                    "visual_prompt": visual_prompt,
                }), "human_actor_not_supported_by_directed_icons")

    def test_named_weaver_and_miller_in_bible_require_exact_art(self):
        from astra_v2.directed_scene_contract import named_human_characters
        bible = {"characters": {
            "Bram": "A village weaver operating a wooden loom by the river.",
            "Thomas": "A retired miller managing the stone sluice gate.",
            "Fox": "A red fox with a white tail tip.",
        }}
        self.assertEqual(named_human_characters(bible), ("Bram", "Thomas"))
        self.assertEqual(directed_scene_issue({
            "visual": "forest", "story_named_humans": ("Bram", "Thomas"),
            "visual_prompt": "Thomas and Bram carry the floodgate timber together.",
        }), "human_actor_not_supported_by_directed_icons")

    def test_occupational_terms_do_not_reject_environment_only(self):
        for title, prompt in (
            ("The Mill's Rising Water", "Water pours over the old stone sluice."),
            ("The Loom Turns", "A wooden loom moves slowly without an operator."),
            ("The Owl and the Woven Thread", "An owl observes a loose thread."),
        ):
            with self.subTest(title=title):
                self.assertIsNone(directed_scene_issue({
                    "story_title": title, "visual": "forest",
                    "visual_prompt": prompt,
                }))

    def test_natural_landscape_does_not_need_character_art(self):
        self.assertIsNone(directed_scene_issue({
            "visual": "forest",
            "speech": "The forest glows after rain.",
            "visual_prompt": "Sunlight filters through the forest canopy.",
        }))

    def test_appearance_without_action_does_not_trigger_two_cue_rule(self):
        self.assertIsNone(directed_scene_issue({
            "visual": "forest",
            "speech": "The forest is quiet.",
            "visual_prompt": "A coat hangs from a branch above the moss.",
        }))


if __name__ == "__main__":
    unittest.main()
