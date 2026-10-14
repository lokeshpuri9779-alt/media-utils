import unittest
from experimental.story_supply_audit import audit

class StorySupplyAuditTests(unittest.TestCase):
    def test_all_outlines_remain_unapproved(self):
        report=audit()
        self.assertEqual(report["draft_count"],1024)
        self.assertEqual(report["outline_count"],1024)
        self.assertEqual(report["unique_titles"],1024)
        self.assertEqual(report["unique_ids"],1024)
        self.assertEqual(report["approved_for_publication"],0)
        self.assertEqual(sum(report["publication_rejections"].values()),1024)

if __name__=="__main__":
    unittest.main()
