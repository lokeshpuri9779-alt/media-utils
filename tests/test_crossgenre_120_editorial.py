"""Check isolated cross-genre archive without admitting drafts to production."""
import unittest
from astra_v2.crossgenre_120_editorial import candidates
from astra_v2.story_forge import catalog

class EditorialArchiveTests(unittest.TestCase):
    def test_unique_well_formed_proposals(self):
        records=candidates()
        self.assertEqual(len(records),120)
        ids=set()
        for record in records:
            self.assertEqual(len(record),4)
            key,title,genre,beats=record
            self.assertTrue(all(isinstance(v,str) and v.strip() for v in (key,title,genre)))
            self.assertNotIn(key,ids)
            ids.add(key)
            self.assertEqual(len(beats),4)
            for beat in beats:
                self.assertEqual(len(beat),4)
                self.assertTrue(all(isinstance(x,str) and x.strip() for x in beat))
    def test_proposals_not_automatically_in_production_catalog(self):
        proposed={row[1] for row in candidates()}
        live={row['title'] for row in catalog(limit=10000)}
        self.assertFalse(proposed & live, sorted(proposed & live))

if __name__=='__main__': unittest.main()
