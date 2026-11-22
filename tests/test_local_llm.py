"""Offline tests for the optional loopback Ollama script provider."""
import json
import os
import unittest
from unittest.mock import patch

from astra_v2 import local_llm


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class LocalLLMTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(local_llm.enabled())

    def test_enabled_without_gemini_credentials(self):
        with patch.dict(os.environ, {"ASTRA_LOCAL_LLM_ENABLED": "1"}, clear=True):
            self.assertTrue(local_llm.enabled())

    def test_generates_schema_constrained_json_through_loopback(self):
        response = {"message": {"content": json.dumps({"title": "A small test story"})}}
        captured = {}
        def fake_open(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["payload"] = json.loads(request.data)
            return FakeResponse(response)
        with patch.dict(os.environ, {"ASTRA_LOCAL_LLM_ENABLED": "1"}, clear=True), \
             patch.object(local_llm.urllib.request, "urlopen", side_effect=fake_open):
            result = local_llm.generate_json("Write a story", {"type": "object"})
        self.assertEqual(result["title"], "A small test story")
        self.assertEqual(captured["url"], "http://127.0.0.1:11434/api/chat")
        self.assertEqual(captured["payload"]["format"], {"type": "object"})
        self.assertFalse(captured["payload"]["stream"])

    def test_rejects_non_loopback_endpoint(self):
        with patch.dict(os.environ, {"ASTRA_LOCAL_LLM_URL": "http://example.com"}, clear=True):
            with self.assertRaises(ValueError):
                local_llm._endpoint()

    def test_rejects_invalid_model_response(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(local_llm.urllib.request, "urlopen",
                          return_value=FakeResponse({"message": {"content": "not json"}})):
            with self.assertRaises(ValueError):
                local_llm.generate_json("Write a story", {"type": "object"})


if __js__:
    pass
