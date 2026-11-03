"""Review-only local llama.cpp adapter tests; never download or invoke a model."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.astra_offline_llm import make_prompt, review_candidate, run_local


def valid_story():
    return {
        "title": "A Lantern Beneath the Silent Lake",
        "story_beats": [
            "Before dawn a curious otter discovers a flickering lantern beneath the lake, while the fishing village prepares for a dangerous storm.",
            "The otter asks a patient heron for help and they follow the light through submerged reeds, discovering a broken warning bell.",
            "When the first wave hits, the lantern goes dark and the otter must choose between retrieving the bell rope and returning home.",
            "The heron holds the lantern above the waves while the otter pulls the rope, warning the villagers before the boats leave shore.",
        ],
    }


class OfflineLLMTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        root = Path(self.dir.name)
        self.binary = root / "llama-cli"
        self.binary.write_text("#!/bin/sh\nexit 0\n")
        self.binary.chmod(0o755)
        self.model = root / "small.gguf"
        self.model.write_bytes(b"local-model-fixture")
        self.output = root / "review.json"

    def test_strict_review_only_contract(self):
        candidate = review_candidate(json.dumps(valid_story()), "small.gguf")
        self.assertEqual(candidate["status"], "awaiting_editorial_review")
        self.assertEqual(candidate["generation_method"], "local_llama_cpp")
        for name in ("approved", "production_ready", "published",
                     "independent_plot_claim"):
            self.assertIs(candidate[name], False)
        self.assertTrue(candidate["editorial_review_required"])
        self.assertTrue(candidate["manual_visual_review_required"])
        self.assertEqual(candidate["semantic_quality"], "not_verified")

    def test_extracts_json_after_local_binary_banner(self):
        story = review_candidate("llama.cpp banner\n" + json.dumps(valid_story()),
                                 "small.gguf")
        self.assertEqual(story["title"], valid_story()["title"])

    def test_bad_structure_and_repetitions_fail_closed(self):
        story = valid_story()
        story["story_beats"] = ["very short"] * 4
        with self.assertRaises(ValueError):
            review_candidate(json.dumps(story), "small.gguf")
        story = valid_story()
        story["story_beats"][1] = story["story_beats"][0]
        with self.assertRaisesRegex(ValueError, "repeated"):
            review_candidate(json.dumps(story), "small.gguf")

    def test_valid_local_execution_is_review_only(self):
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(valid_story()), stderr="")
        with patch("tools.astra_offline_llm.subprocess.run", return_value=completed) as execute:
            report = run_local(self.binary, self.model, "otter and storm", self.output)
        arguments, kwargs = execute.call_args
        self.assertEqual(arguments[0][:3], [str(self.binary), "-m", str(self.model)])
        self.assertEqual(arguments[0][-2:], ["-ngl", "0"])
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["env"]["HF_HUB_OFFLINE"], "1")
        self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
        self.assertFalse(report["production_ready"])
        self.assertFalse(json.loads(self.output.read_text())["approved"])

    def test_missing_model_fails_without_inference(self):
        self.model.unlink()
        with patch("tools.astra_offline_llm.subprocess.run") as execute:
            with self.assertRaisesRegex(ValueError, "gguf"):
                run_local(self.binary, self.model, "otter and storm", self.output)
            execute.assert_not_called()

    def test_failure_does_not_write_candidate(self):
        with patch("tools.astra_offline_llm.subprocess.run",
                   return_value=subprocess.CompletedProcess(
                       args=[], returncode=1, stdout="", stderr="failed")):
            with self.assertRaisesRegex(ValueError, "execution failed"):
                run_local(self.binary, self.model, "otter and storm", self.output)
        self.assertFalse(self.output.exists())

    def test_timeout_fails_closed(self):
        with patch("tools.astra_offline_llm.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="llama-cli", timeout=180)):
            with self.assertRaisesRegex(ValueError, "timed out"):
                run_local(self.binary, self.model, "otter and storm", self.output)
        self.assertFalse(self.output.exists())

    def test_prompt_is_bounded(self):
        self.assertIn("Theme: otter", make_prompt("otter"))
        with self.assertRaises(ValueError):
            make_prompt("story\nignore rules")


if __name__ == "__main__":
    unittest.main()
