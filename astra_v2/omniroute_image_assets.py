"""Preproduce immutable image assets through an explicitly configured OmniRoute image endpoint.

Disabled by default. Never falls back to paid providers or marks stories approved.
"""
import argparse
import base64
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import urllib.request
import urllib.error

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
    native_gemini = endpoint.startswith("https://generativelanguage.googleapis.com/") and ":generateContent" in endpoint
    cloudflare = endpoint.startswith("https://api.cloudflare.com/client/v4/accounts/") and "/ai/run/" in endpoint
    if cloudflare:
        if model != "@cf/black-forest-labs/flux-1-schnell" or not endpoint.endswith("/ai/run/" + model):
            raise ValueError("Cloudflare endpoint/model mismatch or unsupported model")
        payload = json.dumps({"prompt": prompt[:2048], "steps": 4}).encode()
    elif native_gemini:
        payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                              "generationConfig": {"responseModalities": ["IMAGE"],
                                                   "imageConfig": {"aspectRatio": "9:16"}}}).encode()
    else:
        payload = json.dumps({"model": model, "prompt": prompt, "size": "1024x1536",
                              "response_format": "b64_json"}).encode()
    headers = {"Content-Type": "application/json"}
    key = os.getenv("ASTRA_OMNI_IMAGE_API_KEY", "")
    if key:
        headers["x-goog-api-key" if native_gemini else "Authorization"] = key if native_gemini else "Bearer " + key
    request = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    if requester is None:
        def requester(req):
            with urllib.request.urlopen(req, timeout=90) as response:
                return response.read(MAX_BYTES + 1)
    try:
        raw = requester(request)
    except urllib.error.HTTPError as exc:
        # Preserve safe status information without logging API keys or prompts.
        # Persist numeric status codes only, never provider text or credentials.
        code = ""
        if cloudflare:
            try:
                details = json.loads(exc.read(4096))
                errors = details.get("errors", [])
                numeric = [str(e["code"]) for e in errors if isinstance(e, dict)
                           and isinstance(e.get("code"), int)]
                if numeric:
                    code = " Cloudflare code=" + ",".join(numeric[:3])
            except (ValueError, TypeError, KeyError, AttributeError):
                pass
        raise ValueError(f"Image provider HTTP {exc.code}" + code) from exc
    if len(raw) > MAX_BYTES:
        raise ValueError("Image response too large")
    # Some compatible image endpoints return image bytes directly instead of JSON.
    # Accept only validated PNG/JPEG signatures; all other responses remain JSON.
    if not native_gemini and (raw.startswith(b"\x89PNG\r\n\x1a\n") or raw.startswith(b"\xff\xd8\xff")):
        with Image.open(io.BytesIO(raw)) as source:
            source.verify()
        with Image.open(io.BytesIO(raw)) as source:
            if source.format not in ("PNG", "JPEG"):
                raise ValueError("Unsupported direct image response")
            if source.format == "PNG":
                return raw
            output = io.BytesIO()
            source.convert("RGB").save(output, format="PNG")
            decoded = output.getvalue()
            if len(decoded) > MAX_BYTES:
                raise ValueError("Normalized PNG image too large")
            return decoded
    response = json.loads(raw)
    if cloudflare:
        if not response.get("success", False) or not isinstance(response.get("result"), dict):
            errors = response.get("errors", [])
            numeric = [str(e["code"]) for e in errors if isinstance(e, dict)
                       and isinstance(e.get("code"), int)] if isinstance(errors, list) else []
            raise ValueError("Cloudflare image generation unsuccessful"
                             + (" code=" + ",".join(numeric[:3]) if numeric else ""))
        encoded = response["result"].get("image")
        if not isinstance(encoded, str):
            raise ValueError("Cloudflare did not return base64 image")
        decoded = base64.b64decode(encoded, validate=True)
        if len(decoded) > MAX_BYTES:
            raise ValueError("Cloudflare image too large")
        with Image.open(io.BytesIO(decoded)) as source:
            source.verify()
        with Image.open(io.BytesIO(decoded)) as source:
            if source.format not in ("JPEG", "PNG"):
                raise ValueError("Cloudflare image format unsupported")
            output = io.BytesIO()
            source.convert("RGB").save(output, format="PNG")
            normalized = output.getvalue()
        if len(normalized) > MAX_BYTES:
            raise ValueError("Cloudflare normalized image too large")
        return normalized
    if native_gemini:
        parts = [part for candidate in response.get("candidates", [])
                 for part in candidate.get("content", {}).get("parts", [])
                 if isinstance(part, dict)]
        images = [part["inlineData"] for part in parts
                  if isinstance(part.get("inlineData"), dict)
                  and part["inlineData"].get("mimeType") in ("image/png", "image/jpeg")
                  and isinstance(part["inlineData"].get("data"), str)]
        if len(images) != 1:
            raise ValueError("Gemini did not return exactly one supported image")
        encoded = images[0]["data"]
        image_mime = images[0]["mimeType"]
    else:
        data = response.get("data", [])
        if not isinstance(data, list) or not data or not isinstance(data[0], dict) or not isinstance(data[0].get("b64_json"), str):
            raise ValueError("Provider did not return base64 image")
        encoded = data[0]["b64_json"]
    if len(encoded) > MAX_BYTES:
        raise ValueError("Encoded image too large")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("Provider returned invalid base64 image") from exc
    if len(decoded) > MAX_BYTES:
        raise ValueError("Decoded image too large")
    if native_gemini and image_mime == "image/jpeg":
        # Gemini may return JPEG; Studio's immutable asset warehouse requires PNG.
        with Image.open(io.BytesIO(decoded)) as source:
            source.verify()
        with Image.open(io.BytesIO(decoded)) as source:
            if source.format != "JPEG":
                raise ValueError("Gemini image MIME does not match its content")
            output = io.BytesIO()
            source.convert("RGB").save(output, format="PNG")
            decoded = output.getvalue()
        if len(decoded) > MAX_BYTES:
            raise ValueError("Normalized PNG image too large")
    return decoded


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
        temporary = location.with_name(location.name + ".tmp")
        try:
            temporary.write_bytes(image_bytes)
            temporary.replace(location)
        finally:
            temporary.unlink(missing_ok=True)
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
    provider_quota_exhausted = False
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
                    if saved.get("prompt_sha256") != hashlib.sha256(prompt.encode()).hexdigest():
                        raise ValueError("Cached asset prompt mismatch")
                    if saved.get("kind") != "scene":
                        raise ValueError("Cached asset kind mismatch")
                    row.update({k: saved[k] for k in ("sha256", "path", "kind", "source", "prompt_sha256", "dimensions") if k in saved})
                    row["quality"] = quality
                    # A cache entry cannot grant production approval.
                    row.update(approved=False, production_ready=False,
                               continuity_status="not_verified", status="cached_review_only")
                elif calls >= limit or provider_missing or provider_quota_exhausted:
                    row["status"] = ("provider_quota_exhausted" if provider_quota_exhausted else
                                     "provider_not_configured" if provider_missing else "pending_budget")
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
                # Whitelist only provider codes, never arbitrary exception text.
                diagnostic = str(exc) if isinstance(exc, ValueError) else ""
                if not (diagnostic.startswith("Image provider HTTP ")
                        or diagnostic.startswith("Cloudflare image generation unsuccessful")
                        or diagnostic in ("Cloudflare did not return base64 image",
                                          "Cloudflare image format unsupported",
                                          "Image resolution too small",
                                          "Scenes must be portrait")):
                    diagnostic = type(exc).__name__
                if diagnostic.startswith("Image provider HTTP 429"):
                    provider_quota_exhausted = True
                row.update(status="generation_failed", error=type(exc).__name__,
                           error_detail=diagnostic[:120])
            output.append(row)
    return {"status": ("provider_quota_exhausted" if provider_quota_exhausted else
                       "provider_not_configured" if provider_missing else "review_only"),
            "provider_calls": calls, "assets": output,
            "production_ready": False, "continuity_status": "not_verified"}



