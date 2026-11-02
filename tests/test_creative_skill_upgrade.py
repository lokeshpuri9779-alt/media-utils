import os
import unittest
from unittest.mock import patch
from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_editorial import triage
from astra_v2.creative_skill_upgrade import (
    anti_slop, script_brief, workflow_plan, retention_review, research_intake,
    story_advisory,
)

class CreativeSkillUpgradeTests(unittest.TestCase):
    def test_cliche_and_repetition(self):
        report = anti_slop("Delve deep. The door opens. The door opens.")
        self.assertFalse(report["pass"])
        self.assertFalse(report["approval"])
        self.assertTrue(report["repeated_sentences"])

    def test_cliche_matches_only_whole_phrases(self):
        self.assertFalse(anti_slop("This is a game changer.")["pass"])
        self.assertTrue(anti_slop("The pregame changers arrive.")["pass"])
        self.assertTrue(anti_slop("We can undelve deeper.")["pass"])

    def test_clean_script_not_publication_approval(self):
        report = anti_slop("A copper robot reaches for the amber orb.")
        self.assertTrue(report["pass"])
        self.assertFalse(report["approval"])

    def test_script_brief_and_plan(self):
        self.assertTrue(script_brief("Lighthouse")["visual_feasibility_required"])
        plan = workflow_plan("Lighthouse")
        self.assertLess(plan["stages"].index("visual_feasibility"),
                        plan["stages"].index("render"))
        self.assertFalse(plan["publish_allowed"])

    def test_no_fabricated_analytics(self):
        self.assertEqual(retention_review([])["status"], "no_analytics")
        result = retention_review([{"second": 0, "retention": 1},
                                   {"second": 5, "retention": .7}])
        self.assertEqual(len(result["drops"]), 1)

    def test_research_is_offline_and_fail_closed(self):
        result = research_intake([{"title": "Sample", "url": "https://example.org/video"},
                                  {"title": "Unsafe", "url": "file:///etc/passwd"}])
        self.assertEqual(len(result["items"]), 1)
        self.assertFalse(result["live_search_enabled"])
        self.assertFalse(result["editorial_approval"])

    def test_advisory_sanitizes_script_and_never_approves(self):
        story = {"story_beats": [{"speech": "Delve deep. PRIVATE_TEST_CONTENT. PRIVATE_TEST_CONTENT."}]}
        report = story_advisory(story)
        self.assertEqual(report["status"], "review_suggested")
        self.assertFalse(report["approval"])
        self.assertNotIn("PRIVATE_TEST_CONTENT", str(report))
        self.assertEqual(report["repeated_sentence_count"], 1)

    def test_opt_in_triage_preserves_existing_review_decisions(self):
        story = proposal(999)
        with patch.dict(os.environ, {"ASTRA_CREATIVE_SKILLS_ADVISORY": "0"}):
            baseline = triage([story])
        with patch.dict(os.environ, {"ASTRA_CREATIVE_SKILLS_ADVISORY": "1"}):
            result = triage([story])
            indexed = triage([story], use_semantic_index=True)
        self.assertEqual(result, indexed)
        for bucket in ("ready_for_review", "needs_work"):
            self.assertEqual(len(baseline[bucket]), len(result[bucket]))
            for before, after in zip(baseline[bucket], result[bucket]):
                self.assertNotIn("creative_advisory", before)
                advisory = after.pop("creative_advisory")
                self.assertFalse(advisory["approval"])
                self.assertEqual(before, after)
        self.assertEqual(baseline, result)

    def test_advisory_does_not_read_credentials(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "PRIVATE_TEST_SECRET"}):
            result = story_advisory({"story_beats": [{"speech": "A door opens."}]})
        self.assertNotIn("PRIVATE_TEST_SECRET", str(result))

    def test_invalid_analytics_are_rejected(self):
        for value in (float("nan"), float("inf"), True, -1, 2):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    retention_review([{"second": 0, "retention": value}])

    def test_bad_research_input_not_accepted(self):
        result = research_intake([None, {"title": "local", "url": "https://localhost/secret"},
                                  {"title": "bad", "url": "https://example.org/\\nsecret"},
                                  {"title": "good", "url": "https://example.org/ok"}])
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["title"], "good")

    def test_oversize_input_bounded(self):
        with self.assertRaises(ValueError):
            anti_slop("a" * 100_001)
        self.assertEqual(story_advisory({"story_beats": [{"speech": "a" * 100_001}]})["status"],
                         "script_too_long")

if __name__ == "__main__":
    unittest.main()
