"""Independent AI editorial assessment; existing approval manifest remains authoritative.

This module deliberately does not write approval manifests or publish videos.
"""
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

from astra_v2.editorial_approval_manifest import story_digest, review_decision
from astra_v2.production_story_gate import candidate_issues


def assess(story, history=(), *, model=None, api_key=None, transport=None):
    """Return a traceable record only when full-story review passes every gate."""
    if not isinstance(story, dict):
        raise ValueError("story_must_be_object")
    problems = candidate_issues(story, history)
    if problems:
        return {"approved": False, "issues": sorted(set(problems)), "record": None}
    model = model or os.getenv("ASTRA_EDITORIAL_REVIEW_MODEL", "gemini-3.1-flash-lite")
    api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"approved": False, "issues": ["reviewer_unavailable"], "record": None}
    import re
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", model):
        raise ValueError("invalid_reviewer_model")
    prompt = (
        "You are an independent editorial reviewer. Assess the ENTIRE story for "
        "originality, causal coherence, clarity, copyright/trademark concerns, "
        "unsafe or misleading content, audience suitability, and YouTube policy "
        "risks. Do not assume originality merely because the author is AI. "
        "Assess whether the story repeats recently published premises, characters, "
        "settings, causal mechanisms or endings when comparison history is supplied. "
        "Do not reject solely for sharing a genre or common vocabulary. "
        'Return JSON only: {"decision":"approve or reject",'
        '"reasons":["specific evidence-based reasons"]}. '
        "Reject if uncertain or unable to review fully. Story:\n"
        + json.dumps(story, ensure_ascii=False, sort_keys=True)
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0,
                             "maxOutputTokens": 1200}
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
        data=payload, method="POST",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"})
    try:
        if transport is None:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
        else:
            result = transport(request)
        candidates = result.get("candidates") or []
        if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
            raise ValueError("incomplete_review")
        parts = candidates[0]["content"]["parts"]
        answer = json.loads("".join(p["text"] for p in parts))
        reasons = answer.get("reasons")
        if (answer.get("decision") not in ("approve", "reject")
                or not isinstance(reasons, list) or not reasons
                or any(not isinstance(x, str) or not x.strip() for x in reasons)):
            raise ValueError("invalid_review_schema")
    except (ValueError, KeyError, TypeError, OSError, urllib.error.URLError) as exc:
        return {"approved": False, "issues": ["review_failed:" + type(exc).__name__], "record": None}
    if answer["decision"] != "approve":
        return {"approved": False, "issues": ["ai_editorial_rejection"] + reasons, "record": None}
    record = {
        "content_id": story["content_id"],
        "story_sha256": story_digest(story),
        "decision": "approve",
        "reviewer": "Independent Gemini editorial reviewer: " + model,
        "review_notes": "; ".join(reasons),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_model": model,
    }
    blockers = review_decision(story, record, history)
    return {"approved": not blockers, "issues": blockers, "record": record if not blockers else None}
