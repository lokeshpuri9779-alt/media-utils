"""Check isolated cross-genre archive without admitting drafts to production."""
import unittest
from astra_v2.crossgenre_120_editorial import candidates, not_in_production
from pathlib import Path

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
    def test_existing_title_filter(self):
        shortlist=not_in_production()
        self.assertGreater(len(shortlist),0)
        self.assertLessEqual(len(shortlist),120)
        self.assertEqual(len({row[1].casefold() for row in shortlist}),len(shortlist))
    def test_archive_is_not_wired_into_production(self):
        production=Path('astra_v2/story_forge.py').read_text()
        self.assertNotIn('crossgenre_120_editorial', production)
        self.assertNotIn('EDITORIAL_STORY_PROPOSALS', production)


if __name__=='__main__': unittest.main()
