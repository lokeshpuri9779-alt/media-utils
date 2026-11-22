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

    def test_exhausted_models_stops_batch_after_one_failed_slot(self):
        calls = []
        def provider(*args):
            calls.append(True)
            raise RuntimeError(
                "Gemini exhausted configured free-tier models without a response")
        result = generate_batch(20, generator=provider)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["generated"], 0)
        self.assertEqual(result["requested"], 20)
        self.assertEqual(result["failures"], [
            {"index": 0, "reason": "provider_models_exhausted"}])
        self.assertEqual(result["status"], "unreviewed")

    def test_exhaustion_keeps_prior_stories_unreviewed_and_never_continues(self):
        calls = []
        def provider(*args):
            calls.append(True)
            if len(calls) == 1:
                return {"content_id": "new-a", "title": "Original Story A"}
            raise RuntimeError(
                "Gemini exhausted configured free-tier models without a response")
        result = generate_batch(20, generator=provider)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["generated"], 1)
        self.assertEqual(result["stories"], [
            {"content_id": "new-a", "title": "Original Story A"}])
        self.assertEqual(result["failures"], [
            {"index": 1, "reason": "provider_models_exhausted"}])
        self.assertEqual(result["status"], "unreviewed")

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

    def test_known_gemini_beat_quality_failures_have_sanitized_categories(self):
        # The production generator calls validate_beat_quality(beats, "Gemini").
        # These are validator errors, not evidence of semantic acceptance.
        messages = [
            ValueError("Gemini requires exactly four beats"),
            ValueError("Gemini narration needs at least 12 words per beat"),
            ValueError("Gemini needs at least three distinct visual types"),
        ]
        def fail(*args):
            raise messages.pop(0)
        result = generate_batch(3, generator=fail)
        self.assertEqual(result["generated"], 0)
        self.assertEqual([row["reason"] for row in result["failures"]], [
            "invalid_beat_count",
            "insufficient_beat_narration",
            "insufficient_visual_diversity",
        ])
        self.assertEqual(messages, [])
        self.assertEqual(result["status"], "unreviewed")

    def test_unknown_gemini_validator_message_stays_unclassified_and_private(self):
        from astra_v2.gemini_batch import _failure_reason
        self.assertEqual(
            _failure_reason(ValueError("Gemini private prompt rejected: API_KEY_SENTINEL")),
            "validation_error_unclassified")

    def test_invalid_json_and_unknown_runtime_are_sanitized(self):
        from astra_v2.gemini_batch import _failure_reason
        import json
        self.assertEqual(_failure_reason(json.JSONDecodeError("secret", "private", 0)),
                         "invalid_provider_json")
        self.assertEqual(_failure_reason(RuntimeError("private token")),
                         "runtime_error_unclassified")



if __name__ == "__main__":
    unittest.main()


class BatchDiagnosticsAndPacingTests(unittest.TestCase):
    def test_pacing_validator_rejections_are_classified_without_model_text(self):
        messages = [
            "Gemini narration must be 24-38 words per beat",
            "Gemini narration must total 96-152 words",
            "Gemini story needs at least one natural dialogue line",
            "Gemini story needs at least two scene-ending hooks",
            "Gemini requires exactly four cinematic beats",
            "Gemini returned an invalid story beat",
            "Invalid beat subject, environment, or narrative role",
            "Gemini visual must name a supported animal subject",
            "Gemini must preserve a protagonist visual across beats",
            "Gemini private model sentence that is not a validator",
        ]
        queue = [ValueError(m) for m in messages]
        def fail(*args):
            raise queue.pop(0)
        result = generate_batch(len(messages), generator=fail)
        self.assertEqual([f["reason"] for f in result["failures"]], [
            "beat_word_count_out_of_range", "total_word_count_out_of_range",
            "missing_dialogue", "insufficient_scene_hooks", "invalid_beat_count",
            "invalid_beat", "invalid_beat", "unsupported_visual_subject",
            "protagonist_not_preserved", "validation_error_unclassified"])
        self.assertNotIn("private", str(result))
        self.assertEqual(result["attempted"], len(messages))

    def test_pacing_waits_between_slots_only(self):
        waits = []
        def fake(ids, titles, history):
            n = len(history)
            return {"content_id": "s" + str(n), "title": "Story " + str(n)}
        result = generate_batch(3, generator=fake, pace_seconds=6, sleep=waits.append)
        self.assertEqual(result["generated"], 3)
        self.assertEqual(waits, [6, 6])

    def test_single_429_recovers_after_bounded_cooldown(self):
        calls, waits = [], []
        def provider(ids, titles, history):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("Gemini HTTP 429 model=x")
            return {"content_id": "n" + str(len(calls)), "title": "Story " + str(len(calls))}
        result = generate_batch(2, generator=provider, rate_limit_cooldown=65,
                                sleep=waits.append)
        self.assertEqual(result["generated"], 2)
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["cooldowns"], 1)
        self.assertEqual(waits, [65])

    def test_persistent_429_still_stops_the_batch(self):
        calls, waits = [], []
        def provider(*args):
            calls.append(1)
            raise RuntimeError("Gemini HTTP 429 model=x")
        result = generate_batch(20, generator=provider, rate_limit_cooldown=65,
                                sleep=waits.append)
        self.assertEqual(len(calls), 2)  # first call plus one cooldown retry
        self.assertEqual(result["generated"], 0)
        self.assertEqual(result["failures"], [{"index": 0, "reason": "provider_http_429"}])
        self.assertEqual(waits, [65])

    def test_cooldowns_are_capped_per_batch(self):
        waits = []
        state = {"n": 0}
        def provider(ids, titles, history):
            state["n"] += 1
            if state["n"] % 2 == 1:
                raise RuntimeError("Gemini HTTP 429")
            return {"content_id": "c" + str(state["n"]), "title": "Story " + str(state["n"])}
        result = generate_batch(10, generator=provider, rate_limit_cooldown=65,
                                max_cooldowns=2, sleep=waits.append)
        self.assertEqual(waits, [65, 65])
        self.assertEqual(result["cooldowns"], 2)
        self.assertEqual(result["generated"], 2)
        self.assertEqual(result["failures"][-1]["reason"], "provider_http_429")

    def test_non_429_provider_errors_get_no_cooldown_retry(self):
        calls, waits = [], []
        def provider(*args):
            calls.append(1)
            raise RuntimeError("Gemini HTTP 403 model=x")
        result = generate_batch(5, generator=provider, rate_limit_cooldown=65,
                                sleep=waits.append)
        self.assertEqual(len(calls), 1)
        self.assertEqual(waits, [])
        self.assertEqual(result["failures"][0]["reason"], "provider_http_403")
