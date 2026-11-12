"""Exercise the optional model's actual parsing and editorial gates without network or charges."""
import io
import json
import os
import unittest
from unittest.mock import patch
from astra_v2 import openai_creative


def payload(speech):
    visuals = ("fox", "fox", "fox", "fox")
    prompts = ("A fox stands beside a forest stream and looks toward the moonlight.",) * 4
    return {"status": "completed", "output": [{"content": [{"type": "output_text",
        "text": json.dumps({"title": "The Clockwork Moon's Secret",
                            "question": "What happened to the moon's missing light tonight?",
                            "answer": "The tiny robots restored the moon's missing light.",
                            "beats": [{"headline": f"Chapter {i} begins", "speech": speech[i],
                                       "visual": visuals[i], "visual_prompt": prompts[i],
                                       "story_environment": "forest",
                                       "label": f"Scene {i}", "story_beat": ("reveal", "build", "twist", "payoff")[i]}
                                      for i in range(4)]})}]}]}


class Response:
    def __init__(self, obj):
        self.obj = obj
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, *args):
        return json.dumps(self.obj).encode()
    def __iter__(self):
        return iter(())


class ModelRuntimeGateTests(unittest.TestCase):
    def run_story(self, lines):
        with patch.object(openai_creative, "enabled", return_value=True), \
             patch.object(openai_creative, "assert_no_paid_api"), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "test-placeholder"}), \
             patch.object(openai_creative.urllib.request, "urlopen", return_value=Response(payload(lines))), \
             patch.object(openai_creative.json, "load", side_effect=lambda response: response.obj):
            return openai_creative.generate(set(), set(), [])

    def test_rejects_thin_but_structurally_valid_model_story(self):
        lines = ["A little robot finds the moon's lost light today beside the quiet forest stream.",
                 "The robot repairs its damaged lamp before dawn arrives along the forest path.",
                 "A hidden switch opens and the light returns above the forest at last again.",
                 "Everyone celebrates when the moon shines brightly over the forest at last tonight."]
        with self.assertRaisesRegex(ValueError, "editorial"):
            self.run_story(lines)

    def test_model_remains_disabled_without_opt_in(self):
        with patch.dict(os.environ, {"ASTRA_OPENAI_ENABLED": "0", "ASTRA_OPENAI_ALLOW_PAID_API": "0"}):
            self.assertFalse(openai_creative.enabled())


if __name__ == "__main__":
    unittest.main()
