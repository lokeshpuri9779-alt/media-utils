import unittest
from rewrite_queue_diagnostics import inspect_queue

class RewriteQueueTests(unittest.TestCase):
    def test_actual_shape(self):
        data = {"publication_triggered":False,"rewrites":[
            {"candidate_id":"example","story":{"content_id":"sample","hook":"A Sticky Discovery","title":"The Great Citrus Siphon Debacle","production_ready":False}},
            {"candidate_id":"missing"}]}
        out = inspect_queue(data)
        self.assertEqual(out["entries_checked"],2)
        self.assertTrue(out["results"][0]["has_hook"])
        self.assertTrue(out["results"][0]["has_title"])
        self.assertFalse(out["results"][0]["has_thumbnail"])
        self.assertFalse(out["results"][0]["diagnostics"]["production_ready"])
        self.assertIn("error",out["results"][1])
        self.assertFalse(out["publication_triggered"])
    def test_long_hook_never_grants_editorial_quality_decision(self):
        payload = {"rewrites": [{"story": {
            "hook": "What happens when a mysterious visitor changes everything overnight in this village",
            "title": "A Mysterious Visitor",
        }}]}
        result = inspect_queue(payload)
        row = result["results"][0]
        self.assertEqual(row["hook_score_applicability"], "heuristic_only")
        self.assertFalse(row["diagnostics"]["hook"]["quality_decision_allowed"])
        self.assertEqual(row["diagnostics"]["hook"]["interpretation"], "unvalidated_heuristic_not_quality_gate")
        self.assertFalse(row["diagnostics"]["production_ready"])

    def test_invalid_queue(self):
        with self.assertRaises(ValueError):
            inspect_queue({"rewrites":{}})

if __name__ == "__main__":
    unittest.main()
