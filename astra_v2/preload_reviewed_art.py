"""Opt-in reviewed-art manifest attachment for the existing production renderer.

No story approval, new renderer, or publisher bypass is performed here.
"""
import os
from pathlib import Path

from astra_v2.story_art_direction import bind_reviewed_scenes


def attach_reviewed_art(story, *, environ=None):
    env = os.environ if environ is None else environ
    path = env.get("ASTRA_PRELOAD_REVIEWED_ART_MANIFEST", "").strip()
    if not path:
        return story
    if not isinstance(story, dict) or not story.get("content_id"):
        raise ValueError("reviewed_art_story_identity_required")
    manifest = Path(path).resolve(strict=True)
    beats = story.get("story_beats")
    if not isinstance(beats, list) or not beats:
        raise ValueError("reviewed_art_story_beats_required")
    # Validate full-story scene coverage and SHA-checked approved asset bytes
    # before spending time on voice synthesis or video rendering.
    bind_reviewed_scenes(beats, story["content_id"], manifest)
    return {**story, "reviewed_art_manifest": str(manifest)}
