"""Generate unapproved story-specific PNGs with an explicitly configured Gemini image model.

No approval or publication is granted by generation. No paid fallback.
"""
import base64
import hashlib
import json
import os
import re
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

MAX_IMAGE_BYTES = 12 * 1024 * 1024


def generate_staged_art(story, destination, *, opener=None):
    if os.getenv("ASTRA_GEMINI_ART_ENABLED") != "1":
        raise ValueError("gemini_art_not_enabled")
    key = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("ASTRA_GEMINI_IMAGE_MODEL", "")
    if not key or not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", model):
        raise ValueError("gemini_art_credentials_or_model_missing")
    cid = story.get("content_id")
    beats = story.get("story_beats")
    if not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", cid):
        raise ValueError("invalid_story_content_id")
    if not isinstance(beats, list) or not 1 <= len(beats) <= 12:
        raise ValueError("invalid_story_beats")
    destination = Path(destination)
    if destination.exists():
        raise ValueError("art_staging_destination_exists")
    destination.mkdir(parents=True)
    opener = urllib.request.urlopen if opener is None else opener
    entries = []
    try:
        for i, beat in enumerate(beats):
            if not isinstance(beat, dict):
                raise ValueError("invalid_story_beat")
            prompt = str(beat.get("visual_prompt") or beat.get("visual") or "").strip()
            if len(prompt) < 12 or len(prompt) > 2400:
                raise ValueError("invalid_art_prompt")
            scene_id = str(beat.get("scene_id") or "scene-" + str(i + 1))
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", scene_id):
                raise ValueError("invalid_scene_id")
            body = {"contents": [{"parts": [{"text":
                "Original family-safe vertical 9:16 cinematic illustration. "
                "Keep characters and objects consistent across this story. "
                "No typography, logos, watermarks or panels. Scene: " + prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE"]}}
            request = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
                data=json.dumps(body).encode(), method="POST",
                headers={"Content-Type": "application/json", "x-goog-api-key": key})
            with opener(request, timeout=90) as response:
                payload = json.load(response)
            parts = [p for c in payload.get("candidates", []) for p in c.get("content", {}).get("parts", [])]
            images = [p["inlineData"] for p in parts if isinstance(p, dict) and "inlineData" in p]
            if len(images) != 1 or not images[0].get("mimeType", "").startswith("image/"):
                raise ValueError("gemini_image_response_missing")
            encoded = images[0].get("data", "")
            if len(encoded) > MAX_IMAGE_BYTES * 2:
                raise ValueError("gemini_image_too_large")
            raw = base64.b64decode(encoded, validate=True)
            if not raw or len(raw) > MAX_IMAGE_BYTES:
                raise ValueError("gemini_image_too_large")
            with Image.open(BytesIO(raw)) as image:
                image.load()
                if image.width < 256 or image.height < 256:
                    raise ValueError("gemini_image_too_small")
                if image.height <= image.width:
                    raise ValueError("gemini_image_not_vertical")
                image = image.convert("RGB")
                name = "scene-" + str(i + 1) + ".png"
                target = destination / name
                image.save(target, format="PNG")
            entries.append({"id": cid + "-" + scene_id, "story_content_id": cid,
                            "scene_id": scene_id, "category": "background",
                            "status": "pending_review", "source": "gemini-image",
                            "path": name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                            "tags": ["story-specific", "ai-generated"]})
        manifest = destination / "staging-manifest.json"
        manifest.write_text(json.dumps({"schema": "astra.art.staging.v1",
                                        "assets": entries, "publication_triggered": False},
                                       indent=2) + "\n", encoding="utf-8")
        return manifest
    except Exception:
        import shutil
        shutil.rmtree(destination)
        raise
