import unittest
from rewrite_queue_diagnostics import inspect_queue

# Non-sensitive structural fixture transcribed from Story Factory run 40236568415.
# The production artifact has three rewrites, top-level hook/title, no thumbnail.
class ProductionShapeTests(unittest.TestCase):
    def test_october_25_rewrite_queue_shape(self):
        payload = {"schema_version":1, "publication_triggered":False,
                   "approved_count":0, "rewrites":[
            {"story":{"hook":"A Sticky Discovery","title":"The Great Citrus Siphon Debacle","production_ready":False}},
            {"story":{"hook":"The Hidden Fault","title":"The Great Neighborhood Relay Ruckus","production_ready":False}},
            {"story":{"hook":"Morning Chaos at the Stall","title":"The Great Market Gadget Gaffe","production_ready":False}},
        ]}
        out = inspect_queue(payload)
        self.assertEqual(out["entries_checked"],3)
        self.assertFalse(out["publication_triggered"])
        for row in out["results"]:
            self.assertEqual(row["hook_score_applicability"], "limited_short_fiction_label")
            self.assertTrue(row["has_hook"])
            self.assertTrue(row["has_title"])
            self.assertFalse(row["has_thumbnail"])
            self.assertTrue(row["diagnostics"]["advisory_only"])
            self.assertFalse(row["diagnostics"]["production_ready"])
            self.assertIn("hook",row["diagnostics"])
            self.assertFalse(row["diagnostics"]["hook"]["quality_decision_allowed"])
            self.assertEqual(row["diagnostics"]["hook"]["interpretation"], "short_label_not_spoken_hook")
            self.assertIn("package",row["diagnostics"])

if __name__ == "__main__":
    unittest.main()
