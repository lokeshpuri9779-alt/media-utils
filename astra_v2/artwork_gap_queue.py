"""Review-only repair queue for fiction scenes missing verified backgrounds.

No image generation, source mutation, publication approval, or YouTube activity.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

FIELDS = ("story_environment", "scene_environment", "scene_location", "setting",
          "visual_prompt", "visual_intent", "visual", "speech", "story_level_environment")


def _text(value, limit=160):
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def build_repair_queue(selection, *, lane):
    """Build bounded, explicitly unapproved evidence from rejected candidates."""
    if not isinstance(selection, dict) or not selection.get("background_review_gaps"):
        return None
    if type(lane) is not int or not 0 <= lane < 16:
        raise ValueError("invalid preload lane")
    gaps = []
    for source in selection["background_review_gaps"][:24]:
        if not isinstance(source, dict):
            continue
        cid = _text(source.get("content_id"), 96)
        rows = []
        raw = source.get("missing_shots")
        for row in (raw[:24] if isinstance(raw, list) else []):
            if not isinstance(row, dict):
                continue
            shot, reason = row.get("shot"), row.get("reason")
            if (type(shot) is not int or not 1 <= shot <= 256 or
                    reason not in ("scene_unresolved", "no_matching_background")):
                continue
            context = row.get("authored_context")
            context = context if isinstance(context, dict) else {}
            fields = context.get("authored_fields")
            fields = fields if isinstance(fields, dict) else {}
            excerpts = {k: _text(fields[k]) for k in FIELDS if _text(fields.get(k))}
            evidence = {
                "shot": shot, "reason": reason,
                "authored_context": {
                    "source": "unmodified_story_input" if context.get("source_beat_found") is True else "unavailable",
                    "source_beat_found": context.get("source_beat_found") is True,
                    "authored_fields": excerpts, "review_only": True,
                },
            }
            if reason == "no_matching_background" and _text(row.get("scene"), 48):
                evidence["scene"] = _text(row["scene"], 48)
            rows.append(evidence)
        if cid and rows:
            gaps.append({
                "content_id": cid,
                "shot_count": source.get("shot_count") if type(source.get("shot_count")) is int else None,
                "missing_shot_count": len(rows), "missing_shots": rows,
                "publication_approval": False, "semantic_quality": "not_verified",
                "repair_status": "manual_scene_and_art_review_required",
            })
    if not gaps:
        return None
    gaps.sort(key=lambda gap: (-gap["missing_shot_count"], gap["content_id"]))
    return {
        "schema_version": 1, "lane": lane,
        "report_type": "fiction_scene_artwork_repair_queue",
        "story_count": len(gaps),
        "missing_shot_count": sum(g["missing_shot_count"] for g in gaps),
        "scene_unresolved_count": sum(s["reason"] == "scene_unresolved"
                                      for g in gaps for s in g["missing_shots"]),
        "no_matching_background_count": sum(s["reason"] == "no_matching_background"
                                              for g in gaps for s in g["missing_shots"]),
        "publication_approval": False, "semantic_quality": "not_verified",
        "automatic_scene_substitution": False, "automatic_image_generation": False,
        "items": gaps,
    }


def save_repair_queue(selection, *, lane, directory="runtime-health/artwork-gap-reports"):
    """Atomically create a lane-specific report only if real gaps were observed."""
    report = build_repair_queue(selection, lane=lane)
    if report is None:
        return None
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    output, temporary = root / f"lane-{lane}.json", root / f".lane-{lane}.json.tmp"
    try:
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {"path": str(output), "story_count": report["story_count"],
            "missing_shot_count": report["missing_shot_count"],
            "publication_approval": False}
