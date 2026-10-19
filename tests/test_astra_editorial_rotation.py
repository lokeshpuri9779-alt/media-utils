import unittest
from tools.astra_editorial_candidate_report import build_report
class EditorialRotationTests(unittest.TestCase):
 def test_rotation_preserves_review_gate_and_changes_selection(self):
  a=build_report(limit=30,rotation=0)
  b=build_report(limit=30,rotation=1)
  self.assertEqual(a["publication_approved"],0)
  self.assertEqual(b["publication_approved"],0)
  self.assertTrue(all(not x["production_ready"] and x["review_status"]=="unreviewed" for x in b["candidates"]))
  self.assertNotEqual([x["key"] for x in a["candidates"]],[x["key"] for x in b["candidates"]])
  self.assertEqual([x["key"] for x in b["candidates"]],[x["key"] for x in build_report(limit=30,rotation=1)["candidates"]])
if __name__=="__main__": unittest.main()
