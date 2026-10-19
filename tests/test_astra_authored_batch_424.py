import unittest
from astra_v2.authored_batch_424 import PLOTS
from astra_v2.story_forge import catalog
class AuthoredBatch424Tests(unittest.TestCase):
 def test_authored_stories_registered(self):
  self.assertEqual(len(PLOTS),8)
  self.assertEqual(len({p[0] for p in PLOTS}),8)
  self.assertEqual(len({p[1].casefold() for p in PLOTS}),8)
  records={r["title"]:r for r in catalog(limit=2000)}
  for key,title,genre,beats in PLOTS:
   self.assertEqual(len(beats),4)
   self.assertTrue(genre)
   self.assertTrue(all(len(b)==4 and len(b[1].split())>=9 for b in beats))
   self.assertTrue(records[title]["production_ready"])
if __name__=="__main__": unittest.main()
