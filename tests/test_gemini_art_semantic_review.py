import base64
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from astra_v2.gemini_art_semantic_review import review, CRITERIA


class FakeResponse:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, *args):
        return json.dumps(self.data).encode()


class SemanticArtReviewTests(unittest.TestCase):
    def test_multimodal_review_never_approves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "scene-1.png"
            Image.new("RGB", (360, 640), (20, 30, 40)).save(image)
            manifest = root / "staging-manifest.json"
            manifest.write_text(json.dumps({"schema": "astra.art.staging.v1",
                "publication_triggered": False, "assets": [{
                "scene_id": "scene-1", "story_content_id": "story1",
                "status": "pending_review", "path": image.name,
                "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}]}))
            response = {"candidates": [{"content": {"parts": [{"text": json.dumps({
                "scenes": [{"scene_id": "scene-1", "issues": [],
                            **{k: True for k in CRITERIA}}]})}]}}]}
            with patch.dict(os.environ, {"GEMINI_API_KEY": "fake",
                                          "ASTRA_GEMINI_ART_REVIEW_MODEL": "test-model"}):
                report = review({"content_id": "story1", "title": "Test",
                                 "story_beats": [{"visual_prompt": "A fox near a river"}]},
                                manifest, opener=lambda *a, **k: FakeResponse(response))
            self.assertTrue(report["semantic_pass"])
            self.assertFalse(report["independent_visual_approval"])
            self.assertFalse(report["publication_triggered"])

    def test_bad_story_identity_fails_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "staging-manifest.json"
            manifest.write_text(json.dumps({"schema": "astra.art.staging.v1",
                                             "publication_triggered": False, "assets": []}))
            with self.assertRaises(ValueError):
                review({"content_id": "other", "story_beats": []}, manifest)


if __name__ == "__main__":
    unittest.main()
