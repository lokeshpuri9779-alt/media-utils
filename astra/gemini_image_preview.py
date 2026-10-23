"""Opt-in Gemini image preview producer. Never approves or publishes artwork."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
import re
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

MODEL_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,80}")


def generate_preview(prompt: str, output_root: str | Path, *, model: str | None = None,
                     api_key: str | None = None, opener=None) -> dict:
    """Create one unapproved vertical PNG from Gemini image-capable model output."""
    if not isinstance(prompt, str) or not 12 <= len(prompt) <= 4000:
        raise ValueError("invalid_image_prompt")
    model = model or os.getenv("ASTRA_GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    if not MODEL_PATTERN.fullmatch(model):
        raise ValueError("invalid_image_model")
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("missing_gemini_api_key")
    body = json.dumps({"contents": [{"parts": [{"text": (
        "Create an original, family-safe, high-quality vertical 9:16 "
        "story illustration without text, watermarks or panels. " + prompt
    )}]}], "generationConfig": {"responseModalities": ["IMAGE"]}}).encode()
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
        data=body, method="POST",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"})
    transport = opener or urllib.request.urlopen
    with transport(request, timeout=90) as response:
        payload = json.load(response)
    candidates = payload.get("candidates") or []
    if not candidates or candidates[0].get("finishReason") not in (None, "STOP"):
        raise ValueError("image_generation_incomplete")
    parts = candidates[0].get("content", {}).get("parts", [])
    images = [p["inlineData"] for p in parts if isinstance(p, dict)
              and isinstance(p.get("inlineData"), dict)
              and str(p["inlineData"].get("mimeType", "")).startswith("image/")]
    if len(images) != 1:
        raise ValueError("expected_exactly_one_image")
    raw = base64.b64decode(images[0].get("data", ""), validate=True)
    if len(raw) > 20_000_000:
        raise ValueError("image_too_large")
    with Image.open(BytesIO(raw)) as opened:
        opened.verify()
    with Image.open(BytesIO(raw)) as opened:
        if opened.width < 256 or opened.height < 256:
            raise ValueError("image_too_small")
        # Preview-only crop: independent visual review must verify composition.
        image = ImageOps.fit(opened.convert("RGB"), (540, 960), method=Image.Resampling.LANCZOS)
    root = Path(output_root).resolve()
    folder = root / "art" / "assets" / "ai-preview"
    folder.mkdir(parents=True, exist_ok=True)
    identity = hashlib.sha256((model + "\n" + prompt).encode()).hexdigest()[:24]
    target = folder / (identity + ".png")
    image.save(target, format="PNG")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    row = {"id": "gemini-preview-" + identity,
           "path": target.relative_to(root).as_posix(),
           "category": "background", "tags": [],
           "source": "gemini-image", "status": "pending_review",
           "model": model, "sha256": digest}
    manifest = root / "art" / "ai-preview-manifest.json"
    # Never touch the production manifest or manufacture approval receipts.
    existing = json.loads(manifest.read_text()) if manifest.exists() else {"assets": []}
    if not isinstance(existing.get("assets"), list):
        raise ValueError("invalid_preview_manifest")
    existing["assets"] = [x for x in existing["assets"] if x.get("id") != row["id"]] + [row]
    manifest.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return {"manifest": str(manifest), "asset_id": row["id"], "status": "pending_review"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(generate_preview(args.prompt, args.output)))


if __name__ == "__main__":
    main()
