import unittest
from experimental.parallel_scene_plan import plan_jobs

class ParallelPlanTests(unittest.TestCase):
    def test_all_frames_assigned_exactly_once(self):
        p=plan_jobs(14,4,24,30)
        self.assertEqual(p["frames"],720)
        self.assertEqual(sum(j["frames"] for j in p["jobs"]),720)
        self.assertEqual(p["jobs"][0]["start_frame"],0)
        self.assertEqual(p["jobs"][-1]["end_frame"],720)
        self.assertTrue(all(a["end_frame"]==b["start_frame"] for a,b in zip(p["jobs"],p["jobs"][1:])))
    def test_deterministic(self):
        self.assertEqual(plan_jobs(),plan_jobs())
    def test_invalid_rejected(self):
        with self.assertRaises(ValueError):plan_jobs(0)
        with self.assertRaises(ValueError):plan_jobs(workers=0)
        with self.assertRaises(ValueError):plan_jobs(fps=8)
if __name__=="__main__":unittest.main()
