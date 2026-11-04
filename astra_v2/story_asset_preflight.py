"""Offline story-to-art inspection; review-only, never uploads or publishes videos.

Use the production compositor's scene taxonomy and verified asset selector,
not raw free-text tags which can disagree with actual Studio backgrounds.
This inspector does not run Studio planning, prove compositing, or approve art.
"""
from pathlib import Path
from astra_v2.expandable_story_system import candidate_briefs, load_families
from astra_v2.scene_aware_story_drafts import draft_story
from astra_v2.quality_asset_selector import select_assets
from astra_v2.visual_artifact_backdrop import analyze_story_scene


def inspect_story_assets(story, asset_root, *, video_format="shorts"):
    """Check available candidate art using the production scene resolver.

    All positive matches remain *possible*, never semantically verified.
    Missing or malformed pack and unknown scenes fail closed for planning.
    """
    if video_format not in ("shorts", "long"):
        raise ValueError("invalid video format")
    if not isinstance(story, dict):
        raise ValueError("story must be a dictionary")
    beats = story.get("story_beats") or []
    if not isinstance(beats, (list, tuple)):
        raise ValueError("story_beats must be a list")
    root = Path(asset_root)
    pack_present = (root / "art" / "manifest.json").is_file()
    found_by_scene = {}
    rows = []
    for index, beat in enumerate(beats, 1):
        if not isinstance(beat, dict):
            raise ValueError("each story beat must be a dictionary")
        # Same precedence as the compositor: an explicit per-shot environment
        # outranks authored visuals and speech. Use story-level location only
        # if the beat does not declare one. Do not mutate the submitted story.
        shot = dict(beat)
        if not shot.get("story_environment") and story.get("story_environment"):
            shot["story_environment"] = story["story_environment"]
        analysis = analyze_story_scene(shot)
        scene = analysis["scene"]
        if not pack_present:
            matches, reason = [], "verified_asset_pack_missing"
        elif scene is None:
            matches, reason = [], "scene_unresolved"
        else:
            if scene not in found_by_scene:
                found_by_scene[scene] = select_assets(
                    root, kind="background", tags=(scene,),
                    video_format=video_format, limit=3)
            matches = found_by_scene[scene]
            reason = None if matches else "no_matching_background"
        rows.append({
            "shot": index,
            "setting": shot.get("story_environment"),
            "scene": scene,
            "scene_source": analysis["source_field"],
            "candidate_asset_ids": [asset["id"] for asset in matches],
            "has_verified_match": bool(matches),
            "reason": reason,
        })
    return {
        "content_id": story.get("content_id"),
        "video_format": video_format,
        "shot_count": len(rows),
        "matched_shots": sum(row["has_verified_match"] for row in rows),
        "all_shots_matched": bool(rows) and all(row["has_verified_match"] for row in rows),
        "shots": rows,
        "semantic_quality": "not_verified",
        "approved_for_publication": False,
    }


def prepare_story_candidates(seed, count, *, settings, protagonists, goals, conflicts, twists):
    """Connect concept planning to scene-aware drafts without publication side effects."""
    concepts = candidate_briefs(seed, count, families=load_families(),
                                settings=settings, protagonists=protagonists,
                                goals=goals, conflicts=conflicts, twists=twists)
    for concept in concepts:
        yield draft_story(concept)
