"""Independent multimodal Gemini assessment of staged artwork; never grants approval."""
import base64
import json
import os
import re
import urllib.request
from pathlib import Path

from astra_v2.staged_art_technical_review import audit_staged_art

REVIEW_SCHEMA = "astra.art.semantic-review.v1"
CRITERIA = ("scene_fidelity", "character_consistency", "object_integrity",
            "composition", "text_artifacts", "family_safety")


def review(story, manifest_path, *, opener=None):
    technical = audit_staged_art(manifest_path)
    if not technical["technical_pass"]:
        raise ValueError("technical_review_failed")
    if story.get("content_id") != technical["results"][0]["story_content_id"]:
        raise ValueError("story_identity_mismatch")
    if any(x["story_content_id"] != story["content_id"] for x in technical["results"]):
        raise ValueError("mixed_story_artwork")
    beats = story.get("story_beats")
    if not isinstance(beats, list) or len(beats) != len(technical["results"]):
        raise ValueError("story_scene_count_mismatch")
    model = os.getenv("ASTRA_GEMINI_ART_REVIEW_MODEL", "")
    key = os.getenv("GEMINI_API_KEY", "")
    if not key or not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", model):
        raise ValueError("review_model_or_key_missing")
    path = Path(manifest_path)
    assets = json.loads(path.read_text())["assets"]
    parts = [{"text": (
        "You are an independent visual quality auditor, not an artwork approver. "
        "Evaluate every image against its corresponding story scene and all other images. "
        "Check causal scene accuracy, character/species/clothing consistency, object "
        "continuity, cropping/overlaps, anatomy, typography/watermarks and family safety. "
        "Return ONLY a JSON object with 'scenes' array, each element containing "
        "'scene_id', six boolean criteria: " + ", ".join(CRITERIA) +
        ", and 'issues' as an array of concise strings. All booleans must be true "
        "only when evidence supports passing. Do not claim final approval. "
        "Story: " + json.dumps({"title": story.get("title"),
                                "visual_bible": story.get("visual_bible"),
                                "beats": [{"scene_id": a["scene_id"],
                                           "visual_prompt": b.get("visual_prompt", ""),
                                           "speech": b.get("speech", "")}
                                          for a, b in zip(assets, beats)]}))}]
    for asset in assets:
        raw = (path.parent / asset["path"]).read_bytes()
        parts.append({"text": "Image for scene_id " + asset["scene_id"]})
        parts.append({"inline_data": {"mime_type": "image/png",
                                       "data": base64.b64encode(raw).decode("ascii")}})
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseMimeType": "application/json"}}
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    opener = opener or urllib.request.urlopen
    with opener(request, timeout=90) as response:
        result = json.load(response)
    candidates = result.get("candidates", [])
    if len(candidates) != 1:
        raise ValueError("ambiguous_semantic_review_response")
    content = "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", []))
    data = json.loads(content)
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != len(assets):
        raise ValueError("invalid_semantic_review_scene_count")
    expected = {a["scene_id"] for a in assets}
    if {s.get("scene_id") for s in scenes if isinstance(s, dict)} != expected:
        raise ValueError("semantic_review_scene_mismatch")
    for scene in scenes:
        if any(type(scene.get(k)) is not bool for k in CRITERIA):
            raise ValueError("semantic_review_missing_boolean_criterion")
        if not isinstance(scene.get("issues"), list) or any(not isinstance(x, str) for x in scene["issues"]):
            raise ValueError("semantic_review_invalid_issues")
    return {"schema": REVIEW_SCHEMA, "story_content_id": story["content_id"],
            "scenes": scenes, "technical_pass": True,
            "semantic_pass": all(all(s[k] for k in CRITERIA) and not s["issues"] for s in scenes),
            "independent_visual_approval": False, "publication_triggered": False}
