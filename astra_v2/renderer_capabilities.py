"""Conservative capability contract for ASTRA's deterministic Pillow renderer.

Renderable means the renderer can put a symbol on screen. Story-faithful means
there is a dedicated illustration for the object's identity and condition.
This registry intentionally does not claim pixel-level semantic verification.
"""
from __future__ import annotations

# These names must correspond to dedicated branches in pillow_duo_scene._prop.
# Anything handled by its generic draw_icon fallback is renderable, not faithful.
STORY_FAITHFUL_PROPS = frozenset({
    "box", "book", "ball", "flower", "lantern",
})

def renderer_prop_capabilities() -> dict:
    """Return renderer prop names split by fidelity, using the live prop table."""
    from astra_v2.pillow_duo_scene import PROPS
    renderable = frozenset(PROPS)
    return {
        "renderable": renderable,
        "story_faithful": renderable & STORY_FAITHFUL_PROPS,
        "generic_fallback": renderable - STORY_FAITHFUL_PROPS,
    }

def prop_is_story_faithful(name: str) -> bool:
    """True only for a prop with a dedicated, story-specific illustration."""
    return str(name or "").strip().casefold() in renderer_prop_capabilities()["story_faithful"]

def renderer_subject_capabilities() -> dict:
    """Expose the intersection of generation labels and actual puppet actors."""
    from astra_v2.openai_creative import VISUALS
    from astra_v2.pillow_duo_scene import ACTORS
    return {
        "generation_labels": frozenset(VISUALS),
        "renderer_actors": frozenset(ACTORS),
        "story_faithful": frozenset(VISUALS) & frozenset(ACTORS),
    }

def renderer_environment_capabilities() -> dict:
    """Only environments with a directed Pillow stage count as renderer-supported."""
    from astra_v2.pillow_scene_direction import SCENE_CUES
    from astra_v2.visual_artifact_library import SCENES
    stages = frozenset(name for name, _ in SCENE_CUES)
    artifacts = frozenset(SCENES)
    return {
        "story_faithful": stages & artifacts,
        "artifact_only": artifacts - stages,
        "stage_only": stages - artifacts,
    }
