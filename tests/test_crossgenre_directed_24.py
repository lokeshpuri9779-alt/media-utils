"""Cross-genre scripts must remain individually directed, distinct and gated."""
import unittest
from astra_v2.crossgenre_directed_24 import PLOTS
from astra_v2.story_forge import catalog, plot_fingerprint
from astra_v2.publication_quality import publication_rejection
from astra_v2.story_action_motion import choose_action

GENERIC_HEADLINES={"THE PROBLEM GROWS","A HIDDEN ANSWER","THE FINAL TURN"}

class CrossGenreEditorialTests(unittest.TestCase):
    def test_twenty_four_story_arcs_cover_twelve_genres(self):
        self.assertEqual(len(PLOTS),24)
        self.assertEqual(len({s[2] for s in PLOTS}),12)
        self.assertEqual(len({s[0] for s in PLOTS}),24)
        self.assertEqual(len({s[1].casefold() for s in PLOTS}),24)
        self.assertEqual(len({plot_fingerprint(s[3]) for s in PLOTS}),24)
        seqs=set()
        for key,title,genre,beats in PLOTS:
            with self.subTest(title=title):
                self.assertEqual(len(beats),4)
                self.assertTrue(all(len(x)==4 for x in beats))
                self.assertTrue(all(len(x[1].split())>=9 for x in beats))
                self.assertFalse(any("memorable turning point" in x[1].casefold() for x in beats))
                self.assertEqual(len({x[0] for x in beats}),4)
                self.assertFalse({x[0] for x in beats} & GENERIC_HEADLINES)
                self.assertTrue(all(x[2] in {"story","forest","door","ship","signal",
                    "robot","planet","museum","book","train","ocean"} for x in beats))
                seqs.add(tuple(x[2] for x in beats))
        self.assertGreaterEqual(len(seqs),20)

    def test_new_catalog_has_unique_approved_stories_and_draft_gate(self):
        records=catalog(limit=400)
        new={x[1] for x in PLOTS}
        selected=[x for x in records if x["title"] in new]
        self.assertEqual(len(selected),24)
        self.assertEqual(len({x["content_id"] for x in selected}),24)
        for x in selected:
            self.assertTrue(x["production_ready"])
            self.assertEqual(x["kind"],"authored_causal_story")
            self.assertIsNone(publication_rejection(x))
            self.assertEqual(len(x["story_beats"]),4)
            self.assertEqual([b["story_beat"] for b in x["story_beats"]],
                ["reveal","build","twist","payoff"])
        ids={x["content_id"] for x in records if x["title"] not in new}
        remaining=catalog(excluded_ids=ids,limit=400)
        self.assertEqual({x["title"] for x in remaining},new)

    def test_unreviewed_drafts_not_accidentally_published(self):
        drafts=[x for x in catalog(limit=3000,include_drafts=True)
                if x["kind"]=="unreviewed_causal_draft"]
        self.assertEqual(len(drafts),996)
        self.assertTrue(all(not x["production_ready"] for x in drafts))
        self.assertTrue(all(publication_rejection(x)=="unreviewed_causal_draft"
                            for x in drafts))

if __name__=="__main__":
    unittest.main()
