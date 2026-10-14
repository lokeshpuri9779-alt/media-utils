import unittest
from experimental.dual_engine_queue import plan_jobs

class DualEngineQueueTests(unittest.TestCase):
    def test_separate_lanes(self):
        q=plan_jobs([{"story_id":"episode-1","engine":"astra_main"},
                     {"story_id":"episode-1","engine":"cinematic_story"}])
        self.assertEqual(len(q["jobs"]),2)
        self.assertNotEqual(q["jobs"][0]["queue"],q["jobs"][1]["queue"])
        self.assertNotEqual(q["jobs"][0]["job_id"],q["jobs"][1]["job_id"])
        self.assertTrue(all(not j["publish"] for j in q["jobs"]))
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            plan_jobs([{"story_id":"x"},{"story_id":"x"}])
    def test_unknown_engine_rejected(self):
        with self.assertRaises(ValueError):
            plan_jobs([{"story_id":"x","engine":"legacy"}])
if __name__=="__main__":unittest.main()
