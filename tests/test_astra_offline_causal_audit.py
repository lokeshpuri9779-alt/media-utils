"""Offline negative-control tests for the lighthouse CPU story audit."""
import json
import unittest
from tools.astra_offline_causal_audit import audit_lighthouse_repair
from tools.astra_offline_llm import review_candidate


def resolved():
    return [
        "Before sunrise, a copper robot discovers the dark lighthouse and realizes that a cargo ship is approaching an unlit reef beside the coastline. The ship cannot see the rocks.",
        "The robot climbs the stairs and opens the damaged warning signal panel to inspect a corroded connector and test the cracked switch. It reaches for the emergency battery.",
        "When lightning strikes, the robot drops the spare battery, and the beacon goes dark again while the ship enters the dangerous water. The robot has only a frayed cable left.",
        "The robot reconnects the damaged switch using its power cable and restores the lamp. The lighthouse beam returns, warning the ship before it reaches the rocks.",
    ]


def real_failed_grammar_story():
    # Archive of the actual real Qwen 0.5B CPU run #41660334335.
    return [
        "A copper robot, tasked with repairing a lighthouse warning signal, finds itself caught in a storm.",
        "The robot must navigate through the stormy waters and over the towering lighthouse, where the warning signal is flashing.",
        "As the robot tries to navigate through the storm, it realizes that the lighthouse is not just a warning signal, but a lifeline for the town.",
        "The copper robot must use its skills and wit to navigate the stormy waters and find a way to repair the lighthouse warning signal before it goes off.",
    ]


class CausalNegativeControlTests(unittest.TestCase):
    def test_resolved_causal_fixture_passes_cues_but_never_approves(self):
        r = audit_lighthouse_repair(resolved())
        self.assertTrue(r["passed"], r["failures"])
        self.assertTrue(all(r["checks"].values()))
        self.assertEqual(r["semantic_quality"], "not_verified")
        for key in ("approved", "production_ready", "published"):
            self.assertFalse(r[key])
        self.assertTrue(r["manual_editorial_review_required"])

    def test_real_failed_grammar_story_rejected(self):
        r = audit_lighthouse_repair(real_failed_grammar_story())
        self.assertFalse(r["passed"])
        self.assertFalse(r["checks"]["payoff_has_completed_repair_cue"])
        self.assertFalse(r["checks"]["not_repeated_navigation_cue"])

    def test_long_unresolved_story_fails_even_if_length_contract_passes(self):
        beats = resolved()
        beats[3] = ("The robot searches for the right tool and studies the broken "
                    "lighthouse warning signal, but no repair is completed. "
                    "The ship is approaching and the robot must find a way "
                    "to repair the lamp while the storm gets worse.")
        story = {"title": "The Robot and the Dark Beacon", "story_beats": beats}
        candidate = review_candidate(json.dumps(story), "test.gguf")
        self.assertFalse(candidate["production_ready"])
        r = audit_lighthouse_repair(candidate["story_beats"])
        self.assertFalse(r["passed"])
        self.assertFalse(r["checks"]["payoff_has_completed_repair_cue"])
        self.assertFalse(r["checks"]["payoff_has_visible_restoration_cue"])

    def test_negated_repair_does_not_count(self):
        beats = resolved()
        beats[3] = ("The robot never repaired the lighthouse lamp, though it "
                    "opened the panel again and looked for help. The beacon "
                    "returns briefly when lightning hits, but the electrical "
                    "switch remains damaged and the ship is still at risk.")
        r = audit_lighthouse_repair(beats)
        self.assertFalse(r["checks"]["payoff_has_completed_repair_cue"])

    def test_unknown_profile_fails_closed(self):
        with self.assertRaises(ValueError):
            audit_lighthouse_repair(resolved(), profile="unverified_new_genre")

    def test_malformed_beat_data_fails_closed(self):
        for beats in ([], ["one"] * 5, ["one", 3, "three", "four"]):
            with self.subTest(beats=beats), self.assertRaises(ValueError):
                audit_lighthouse_repair(beats)


if __name__ == "__main__":
    unittest.main()
