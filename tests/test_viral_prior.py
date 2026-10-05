import unittest
from viral_prior import score_candidate, rank_candidates

class ViralPriorTests(unittest.TestCase):
    def test_scores_are_bounded(self):
        s=score_candidate({"hook":"CAN YOU FIND IT FAST?","question":"Find the odd one","answer":"ROW 2 COL 3","title":"Find it before time runs out?","genre":"challenge","trend_matches":[]})
        self.assertGreaterEqual(s["total"],0); self.assertLessEqual(s["total"],100)

    def test_trend_signal_increases_score(self):
        c={"hook":"WHY DOES THIS HAPPEN?","question":"A clear question","answer":"Because there is a payoff","title":"Why this happens?","genre":"space"}
        a=score_candidate(c,trend_matches=[])["total"]
        b=score_candidate(c,trend_matches=[{"title":"x"},{"title":"y"}])["total"]
        self.assertGreater(b,a)

    def test_rank(self):
        rows=[
          {"content_id":"weak","hook":"INFO","question":"x","answer":"","title":"Info","genre":"tech","trend_matches":[]},
          {"content_id":"strong","hook":"CAN YOU FIND IT FAST?","question":"What is missing?","answer":"THE ANSWER","title":"Can you find it before the reveal?","genre":"challenge","trend_matches":[{"title":"trend"}]},
        ]
        self.assertEqual(rank_candidates(rows)[0]["content_id"],"strong")

if __name__=="__main__": unittest.main()
