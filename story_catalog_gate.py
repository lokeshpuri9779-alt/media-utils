from __future__ import annotations

import re
from difflib import SequenceMatcher


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(text).lower()))


def hook_similarity(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    sa, sb = set(na.split()), set(nb.split())
    jac = len(sa & sb) / max(1, len(sa | sb))
    return round(max(seq, jac), 4)


def validate_catalog(stories: list[dict], recent_hooks: list[str] | None = None) -> dict:
    """Fail closed on malformed or repetitive candidate stories."""
    recent_hooks = list(recent_hooks or [])
    failures = []
    warnings = []
    seen = []

    required = ("content_id", "hook", "title", "source", "story_beats")
    for i, story in enumerate(stories):
        cid = str(story.get("content_id") or f"index-{i}")
        missing = [k for k in required if not story.get(k)]
        if missing:
            failures.append(f"{cid}: missing {', '.join(missing)}")
            continue
        beats = story.get("story_beats") or []
        if len(beats) < 3:
            failures.append(f"{cid}: fewer than 3 story beats")
        hook = str(story.get("hook") or "")
        if len(hook.split()) > 10:
            warnings.append(f"{cid}: hook longer than 10 words")

        for prior_cid, prior_hook in seen:
            sim = hook_similarity(hook, prior_hook)
            if sim >= 0.84:
                failures.append(f"{cid}: hook too similar to {prior_cid} ({sim:.2f})")
        for recent in recent_hooks:
            sim = hook_similarity(hook, recent)
            if sim >= 0.84:
                failures.append(f"{cid}: hook too similar to recent upload ({sim:.2f})")
        seen.append((cid, hook))

    return {
        "pass": not failures,
        "failures": failures,
        "warnings": warnings,
        "story_count": len(stories),
    }
