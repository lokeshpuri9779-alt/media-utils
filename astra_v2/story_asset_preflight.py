"""Offline story-to-art preflight. Never uploads or publishes videos."""
from pathlib import Path
from astra_v2.expandable_story_system import candidate_briefs, load_families
from astra_v2.scene_aware_story_drafts import draft_story
from astra_v2.quality_asset_selector import select_assets


def inspect_story_assets(story, asset_root, *, video_format="shorts"):
    if video_format not in ("shorts", "long"):
        raise ValueError("invalid video format")
    rows = []
    for index, beat in enumerate(story.get("story_beats", []), 1):
        setting = beat.get("story_environment") or story.get("story_environment")
        matches = select_assets(Path(asset_root), kind="background",
                                tags=(setting,), video_format=video_format, limit=3) if setting else []
        rows.append({"shot": index, "setting": setting,
                     "candidate_asset_ids": [item["id"] for item in matches],
                     "has_verified_match": bool(matches)})
    return {"content_id": story.get("content_id"), "video_format": video_format,
            "shot_count": len(rows), "matched_shots": sum(row["has_verified_match"] for row in rows),
            "all_shots_matched": bool(rows) and all(row["has_verified_match"] for row in rows),
            "shots": rows, "approved_for_publication": False}


def prepare_story_candidates(seed, count, *, settings, protagonists, goals, conflicts, twists):
    """Connect concept planning to scene-aware drafts without publication side effects."""
    concepts = candidate_briefs(seed, count, families=load_families(),
                                settings=settings, protagonists=protagonists,
                                goals=goals, conflicts=conflicts, twists=twists)
    for concept in concepts:
        yield draft_story(concept)
