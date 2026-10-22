"""Fail-closed preflight for story-specific AI visuals.

Opt-in strict mode prevents generic procedural fallback when the publisher
requires independently reviewed scene illustrations.
"""
from __future__ import annotations
import os


def require_reviewed_story_art(story, *, environ=None):
    env = os.environ if environ is None else environ
    if env.get("ASTRA_REQUIRE_REVIEWED_AI_VISUALS", "0") != "1":
        return False
    if not isinstance(story, dict):
        raise ValueError("story_required_for_strict_visuals")
    if story.get("genre") != "fiction":
        return False
    manifest = story.get("reviewed_art_manifest")
    if not manifest:
        raise ValueError("reviewed_ai_visual_manifest_required")
    if not story.get("content_id"):
        raise ValueError("story_content_identity_required")
    # The renderer's bind_reviewed_scenes independently verifies exact scene
    # identity, coverage and approved asset metadata. No bypass is allowed.
    return True
