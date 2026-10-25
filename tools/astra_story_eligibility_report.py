"""Explain which authored ASTRA stories are actually render-compatible.

This is a read-only supply diagnostic; it does not authorize an upload,
promote drafts, or bypass any publication/rendering quality check.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from collections import Counter

from astra_v2.publication_quality import publication_rejection
from astra_v2.story_forge import catalog


def audit() -> dict:
    stories = catalog(limit=2000)
    causes = Counter()
    samples = []
    blocked_scenes = []
    for story in stories:
        reason = publication_rejection(story)
        if reason:
            causes[reason.split(":", 1)[0]] += 1
            shot = re.search(r"shot (\d+):", reason)
            number = int(shot.group(1)) if shot else None
            beats = story.get("story_beats") or []
            scene = beats[number - 1] if number and number <= len(beats) else {}
            blocked_scenes.append({
                "content_id": story["content_id"], "title": story["title"],
                "shot_number": number, "reason": reason[:250],
                "narration": scene.get("speech") if isinstance(scene, dict) else None,
                "declared_visual": scene.get("visual") if isinstance(scene, dict) else None,
                "approval": False, "publication_eligible": False,
            })
            if len(samples) < 12:
                samples.append({"content_id": story["content_id"],
                                "title": story["title"],
                                "reason": reason[:210]})
        else:
            causes["eligible"] += 1
    return {
        "schema_version": 1,
        "authored_catalog": len(stories),
        "render_eligible": causes["eligible"],
        "rejected": len(stories) - causes["eligible"],
        "by_reason": dict(sorted(causes.items())),
        "rejection_samples": samples,
        "blocked_scene_queue": blocked_scenes,
        "note": "Editorial authored status is NOT video render/publication proof.",
    }


def main() -> None:
    data = audit()
    out = Path("runtime-health/renderer-artwork-gaps.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    summary = {k: v for k, v in data.items() if k not in ("blocked_scene_queue", "rejection_samples")}
    print("ASTRA_RENDERER_ELIGIBILITY_AUDIT=" + json.dumps(summary, sort_keys=True))
    print("ASTRA_RENDERER_ARTWORK_GAPS=" + str(out))
    if data["render_eligible"] < 1:
        raise SystemExit("no_render_eligible_stories")


if __name__ == "__main__":
    main()
