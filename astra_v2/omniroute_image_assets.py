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
    if not image_bytes:
        raise ValueError("Empty image")
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



def image_quality_report(image_bytes, kind):
    """Conservative pixel checks, not semantic or character-continuity approval."""
    validate_png(image_bytes, kind)
    with Image.open(io.BytesIO(image_bytes)) as source:
        sample = source.convert("RGB")
        sample.thumbnail((96, 96))
        colors = list(sample.getdata())
    count = len(colors)
    luminance = [sum(pixel) / 3 for pixel in colors]
    average = sum(luminance) / count
    variance = sum((value - average) ** 2 for value in luminance) / count
    issues = []
    if average < 18:
        issues.append("nearly_black")
    if average > 248:
        issues.append("nearly_white")
    if variance < 20 or len(set(colors)) < 12:
        issues.append("low_information")
    return {"passed": not issues, "issues": issues,
            "average_brightness": round(average, 2),
            "luminance_variance": round(variance, 2),
            "semantic_match": "not_verified",
            "character_continuity": "not_verified"}


def store_asset(image_bytes, root, *, kind, prompt, source="omniroute"):
    if kind not in ("scene", "character", "prop", "background", "thumbnail"):
        raise ValueError("Unsupported asset kind")
    dimensions = validate_png(image_bytes, kind)
    quality = image_quality_report(image_bytes, kind)
    if not quality["passed"]:
        raise ValueError("Image failed pixel quality checks: " + ",".join(quality["issues"]))
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
            "dimensions": dimensions, "quality": quality, "approved": False, "production_ready": False}


def preproduce(queue, root, *, generator=generate_image, limit=3):
    """Bound provider calls while retaining every scene and resuming cached work.

    Cache keys include the full narrative, bible, scene and provider/model. This
    does not assert that repeated text prompts guarantee visual consistency.
    """
    from astra_v2.story_art_direction import illustration_requests
    if not isinstance(limit, int) or not 1 <= limit <= 10:
        raise ValueError("Invalid generation limit")
    root = Path(root).resolve()
    cache = root / "requests"
    cache.mkdir(parents=True, exist_ok=True)
    output, calls = [], 0
    provider_missing = False
    for item in queue.get("rewrites", []):
        if item.get("status") != "awaiting_independent_editorial_approval":
            continue
        story = item.get("story") or {}
        try:
            requests = illustration_requests(story)
        except (ValueError, TypeError) as exc:
            output.append({"story_content_id": story.get("content_id"),
                           "status": "invalid_visual_plan", "error": str(exc),
                           "approved": False, "production_ready": False})
            continue
        for request in requests:
            prompt = request.pop("prompt")
            provider = [os.getenv("ASTRA_OMNI_IMAGE_ENDPOINT", ""),
                        os.getenv("ASTRA_OMNI_IMAGE_MODEL", "")]
            key = hashlib.sha256(json.dumps([provider, prompt]).encode()).hexdigest()
            record = cache / (key + ".json")
            row = {**request, "request_sha256": key,
                   "approved": False, "production_ready": False}
            try:
                if record.is_file():
                    saved = json.loads(record.read_text())
                    location = (root / saved["path"]).resolve()
                    if not location.is_relative_to(root):
                        raise ValueError("Unsafe cached asset path")
                    raw = location.read_bytes()
                    if hashlib.sha256(raw).hexdigest() != saved["sha256"]:
                        raise ValueError("Cached asset corruption")
                    quality = image_quality_report(raw, "scene")
                    if not quality["passed"]:
                        raise ValueError("Cached asset failed pixel quality checks")
                    row.update(saved)
                    row["quality"] = quality
                    # A cache entry cannot grant production approval.
                    row.update(approved=False, production_ready=False,
                               continuity_status="not_verified", status="cached_review_only")
                elif calls >= limit or provider_missing:
                    row["status"] = "provider_not_configured" if provider_missing else "pending_budget"
                else:
                    calls += 1
                    image = generator(prompt)
                    if image is None:
                        provider_missing = True
                        row["status"] = "provider_not_configured"
                    else:
                        asset = store_asset(image, root, kind="scene", prompt=prompt)
                        row.update(asset, status="review_only")
                        temporary = record.with_suffix(".tmp")
                        temporary.write_text(json.dumps(asset, sort_keys=True))
                        temporary.replace(record)
            except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
                row.update(status="generation_failed", error=type(exc).__name__)
            output.append(row)
    return {"status": "provider_not_configured" if provider_missing else "review_only",
            "provider_calls": calls, "assets": output,
            "production_ready": False, "continuity_status": "not_verified"}


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
