"""Offline checks: free Gemini OmniRoute is opt-in and fails closed."""
import os
import urllib.error
import unittest
from unittest.mock import patch
from astra_v2 import omniroute_gemini


class GeminiRouteTests(unittest.TestCase):
    def test_missing_key_disables_route(self):
        with patch.dict(os.environ, {"ASTRA_GEMINI_ENABLED": "1"}, clear=True):
            self.assertFalse(omniroute_gemini.enabled())
            self.assertIsNone(omniroute_gemini.generate(set(), set()))

    def test_explicit_enable_required(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}, clear=True):
            self.assertFalse(omniroute_gemini.enabled())

    def test_invalid_model_rejected_without_network(self):
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1",
            "ASTRA_GEMINI_MODEL": "../other"}, clear=True):
            with self.assertRaises(ValueError):
                omniroute_gemini.generate(set(), set())


    def test_missing_primary_model_uses_free_fallback(self):
        import io
        import json
        import urllib.error
        from unittest.mock import Mock
        requested = []
        def fake_urlopen(request, timeout):
            requested.append(request.full_url)
            if "gemini-3.1-flash-lite" in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)
            return io.BytesIO(json.dumps({"candidates": []}).encode())
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1",
            "ASTRA_GEMINI_MODEL": "gemini-3.1-flash-lite",
            "ASTRA_GEMINI_FALLBACK_MODEL": "gemini-2.5-flash-lite",
        }, clear=True), patch.object(omniroute_gemini.urllib.request, "urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(ValueError, "no candidates"):
                omniroute_gemini.generate(set(), set())
        self.assertEqual(len(requested), 2)
        self.assertIn("gemini-2.5-flash-lite", requested[-1])

    def test_default_fallback_avoids_legacy_25_model(self):
        import io
        import json
        requested = []
        def fake_urlopen(request, timeout):
            requested.append(request.full_url)
            if "gemini-3.5-flash-lite" in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)
            return io.BytesIO(json.dumps({"candidates": []}).encode())
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1",
            "ASTRA_GEMINI_MODEL": "gemini-3.5-flash-lite",
        }, clear=True), patch.object(omniroute_gemini.urllib.request, "urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(ValueError, "no candidates"):
                omniroute_gemini.generate(set(), set())
        self.assertEqual(len(requested), 2)
        self.assertIn("gemini-3.1-flash-lite", requested[-1])
        self.assertNotIn("gemini-2.5-flash-lite", requested[-1])

    def test_default_model_pair_has_independent_404_fallback(self):
        import io
        import json
        requested = []
        def fake_urlopen(request, timeout):
            requested.append(request.full_url)
            if "gemini-3.5-flash-lite" in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)
            return io.BytesIO(json.dumps({"candidates": []}).encode())
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1"}, clear=True), patch.object(omniroute_gemini.urllib.request, "urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(ValueError, "no candidates"):
                omniroute_gemini.generate(set(), set())
        self.assertEqual(len(requested), 2)
        self.assertIn("gemini-3.5-flash-lite", requested[0])
        self.assertIn("gemini-3.1-flash-lite", requested[1])

    def test_publisher_configures_distinct_free_model_pair(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/astra-v2-publish.yml").read_text(encoding="utf-8")
        self.assertIn("ASTRA_GEMINI_MODEL: 'gemini-3.5-flash-lite'", workflow)
        self.assertIn("ASTRA_GEMINI_FALLBACK_MODEL: 'gemini-3.1-flash-lite'", workflow)

    def test_authentication_error_never_falls_back(self):
        import urllib.error
        requested = []
        def fake_urlopen(request, timeout):
            requested.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 403, "forbidden", {}, None)
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1",
            "ASTRA_GEMINI_MODEL": "gemini-3.1-flash-lite",
            "ASTRA_GEMINI_FALLBACK_MODEL": "gemini-2.5-flash-lite",
        }, clear=True), patch.object(omniroute_gemini.urllib.request, "urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(RuntimeError, "Gemini HTTP 403"):
                omniroute_gemini.generate(set(), set())
        self.assertEqual(len(requested), 1)

    def test_queue_new_plot_request_reaches_gemini_without_rejected_plot(self):
        import json
        from astra_v2.story_factory_rewrite_queue import rewrite_packet
        candidate = {"candidate_id": "c1", "source_sha256": "a" * 64,
                     "review_status": "needs_new_plot", "decision": "not_approved",
                     "production_ready": False, "eligible_for_automatic_publishing": False,
                     "review_issues": ["repeated_underlying_plot_mechanism"],
                     "title": "REJECTED_TITLE_SENTINEL", "premise_key": "REJECTED_KEY_SENTINEL",
                     "story_beats": ["REJECTED_BEAT_SENTINEL"] * 4}
        prompts = []
        def capture(request, timeout):
            prompts.append(json.loads(request.data)["contents"][0]["parts"][0]["text"])
            raise RuntimeError("offline request captured")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1"}, clear=True), patch.object(omniroute_gemini.urllib.request, "urlopen", side_effect=capture):
            result = rewrite_packet({"approved_count": 0, "publication_triggered": False,
                                     "candidates": [candidate]}, generator=omniroute_gemini.generate)
        self.assertEqual(len(prompts), 1)
        self.assertIn("Invent an entirely new causal plot mechanism", prompts[0])
        for marker in ("REJECTED_TITLE_SENTINEL", "REJECTED_KEY_SENTINEL", "REJECTED_BEAT_SENTINEL"):
            self.assertNotIn(marker, prompts[0])
        self.assertFalse(result["rewrites"][0]["approved"])
        self.assertEqual(result["rewrites"][0]["status"], "rewrite_failed")

    def test_unsanitized_new_plot_request_never_calls_gemini(self):
        base = {"review_status": "needs_new_plot", "decision": "not_approved",
                "production_ready": False, "eligible_for_automatic_publishing": False,
                "required_next_action": "invent_distinct_causal_plot_mechanism",
                "review_issues": ["repeated_underlying_plot_mechanism"], "story_beats": []}
        for changes in ({"story_beats": ["old plot"] * 4}, {"decision": "approved"},
                        {"eligible_for_automatic_publishing": True}, {"review_issues": []},
                        {"required_next_action": "rewrite"}, {"production_ready": True}):
            with self.subTest(changes=changes), patch.dict(os.environ, {"GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1"}, clear=True), patch.object(omniroute_gemini.urllib.request, "urlopen") as network:
                with self.assertRaises(ValueError):
                    omniroute_gemini.generate(set(), set(), premise={**base, **changes})
                network.assert_not_called()

    def test_gemini_request_constrains_visual_and_story_role_enums(self):
        import json
        from astra_v2.openai_creative import VISUALS, ROLES
        from astra_v2.visual_artifact_library import SCENES
        requests = []
        def capture(request, timeout):
            requests.append(json.loads(request.data))
            raise RuntimeError("offline request captured")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1"}, clear=True), patch.object(omniroute_gemini.urllib.request, "urlopen", side_effect=capture):
            with self.assertRaisesRegex(RuntimeError, "offline request captured"):
                omniroute_gemini.generate(set(), set())
        self.assertEqual(len(requests), 1)
        config = requests[0]["generationConfig"]
        self.assertEqual(config["responseMimeType"], "application/json")
        self.assertNotIn("responseSchema", config)
        schema = config["responseJsonSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"]["visual_bible"]["properties"]["characters"]["additionalProperties"]["type"], "string")
        beat = schema["properties"]["beats"]["items"]["properties"]
        self.assertEqual(set(beat["visual"]["enum"]), VISUALS)
        self.assertEqual(set(beat["story_beat"]["enum"]), ROLES)
        self.assertEqual(set(beat["story_environment"]["enum"]), set(SCENES))
        self.assertIn("story_environment", schema["properties"]["beats"]["items"]["required"])
        self.assertIn("visual_bible", schema["required"])
        self.assertIn("supported animals", requests[0]["contents"][0]["parts"][0]["text"])
        self.assertIn("no third species", requests[0]["contents"][0]["parts"][0]["text"])
        self.assertIn("Keep at least one protagonist visual tag consistent", requests[0]["contents"][0]["parts"][0]["text"])

    def test_gemini_normalizes_only_known_beat_labels(self):
        import io
        import json
        from astra_v2.openai_creative import VISUALS, ROLES
        from astra_v2.visual_artifact_library import SCENES
        self.assertIn("fox", VISUALS)
        self.assertIn("forest", SCENES)
        self.assertIn("reveal", ROLES)
        # A noncanonical label must still be rejected; normalization is not
        # permission to map arbitrary model output to a production visual.
        beats = [{"visual": "unmapped_environment", "story_beat": "reveal",
                  "speech": "word " * 14} for _ in range(4)]
        from astra_v2.omniroute import validate_beat_quality
        with self.assertRaises(ValueError):
            validate_beat_quality(beats, "Gemini")

    def test_recent_stories_not_alphabetical_old_titles_guide_generation(self):
        import json
        old = [
            {"title": "A-old-title-%03d" % index, "content_id": "a%d" % index,
             "confirmed_at": "2026-10-01T00:00:00+00:00"}
            for index in range(130)
        ]
        newest = {
            "title": "Zebra-endangered-observatory-recovery",
            "content_id": "newest", "confirmed_at": "2026-11-04T12:05:00+00:00",
            "central_conflict": "Orchestra loses its shared rehearsal hall to a storm",
            "decisive_choice": "Neighbors share time slots after mediating a dispute",
        }
        prompt = []
        def capture(request, timeout):
            prompt.append(json.loads(request.data)["contents"][0]["parts"][0]["text"])
            raise RuntimeError("captured no network")
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1",
        }, clear=True), patch.object(
            omniroute_gemini.urllib.request, "urlopen", side_effect=capture
        ):
            with self.assertRaisesRegex(RuntimeError, "captured no network"):
                omniroute_gemini.generate(
                    {x["content_id"] for x in old} | {"newest"},
                    {x["title"].casefold() for x in old} | {newest["title"].casefold()},
                    prior_stories=[*old, newest])
        self.assertEqual(len(prompt), 1)
        self.assertIn(newest["title"], prompt[0])
        self.assertIn("Neighbors share time slots", prompt[0])
        self.assertIn("fresh causal mechanism", prompt[0])
        self.assertLess(len(prompt[0]), 13000)

    def test_recent_exclusion_context_is_bounded_and_filters_invalid_data(self):
        recent = omniroute_gemini.recent_story_exclusions([
            None, {}, {"title": 123}, {"title": "  "},
            {"title": "Old", "confirmed_at": "2026-10-01T12:00:00+00:00"},
            {"title": "New", "confirmed_at": "2026-11-04T12:00:00+00:00",
             "central_conflict": "n" * 250},
            {"title": "New", "confirmed_at": "2026-11-03T12:00:00+00:00"},
        ])
        self.assertEqual([x["title"] for x in recent], ["New", "Old"])
        self.assertLessEqual(len(recent[0]["central_conflict"]), 135)
        for limit in (0, 33, True):
            with self.assertRaises(ValueError):
                omniroute_gemini.recent_story_exclusions([], limit=limit)

    def test_twelve_batch_calls_cover_all_twelve_domain_constraints(self):
        import json
        prompts = []
        def capture(request, timeout):
            prompts.append(json.loads(request.data)["contents"][0]["parts"][0]["text"])
            raise RuntimeError("captured no network")
        history = [{"title": "Fixed %d" % i,
                    "content_id": "fixed-%d" % i,
                    "confirmed_at": "2026-10-30T12:00:00+00:00"}
                   for i in range(15)]
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test", "ASTRA_GEMINI_ENABLED": "1",
        }, clear=True), patch.object(
            omniroute_gemini.urllib.request, "urlopen", side_effect=capture
        ):
            for i in range(12):
                prior = history + [
                    {"title": "New experiment %d" % j,
                     "content_id": "generated-%d" % j, "kind": "microfiction",
                     "production_ready": True}
                    for j in range(i)
                ]
                with self.assertRaisesRegex(RuntimeError, "captured no network"):
                    omniroute_gemini.generate(
                        {x["content_id"] for x in prior},
                        {x["title"].casefold() for x in prior}, prior_stories=prior)
        domains = [p.split("Required distinct creative domain: ", 1)[1].split(". ", 1)[0]
                   for p in prompts]
        self.assertEqual(len(set(domains)), 12, domains)
        self.assertTrue(all("recent accepted, pending or batch-candidate" in p
                            for p in prompts))


if __name__ == "__main__":
    unittest.main()