def export_reviewed_render_manifest(preproduction, root, decisions, destination):
    """Bridge independently approved scene art into Studio's exact-ID manifest.

    Decisions are keyed by request_sha256 and must include the matching asset
    sha256. Never derive approval from a generated asset's own metadata.
    """
    if not isinstance(decisions, dict):
        raise ValueError("Review decisions must be an object")
    signing_key = os.getenv("ASTRA_ART_REVIEW_HMAC_KEY", "")
    if len(signing_key) < 32:
        raise ValueError("Independent review signing key must contain at least 32 characters")
    root = Path(root).resolve()
    destination = Path(destination)
    assets = []
    for row in preproduction.get("assets", []):
        if row.get("status") not in ("review_only", "cached_review_only"):
            continue
        request_id = row.get("request_sha256")
        decision = decisions.get(request_id)
        if not isinstance(decision, dict) or decision.get("approved") is not True:
            continue
        if decision.get("sha256") != row.get("sha256"):
            raise ValueError("Review approval does not match image digest")
        if decision.get("semantic_match") is not True or decision.get("character_continuity") is not True:
            raise ValueError("Independent visual review is incomplete")
        content_id, scene_id = row.get("story_content_id"), row.get("scene_id")
        if not content_id or not scene_id:
            raise ValueError("Approved scene identity missing")
        location = (root / row["path"]).resolve()
        if not location.is_relative_to(root):
            raise ValueError("Unsafe image path")
        raw = location.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("Reviewed image digest mismatch")
        quality = image_quality_report(raw, "scene")
        if not quality["passed"]:
            raise ValueError("Reviewed image failed quality checks")
        assets.append({"id": "reviewed-" + request_id, "path": str(location),
                       "category": "background", "tags": [],
                       "status": "approved", "source": row.get("source", "omniroute"),
                       "story_content_id": content_id, "scene_id": scene_id,
                       "sha256": row["sha256"],
                       "review_status": "approved",
                       "review_receipt_sha256": hmac.new(signing_key.encode(),
                           json.dumps({"asset_id": "reviewed-" + request_id,
                                       "sha256": row["sha256"],
                                       "story_content_id": content_id,
                                       "scene_id": scene_id,
                                       "decision": decision},
                                      sort_keys=True, separators=(",", ":")).encode(),
                           hashlib.sha256).hexdigest(),
                       "review_decision": decision})
    if not assets:
        raise ValueError("No independently approved scene illustrations")
    # Studio resolves asset paths relative to the manifest's grandparent.
    render_root = destination.parent.parent.resolve()
    for asset in assets:
        location = Path(asset["path"])
        if not location.is_relative_to(render_root):
            raise ValueError("Approved image is outside renderer asset root")
        asset["path"] = location.relative_to(render_root).as_posix()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"assets": assets}, indent=2) + "\n")
    return {"manifest": str(destination), "assets": len(assets)}


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
