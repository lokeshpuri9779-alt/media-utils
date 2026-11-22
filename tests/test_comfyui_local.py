"""Offline contract tests for the optional ComfyUI loopback adapter."""
import json
import os
import unittest
from unittest.mock import patch

from astra_v2 import comfyui_local


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ComfyUILocalTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(comfyui_local.enabled())

    def test_rejects_remote_endpoint(self):
        with patch.dict(os.environ, {"ASTRA_COMFYUI_URL": "http://example.com"}, clear=True):
            with self.assertRaises(ValueError):
                comfyui_local._base_url()

    def test_rejects_non_loopback_ip(self):
        with patch.dict(os.environ, {"ASTRA_COMFYUI_URL": "http://192.168.1.4:8188"}, clear=True):
            with self.assertRaises(ValueError):
                comfyui_local._base_url()

    def test_submit_posts_workflow_and_returns_prompt_id(self):
        prompt_id = "12345678-abcd-1234-abcd-123456789012"
        captured = {}
        def fake_open(request, timeout):
            captured["url"] = request.full_url
            captured["payload"] = json.loads(request.data)
            return FakeResponse({"prompt_id": prompt_id})
        env = {"ASTRA_COMFYUI_ENABLED": "1"}
        with patch.dict(os.environ, env, clear=True), \\
             patch.object(comfyui_local.urllib.request, "urlopen", side_effect=fake_open):
            result = comfyui_local.submit_workflow({"1": {"class_type": "EmptyLatentImage", "inputs": {}}})
        self.assertEqual(result, prompt_id)
        self.assertEqual(captured["url"], "http://127.0.0.1:8188/prompt")
        self.assertIn("prompt", captured["payload"])

    def test_history_rejects_path_injection(self):
        with patch.dict(os.environ, {"ASTRA_COMFYUI_ENABLED": "1"}, clear=True):
            with self.assertRaises(ValueError):
                comfyui_local.get_history("../queue")

    def test_disabled_submission_does_not_call_server(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                comfyui_local.submit_workflow({"1": {}})


if __name__ == "__main__":
    unittest.main()
