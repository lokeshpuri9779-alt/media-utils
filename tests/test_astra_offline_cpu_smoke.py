"""Offline CPU benchmark guardrails using fixtures only; no downloads."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import astra_offline_cpu_smoke as smoke


def story():
    return {
        "title": "The Copper Robot and the Lost Light",
        "story_beats": [
            "Before sunrise, a copper robot discovers that a coastal lighthouse has stopped warning passing boats of dangerous rocks below.",
            "The robot climbs the spiral stairs while the storm gathers, tracing the failed circuit to a damaged copper switch behind the lamp.",
            "When lightning strikes, the robot drops its only spare battery, and the warning light dims while a ship nears the shore.",
            "The robot reconnects the switch using its own power cable, restoring the beacon just before the ship reaches the rocks.",
        ],
    }


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.binary = self.root / "llama-cli"
        self.binary.write_text("#!/bin/sh\nexit 0\n")
        self.binary.chmod(0o755)
        self.model = self.root / smoke.MODEL_FILENAME
        self.model.write_bytes(b"model-test-fixture")
        self.output = self.root / "artifacts"
        self.sha = hashlib.sha256(self.model.read_bytes()).hexdigest()

    def test_checksum_mismatch_refuses_inference(self):
        with patch.object(smoke.subprocess, "run") as execute:
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                smoke.run_benchmark(self.binary, self.model, self.output)
            execute.assert_not_called()

    def test_bounded_success_remains_unapproved(self):
        completed = subprocess.CompletedProcess([], 0, json.dumps(story()), "")
        with patch.object(smoke, "MODEL_SHA256", self.sha), patch.object(
            smoke.subprocess, "run", return_value=completed
        ) as execute:
            result = smoke.run_benchmark(self.binary, self.model, self.output)
        self.assertTrue(result["model_executed"])
        self.assertTrue(result["story_contract_passed"])
        self.assertFalse(result["approved"])
        self.assertFalse(result["published"])
        self.assertFalse(result["production_ready"])
        self.assertTrue(result["manual_editorial_review_required"])
        self.assertTrue((self.output / "story-review.json").is_file())
        args, kwargs = execute.call_args
        self.assertIn("--single-turn", args[0])
        self.assertIn("--no-display-prompt", args[0])
        self.assertEqual(kwargs["env"]["HF_HUB_OFFLINE"], "1")
        self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
        self.assertFalse(kwargs["shell"])

    def test_invalid_output_retained_as_unapproved_review_evidence(self):
        completed = subprocess.CompletedProcess([], 0, '{"title": "incomplete"}', "")
        with patch.object(smoke, "MODEL_SHA256", self.sha), patch.object(
            smoke.subprocess, "run", return_value=completed
        ):
            result = smoke.run_benchmark(self.binary, self.model, self.output)
        self.assertTrue(result["model_executed"])
        self.assertFalse(result["story_contract_passed"])
        self.assertFalse(result["approved"])
        self.assertTrue((self.output / "generated-raw.txt").is_file())
        self.assertFalse((self.output / "story-review.json").exists())

    def test_failed_process_never_produces_candidate(self):
        completed = subprocess.CompletedProcess([], 1, "", "synthetic failure")
        with patch.object(smoke, "MODEL_SHA256", self.sha), patch.object(
            smoke.subprocess, "run", return_value=completed
        ):
            result = smoke.run_benchmark(self.binary, self.model, self.output)
        self.assertFalse(result["model_executed"])
        self.assertFalse(result["story_contract_passed"])
        self.assertFalse((self.output / "story-review.json").exists())

    def test_timeout_creates_fail_closed_report(self):
        with patch.object(smoke, "MODEL_SHA256", self.sha), patch.object(
            smoke.subprocess, "run",
            side_effect=subprocess.TimeoutExpired("llama-cli", 180)
        ):
            result = smoke.run_benchmark(self.binary, self.model, self.output)
        self.assertEqual(result["error_type"], "TimeoutExpired")
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["published"])
        self.assertTrue((self.output / "review-report.json").exists())

    def test_timeout_budget_checked_before_inference(self):
        with patch.object(smoke, "MODEL_SHA256", self.sha), patch.object(
            smoke.subprocess, "run"
        ) as execute:
            with self.assertRaisesRegex(ValueError, "timeout"):
                smoke.run_benchmark(self.binary, self.model, self.output, 9999)
            execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
