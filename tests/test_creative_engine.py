import unittest

from creative_engine import creative_rebuild, topic_headline_alignment

class CreativeEngineTests(unittest.TestCase):
    def test_rejects_mismatched_current_story(self):
        c={
            "genre":"current","title":"Shreyas Iyer","hook":"SHREYAS IYER",
            "question":"A current update.","answer":"A sufficiently long sourced answer for testing.",
            "topic":"shreyas iyer","news_title":"Bhuvneshwar Kumar returns to India's squad",
            "source":"https://example.com","source_count":3,
            "trend_matches":[{"news":[
                {"title":"Bhuvneshwar Kumar returns to India's squad","source":"A","url":"https://a.example"},
                {"title":"India names squad as Bhuvneshwar Kumar returns","source":"B","url":"https://b.example"},
            ]}],
        }
        _, report=creative_rebuild(c)
        self.assertFalse(report["pass"])
        self.assertTrue(any("trend subject" in x for x in report["hard_failures"]))

    def test_metadata_only_current_story_does_not_publish(self):
        c={
            "genre":"current","title":"NASA announces a new lunar mission","hook":"NASA LUNAR MISSION",
            "question":"NASA has announced a new lunar mission.",
            "answer":"NASA announced a new lunar mission according to current coverage.",
            "topic":"NASA lunar mission","news_title":"NASA announces a new lunar mission",
            "source":"https://example.com","source_count":2,
            "trend_matches":[{"news":[
                {"title":"NASA announces a new lunar mission","source":"A","url":"https://a.example"},
                {"title":"NASA lunar mission announced for new programme","source":"B","url":"https://b.example"},
            ]}],
        }
        _, report=creative_rebuild(c)
        self.assertFalse(report["pass"])
        self.assertTrue(any("metadata-only" in x for x in report["hard_failures"]))

    def test_evergreen_gets_tight_viewer_first_brief(self):
        c={"genre":"space","title":"Why Venus Is So Hot","hook":"VENUS IS HOTTER",
           "question":"Why is Venus hotter than Mercury?",
           "answer":"Its thick atmosphere traps heat through a powerful greenhouse effect.",
           "source":"https://science.nasa.gov/","premium_story":True,"production_ready":True}
        out, report=creative_rebuild(c)
        self.assertTrue(report["pass"])
        self.assertLessEqual(out["target_duration_max"],27)
        self.assertEqual(out["cta_mode"],"none")
        self.assertEqual(out["voice_profile"],"af_heart")

    def test_alignment_is_subject_aware(self):
        self.assertEqual(topic_headline_alignment("shreyas iyer","Bhuvneshwar Kumar returns"),0)
        self.assertGreaterEqual(topic_headline_alignment("NASA lunar mission","NASA announces lunar mission"),.66)

if __name__=="__main__":
    unittest.main()
