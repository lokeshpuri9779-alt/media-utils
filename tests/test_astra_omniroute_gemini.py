"""Offline checks: free Gemini OmniRoute is opt-in and fails closed."""
import os
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

    def test_primary_404_uses_current_default_free_tier_fallback(self):
        import io
        import json
        import urllib.error
        requested = []
        def fake_urlopen(request, timeout):
            requested.append(request.full_url)
            if "gemini-3.1-flash-lite" in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)
            return io.BytesIO(json.dumps({"candidates": []}).encode())
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "fixture-only",
            "ASTRA_GEMINI_ENABLED": "1",
            "ASTRA_GEMINI_MODEL": "gemini-3.1-flash-lite",
        }, clear=True), patch.object(
                omniroute_gemini.urllib.request, "urlopen",
                side_effect=fake_urlopen):
            with self.assertRaisesRegex(ValueError, "no candidates"):
                omniroute_gemini.generate(set(), set())
        self.assertEqual(len(requested), 2)
        self.assertIn("gemini-3.5-flash-lite", requested[1])

    def test_two_404s_fail_closed_without_extra_models(self):
        import urllib.error
        requested = []
        def fake_urlopen(request, timeout):
            requested.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "fixture-only",
            "ASTRA_GEMINI_ENABLED": "1",
            "ASTRA_GEMINI_MODEL": "gemini-3.1-flash-lite",
        }, clear=True), patch.object(
                omniroute_gemini.urllib.request, "urlopen",
                side_effect=fake_urlopen):
            with self.assertRaisesRegex(RuntimeError, "Gemini HTTP 404"):
                omniroute_gemini.generate(set(), set())
        self.assertEqual(len(requested), 2)
        self.assertIn("gemini-3.5-flash-lite", requested[-1])

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
        self.assertIn("visual_bible", schema["required"])

    def test_gemini_normalizes_only_known_beat_labels(self):
        import io
        import json
        from astra_v2.openai_creative import VISUALS, ROLES
        self.assertIn("forest", VISUALS)
        self.assertIn("reveal", ROLES)
        # A noncanonical label must still be rejected; normalization is not
        # permission to map arbitrary model output to a production visual.
        beats = [{"visual": "unmapped_environment", "story_beat": "reveal",
                  "speech": "word " * 14} for _ in range(4)]
        from astra_v2.omniroute import validate_beat_quality
        with self.assertRaises(ValueError):
            validate_beat_quality(beats, "Gemini")

if __name__ == "__main__":
    unittest.main()
