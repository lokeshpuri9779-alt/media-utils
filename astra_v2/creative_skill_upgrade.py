"""Optional, offline creative skill adapters. No network, publication or approval effects."""
from __future__ import annotations
import re
from urllib.parse import urlparse

CLICHES = ("in today's digital landscape", "delve deep", "testament to",
           "more than meets the eye", "in this video we will explore",
           "unlock the secrets", "game changer")

def anti_slop(script: str) -> dict:
    """Return explainable warnings; never auto-approve or silently rewrite."""
    if not isinstance(script, str):
        raise TypeError("script must be text")
    normalized = " ".join(script.casefold().split())
    matches = [phrase for phrase in CLICHES if phrase in normalized]
    sentences = [s.strip() for s in re.split(r"[.!?]+", normalized) if s.strip()]
    duplicates = sorted({s for s in sentences if sentences.count(s) > 1})
    return {"pass": not matches and not duplicates, "cliches": matches,
            "repeated_sentences": duplicates, "approval": False}

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
        if not isinstance(second, (int, float)) or not isinstance(retention, (int, float)):
            raise ValueError("numeric samples required")
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
        url = str(item.get("url", ""))
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            continue
        if not isinstance(item.get("title"), str) or not item["title"].strip():
            continue
        accepted.append({"title": item["title"].strip()[:200], "url": url,
                         "source": parsed.hostname.lower()})
    return {"items": accepted, "live_search_enabled": False,
            "editorial_approval": False}
