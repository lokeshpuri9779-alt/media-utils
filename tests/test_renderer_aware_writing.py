"""Offline tests for opt-in Gemini renderer-aware writing, never paid provider calls."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from astra_v2 import omniroute_gemini
from astra_v2.renderer_aware_writing import (
    RENDERER_AWARE_DOMAINS, SUPPORTED_ANIMALS, SUPPORTED_PROPS, writing_guidance,
)


def capture_prompt(renderer_aware):
    captured = []
    def no_network(request, timeout):
        captured.append({
            "prompt": json.loads(request.data)["contents"][0]["parts"][0]["text"],
            "schema": json.loads(request.data)["generationConfig"]["responseJsonSchema"],
            "url": request.full_url,
        })
        raise RuntimeError("offline capture")
    env = {"ASTRA_GEMINI_ENABLED": "1", "GEMINI_API_KEY": "test-only-no-network",
           "ASTRA_GEMINI_RENDERER_AWARE_WRITING": "1" if renderer_aware else "0"}
    with patch.dict(os.environ, env, clear=True), patch.object(
        omniroute_gemini.urllib.request, "urlopen", side_effect=no_network
    ):
        try:
            omniroute_gemini.generate(set(), set())
        except RuntimeError as exc:
            if str(exc) != "offline capture":
                raise
        else:
            raise AssertionError("Expected offline test transport interception")
    return captured


class RendererAwareWritingTests(unittest.TestCase):
    def test_guidance_matches_existing_studio_actor_and_prop_library(self):
        from astra_v2.pillow_duo_scene import ACTORS, PROPS
        self.assertEqual(set(SUPPORTED_ANIMALS), set(ACTORS))
        self.assertEqual(set(SUPPORTED_PROPS), set(PROPS))
        self.assertEqual(len(RENDERER_AWARE_DOMAINS), 12)
        self.assertFalse(any("human protagonist" in d for d in RENDERER_AWARE_DOMAINS))
        self.assertFalse(any("robot caretaker" in d for d in RENDERER_AWARE_DOMAINS))

    def test_opt_in_prompt_uses_same_provider_call_with_supported_cast(self):
        captured = capture_prompt(True)
        self.assertEqual(len(captured), 1)
        prompt = captured[0]["prompt"]
        self.assertIn("Choose exactly one or two recurring animal protagonist SPECIES", prompt)
        self.assertIn("Do not create human protagonists", prompt)
        self.assertIn("supported animal", prompt.lower())
        self.assertIn("without adding an unrepresentable third protagonist", prompt)
        self.assertIn("unreviewed proposal", prompt)
        self.assertIn("genuinely original causal mechanism", prompt)
        self.assertEqual(captured[0]["schema"]["properties"]["beats"]["minItems"], 4)
        self.assertIn("/v1beta/models/", captured[0]["url"])

    def test_default_prompt_unchanged_when_not_opted_in(self):
        captured = capture_prompt(False)
        self.assertEqual(len(captured), 1)
        self.assertNotIn("Production feasibility is mandatory", captured[0]["prompt"])
        # The legacy domain rotation remains unchanged for the other callers.
        self.assertIn("Required distinct creative domain:", captured[0]["prompt"])

    def test_enabled_domain_is_selected_from_supported_domain_bank(self):
        prompt = capture_prompt(True)[0]["prompt"]
        rot = int(hashlib.sha256(b"0").hexdigest()[:8], 16)
        expected = RENDERER_AWARE_DOMAINS[rot % len(RENDERER_AWARE_DOMAINS)]
        self.assertIn("Required distinct creative domain: " + expected, prompt)

    def test_workflow_enables_guidance_only_for_generator_and_keeps_review(self):
        root = Path(__file__).resolve().parents[1]
        flow = (root / ".github/workflows/astra-gemini-proposal-batch.yml").read_text()
        generation = flow.split("      - name: Generate proposals", 1)[1].split(
            "      - name: Install CPU-only renderer eligibility dependencies", 1
        )[0]
        self.assertIn("ASTRA_GEMINI_RENDERER_AWARE_WRITING: '1'", generation)
        self.assertIn("GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}", generation)
        review = flow.split("      - name: Independently review generated proposals", 1)[1].split(
            "      - name: Persist approved batch", 1
        )[0]
        self.assertIn("ASTRA_UNIFIED_STORY_ENGINE: '1'", review)
        self.assertIn("python -m astra_v2.gemini_batch_review", review)
        self.assertIn("Audit script and renderer feasibility (diagnostic only)", flow)
        self.assertIn("continue-on-error: true", flow)

    def test_guidance_never_claims_render_or_publication_approval(self):
        guide = writing_guidance()
        self.assertIn("independent editorial", guide)
        self.assertIn("publisher gates", guide)
        self.assertNotIn("automatically approved", guide)


if __name__ == "__main__":
    unittest.main()
