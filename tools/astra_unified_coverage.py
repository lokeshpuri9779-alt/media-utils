"""Fail-closed preflight audit of every currently eligible ASTRA story."""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from astra_v2.publication_quality import publication_rejection
from astra_v2.story_forge import catalog
from astra_v2.renderer_eligibility import check_renderer_eligibility


def audit():
    old = os.environ.get("ASTRA_UNIFIED_STORY_ENGINE")
    os.environ["ASTRA_UNIFIED_STORY_ENGINE"] = "1"
    failed = []
    modes = Counter()
    ready = 0
    inspected = 0
    try:
        for story in catalog(limit=256):
            inspected += 1
            if not story.get("production_ready") or publication_rejection(story):
                continue
            eligible, reason, scene_modes = check_renderer_eligibility(story)
            if not eligible:
                failed.append({"content_id": story.get("content_id"),
                               "title": story.get("title"),
                               "reason": reason})
                continue
            ready += 1
            modes.update(scene_modes)
    finally:
        if old is None:
            os.environ.pop("ASTRA_UNIFIED_STORY_ENGINE", None)
        else:
            os.environ["ASTRA_UNIFIED_STORY_ENGINE"] = old
    report = {"stories_scanned": inspected,
              "eligible_stories_checked": ready,
              "renderer_incompatible_stories": len(failed),
              "eligible_stories_rejected": len(failed),
              "validated_fiction_scenes": dict(modes),
              "failures": failed}
    Path("runtime-health").mkdir(exist_ok=True)
    Path("runtime-health/astra-unified-coverage.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("ASTRA_UNIFIED_STORY_COVERAGE=" + json.dumps(report))
    if not ready:
        raise RuntimeError("No renderer-compatible production-ready stories were found; audit invalid")
    if failed:
        raise RuntimeError(f"Unified Studio rejected {len(failed)} production-ready catalog stories")
    return report


if __name__ == "__main__":
    audit()
