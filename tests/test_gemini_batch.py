import unittest
from astra_v2.gemini_batch import generate_batch


class BatchTests(unittest.TestCase):
    def test_unique_inventory(self):
        def fake(ids, titles, history):
            n = len(history)
            return {"content_id": "story-" + str(n), "title": "Story " + str(n)}
        result = generate_batch(4, generator=fake)
        self.assertEqual(result["generated"], 4)
        self.assertEqual(result["status"], "unreviewed")

    def test_published_history_excluded_from_generation(self):
        published = {"content_id": "published-1", "title": "Old Story"}
        observed = []
        def fake(ids, titles, history):
            observed.append((set(ids), set(titles), tuple(history)))
            return {"content_id": "new-1", "title": "New Story"}
        result = generate_batch(1, generator=fake, history=[published])
        self.assertEqual(result["generated"], 1)
        self.assertIn("published-1", observed[0][0])
        self.assertIn("old story", observed[0][1])
        self.assertEqual(observed[0][2][0], published)

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            generate_batch(51)

    def test_rate_limit_stops(self):
        def fail(*args):
            raise RuntimeError("Gemini HTTP 429")
        result = generate_batch(10, generator=fail)
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["generated"], 0)
        self.assertEqual(result["failures"][0]["reason"], "provider_http_429")

    def test_http_404_stops_and_is_classified(self):
        calls = []
        def fail(*args):
            calls.append(1)
            raise RuntimeError("Gemini HTTP 404")
        result = generate_batch(10, generator=fail)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["failures"][0]["reason"], "provider_http_404")

    def test_sanitized_failure_categories_and_continue(self):
        messages = [
            ValueError("Generated story failed causal planning"),
            ValueError("Generated story failed editorial review: private model text"),
            ValueError("Generated story repeats narrative history"),
            ValueError("Gemini response incomplete"),
            ValueError("unrecognized private text or API key"),
            KeyError("private_field"),
            ValueError("duplicate_candidate"),
        ]
        def fail(*args):
            raise messages.pop(0)
        result = generate_batch(7, generator=fail)
        self.assertEqual(result["generated"], 0)
        self.assertEqual([f["reason"] for f in result["failures"]], [
            "causal_planning_rejected", "editorial_rejected",
            "narrative_duplicate", "incomplete_provider_response",
            "validation_error_unclassified", "missing_required_field",
            "duplicate_candidate",
        ])
        self.assertNotIn("private", str(result))
        self.assertEqual(messages, [])

    def test_invalid_json_and_unknown_runtime_are_sanitized(self):
        from astra_v2.gemini_batch import _failure_reason
        import json
        self.assertEqual(_failure_reason(json.JSONDecodeError("secret", "private", 0)),
                         "invalid_provider_json")
        self.assertEqual(_failure_reason(RuntimeError("private token")),
                         "runtime_error_unclassified")



if __name__ == "__main__":
    unittest.main()
