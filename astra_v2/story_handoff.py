"""Lossless, allowlisted renderer story context for ASTRA preload handoffs.

Never infer or synthesize missing narration, visuals, approval or artwork.
This module does not approve content; the original and reconstructed
candidate must independently pass the existing publication quality gate.
"""
from __future__ import annotations

from copy import deepcopy

# Only fields necessary to reconstruct the same approved Studio storyboard
# are eligible for propagation through a bounded candidate.json artifact.
STORY_CONTEXT_FIELDS = (
    "kind", "production_ready", "validation_candidate",
    "hook", "question", "answer", "keywords", "source",
    "story_beats", "story_cast", "story_environment", "story_prop",
    "story_prop_id", "story_prop_owner", "story_human_actor",
    "story_location", "series_id", "episode", "experimental_ensemble",
    "artwork_asset_id", "artwork_manifest_path", "scene_id",
    "story_content_id", "illustrated_assets", "auto_illustrated_art",
)


def approved_story_context(story: dict) -> dict:
    """Copy existing reviewed scene metadata without changing its meaning.

    Deliberately no fallback to an invented generic graphic. A missing
    speech or visual remains missing so existing renderer QA rejects it.
    """
    if not isinstance(story, dict):
        raise TypeError("story must be an object")
    return {key: deepcopy(story[key]) for key in STORY_CONTEXT_FIELDS
            if key in story}
