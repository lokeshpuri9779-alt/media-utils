"""Fail-closed preflight audit of every currently eligible ASTRA story."""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from astra_errors import CreativeReject
from astra_v2.publication_quality import publication_rejection
from astra_v2.story_forge import catalog
from astra_v2.layer_contract import scene_layers
from astra_v2.unified_story_engine import validate_story_shot
from studio_renderer import make_plan


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
            ready += 1
            try:
                plan = make_plan(dict(story))
                if not plan:
                    raise CreativeReject("Empty directed plan")
                for idx, shot in enumerate(plan, start=1):
                    if story.get("genre") != "fiction" or not scene_layers(shot)["draw_visual"]:
                        continue
                    try:
                        mode = validate_story_shot(shot)
                    except (CreativeReject, ValueError) as exc:
                        raise CreativeReject(f"shot {idx}: {exc}") from exc
                    modes[mode] += 1
            except (CreativeReject, ValueError, KeyError, TypeError) as exc:
                failed.append({"content_id": story.get("content_id"),
                               "title": story.get("title"),
                               "reason": str(exc)[:220]})
    finally:
        if old is None:
            os.environ.pop("ASTRA_UNIFIED_STORY_ENGINE", None)
        else:
            os.environ["ASTRA_UNIFIED_STORY_ENGINE"] = old
    report = {"stories_scanned": inspected,
              "eligible_stories_checked": ready,
              "eligible_stories_rejected": len(failed),
              "validated_fiction_scenes": dict(modes),
              "failures": failed}
    Path("runtime-health").mkdir(exist_ok=True)
    Path("runtime-health/astra-unified-coverage.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("ASTRA_UNIFIED_STORY_COVERAGE=" + json.dumps(report))
    if not ready:
        raise RuntimeError("No production-ready stories were found; audit invalid")
    if failed:
        raise RuntimeError(f"Unified Studio rejected {len(failed)} currently eligible stories")
    return report


if __name__ == "__main__":
    audit()
