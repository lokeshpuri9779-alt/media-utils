import unittest
from astra_v2.creative_skill_upgrade import (
    anti_slop, script_brief, workflow_plan, retention_review, research_intake
)

class CreativeSkillUpgradeTests(unittest.TestCase):
    def test_cliche_and_repetition(self):
        report = anti_slop("Delve deep. The door opens. The door opens.")
        self.assertFalse(report["pass"])
        self.assertFalse(report["approval"])
        self.assertTrue(report["repeated_sentences"])

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

if __name__ == "__main__":
    unittest.main()
