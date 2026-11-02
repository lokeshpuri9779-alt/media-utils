"""Optional, offline creative skill adapters. No network, publication or approval effects."""
from __future__ import annotations
import math
import re
from urllib.parse import urlparse

CLICHES = ("in today's digital landscape", "delve deep", "testament to",
           "more than meets the eye", "in this video we will explore",
           "unlock the secrets", "game changer")

def anti_slop(script: str) -> dict:
    """Return explainable warnings; never auto-approve or silently rewrite."""
    if not isinstance(script, str):
        raise TypeError("script must be text")
    if len(script) > 100_000:
        raise ValueError("script exceeds advisory limit")
    normalized = " ".join(script.casefold().split())
    matches = [phrase for phrase in CLICHES
               if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", normalized)]
    sentences = [s.strip() for s in re.split(r"[.!?]+", normalized) if s.strip()]
    counts = {}
    for sentence in sentences:
        counts[sentence] = counts.get(sentence, 0) + 1
    duplicates = sorted(s for s, count in counts.items() if count > 1)
    return {"pass": not matches and not duplicates, "cliches": matches,
            "repeated_sentences": duplicates, "approval": False}

def story_advisory(story: dict) -> dict:
    """Summarize script findings without exposing story text or granting approval.

    An advisory is not a semantic video check, production gate, or edit request.
    """
    if not isinstance(story, dict):
        raise TypeError("story must be a mapping")
    beats = story.get("story_beats") or []
    if not isinstance(beats, list):
        return {"status": "invalid_beats", "cliche_count": 0,
                "repeated_sentence_count": 0, "approval": False}
    narration = " ".join(str(b.get("speech") or "") for b in beats if isinstance(b, dict))
    if not narration.strip():
        return {"status": "no_narration", "cliche_count": 0,
                "repeated_sentence_count": 0, "approval": False}
    try:
        findings = anti_slop(narration)
    except ValueError:
        return {"status": "script_too_long", "cliche_count": 0,
                "repeated_sentence_count": 0, "approval": False}
    return {"status": "review_suggested" if not findings["pass"] else "no_simple_flags",
            "cliche_count": len(findings["cliches"]),
            "repeated_sentence_count": len(findings["repeated_sentences"]),
            "approval": False}


def script_brief(topic: str, format_name: str = "shorts", preferences: dict | None = None) -> dict:
    """Declarative brief for the existing script engine; no external model."""
    if format_name not in ("shorts", "longform"):
        raise ValueError("unsupported format")
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("topic required")
    prefs = preferences or {}
    if not isinstance(prefs, dict):
        raise TypeError("preferences must be a mapping")
    return {"topic": topic.strip(), "format": format_name,
            "hook_seconds": 3, "style": str(prefs.get("style", "concrete and natural"))[:120],
            "visual_feasibility_required": True, "editorial_approval": False}

def workflow_plan(topic: str, format_name: str = "shorts") -> dict:
    """Connect existing stages conceptually without replacing their implementations."""
    brief = script_brief(topic, format_name)
    return {"brief": brief, "stages": ("topic", "research", "script", "anti_slop",
            "visual_feasibility", "storyboard", "render", "semantic_review",
            "editorial_approval", "seo", "publish"), "publish_allowed": False}

def retention_review(points: list[dict]) -> dict:
    """Review observed retention samples; do not invent audience measurements."""
    if not points:
        return {"status": "no_analytics", "drops": []}
    samples = []
    for point in points:
        second, retention = point["second"], point["retention"]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in (second, retention)):
            raise ValueError("finite numeric samples required")
        if second < 0 or not 0 <= retention <= 1:
            raise ValueError("invalid retention sample")
        samples.append((second, retention))
    if len({s for s, _ in samples}) != len(samples):
        raise ValueError("duplicate timestamps")
    samples.sort()
    return {"status": "observed", "drops": [
        {"second": t, "drop": round(prev - value, 4)}
        for (_, prev), (t, value) in zip(samples, samples[1:])
        if prev - value >= 0.15]}

def research_intake(items: list[dict]) -> dict:
    """Validate supplied public research metadata; never crawl or use paid APIs."""
    accepted = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        if (not isinstance(url, str) or len(url) > 2048 or "\\" in url
                or any(ord(c) < 32 for c in url)):
            continue
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            _ = parsed.port
        except ValueError:
            continue
        if (parsed.scheme != "https" or not hostname or parsed.username or parsed.password
                or hostname in ("localhost", "127.0.0.1", "::1")):
            continue
        if not isinstance(item.get("title"), str) or not item["title"].strip():
            continue
        accepted.append({"title": item["title"].strip()[:200], "url": url,
                         "source": parsed.hostname.lower()})
    return {"items": accepted, "live_search_enabled": False,
            "editorial_approval": False}
