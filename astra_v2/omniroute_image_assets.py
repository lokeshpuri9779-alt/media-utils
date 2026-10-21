"""Preproduce immutable image assets through an explicitly configured OmniRoute image endpoint.

Disabled by default. Never falls back to paid providers or marks stories approved.
"""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import urllib.request

from PIL import Image

MAX_BYTES = 12 * 1024 * 1024


def image_endpoint():
    endpoint = os.getenv("ASTRA_OMNI_IMAGE_ENDPOINT", "").strip()
    model = os.getenv("ASTRA_OMNI_IMAGE_MODEL", "").strip()
    if not endpoint or not model:
        return None
    if not endpoint.startswith("https://"):
        raise ValueError("Image endpoint must use HTTPS")
    if os.getenv("ASTRA_OMNI_IMAGE_ALLOW_PAID", "0") != "0":
        raise ValueError("Paid image generation is not permitted")
    if os.getenv("ASTRA_OMNI_IMAGE_FREE_CONFIRMED") != "1":
        raise ValueError("Explicit free-tier confirmation required")
    return endpoint, model


def generate_image(prompt, *, requester=None):
    config = image_endpoint()
    if config is None:
        return None
    endpoint, model = config
    payload = json.dumps({"model": model, "prompt": prompt, "size": "1024x1536",
                          "response_format": "b64_json"}).encode()
    headers = {"Content-Type": "application/json"}
    key = os.getenv("ASTRA_OMNI_IMAGE_API_KEY", "")
    if key:
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    if requester is None:
        def requester(req):
            with urllib.request.urlopen(req, timeout=90) as response:
                return response.read(MAX_BYTES + 1)
    raw = requester(request)
    if len(raw) > MAX_BYTES:
        raise ValueError("Image response too large")
    response = json.loads(raw)
    data = response.get("data", [])
    if not data or not isinstance(data[0].get("b64_json"), str):
        raise ValueError("Provider did not return base64 image")
    encoded = data[0]["b64_json"]
    if len(encoded) > MAX_BYTES:
        raise ValueError("Encoded image too large")
    return base64.b64decode(encoded, validate=True)


def validate_png(image_bytes, kind):
    if len(image_bytes) > MAX_BYTES:
        raise ValueError("Image too large")
    with Image.open(io.BytesIO(image_bytes)) as im:
        im.verify()
    with Image.open(io.BytesIO(image_bytes)) as im:
        if im.format != "PNG":
            raise ValueError("Only PNG assets are accepted")
        width, height = im.size
        if width < 512 or height < 512:
            raise ValueError("Image resolution too small")
        if kind == "scene" and height <= width:
            raise ValueError("Scenes must be portrait")
        if kind in ("character", "prop") and ("A" not in im.getbands()
                or im.getchannel("A").getextrema()[0] == 255):
            raise ValueError("Character and prop images require transparency")
    return {"width": width, "height": height}


def store_asset(image_bytes, root, *, kind, prompt, source="omniroute"):
    if kind not in ("scene", "character", "prop", "background", "thumbnail"):
        raise ValueError("Unsupported asset kind")
    dimensions = validate_png(image_bytes, kind)
    digest = hashlib.sha256(image_bytes).hexdigest()
    root = Path(root)
    location = root / "sha256" / digest[:2] / (digest + ".png")
    location.parent.mkdir(parents=True, exist_ok=True)
    if location.exists():
        if hashlib.sha256(location.read_bytes()).hexdigest() != digest:
            raise ValueError("Stored asset corruption")
    else:
        location.write_bytes(image_bytes)
    return {"sha256": digest, "path": str(location.relative_to(root)),
            "kind": kind, "source": source, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "dimensions": dimensions, "approved": False, "production_ready": False}


def preproduce(queue, root, *, generator=generate_image, limit=3):
    output = []
    for item in queue.get("rewrites", []):
        if len(output) >= limit:
            break
        if item.get("status") != "awaiting_independent_editorial_approval":
            continue
        story = item.get("story") or {}
        beats = story.get("story_beats") or []
        if not beats:
            continue
        prompt = ("Original family-safe cinematic portrait scene, no text, no logos. "
                  + str(story.get("title", ""))[:100] + ". "
                  + str(beats[0].get("speech", ""))[:250])
        try:
            image = generator(prompt)
            if image is None:
                return {"status": "provider_not_configured", "assets": output}
            asset = store_asset(image, root, kind="scene", prompt=prompt)
            asset["story_content_id"] = story.get("content_id")
            output.append(asset)
        except (ValueError, OSError, RuntimeError) as exc:
            output.append({"story_content_id": story.get("content_id"),
                           "status": "generation_failed", "error": type(exc).__name__,
                           "approved": False})
    return {"status": "review_only", "assets": output}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.limit <= 10:
        raise ValueError("Invalid generation limit")
    queue = json.loads(Path(args.queue).read_text())
    result = preproduce(queue, args.root, limit=args.limit)
    Path(args.manifest).write_text(json.dumps(result, indent=2) + "\n")
    print("ASTRA_OMNI_IMAGE_RESULT=" + json.dumps({"status": result["status"],
        "assets": len(result["assets"])}))


if __name__ == "__main__":
    main()
