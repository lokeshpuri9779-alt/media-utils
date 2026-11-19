import unittest
from astra_v2.autonomous_story_proposals import (CAUSAL_PATHS, MYSTERIES, MYSTERY_CAUSES, MYSTERY_SETTING_INDICES, SETTINGS, proposal)
from astra_v2.publication_quality import publication_rejection


class MysteryPremiseExpansionTests(unittest.TestCase):

    def test_each_mystery_uses_only_a_compatible_setting(self):
        self.assertEqual(len(MYSTERY_SETTING_INDICES), len(MYSTERIES))
        for mystery_index, compatible in enumerate(MYSTERY_SETTING_INDICES):
            self.assertTrue(compatible)
            self.assertEqual(len(set(compatible)), len(compatible))
            self.assertTrue(all(0 <= setting_index < len(SETTINGS) for setting_index in compatible))
            for offset in range(13):
                index = mystery_index * 13 + offset
                setting_index = compatible[(index // 7) % len(compatible)]
                setting = SETTINGS[setting_index][0]
                story = proposal(index)
                reveal = story["story_beats"][0]["speech"]
                self.assertIn(setting, reveal)
                self.assertIn(MYSTERIES[mystery_index][0], reveal)

    def test_all_mysteries_and_causal_paths_are_reachable_and_unreviewed(self):
        self.assertEqual(len(MYSTERY_CAUSES), len(MYSTERIES))
        found_mysteries = set()
        found_causal_paths = set()
        for i in range(176):
            story = proposal(i)
            beats = {beat["story_beat"]: beat["speech"] for beat in story["story_beats"]}
            narration = " ".join(beats.values())
            for j, (mystery, clue, visual) in enumerate(MYSTERIES):
                if mystery in narration:
                    found_mysteries.add(j)
                    self.assertIn(mystery, beats["reveal"])
                    self.assertIn(clue, beats["build"])
                    self.assertIn(MYSTERY_CAUSES[j], beats["twist"])
            for j, (opening, action, reveal, aftermath) in enumerate(CAUSAL_PATHS):
                if opening in narration:
                    found_causal_paths.add(j)
                    self.assertIn(opening, beats["build"])
                    self.assertIn(action, beats["build"])
                    self.assertIn(reveal, beats["twist"])
                    self.assertIn(aftermath, beats["payoff"])
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")
        self.assertEqual(found_mysteries, set(range(len(MYSTERIES))))
        self.assertEqual(found_causal_paths, set(range(len(CAUSAL_PATHS))))


if __name__ == "__main__":
    unittest.main()
