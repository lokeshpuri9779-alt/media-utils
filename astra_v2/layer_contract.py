"""Foreground scene compositor contract for RAYVAN / ASTRA Studio.

A shot gets exactly ONE focal-animation source. Decorative animated widgets,
director cards and subject animation must never independently occupy the
same middle third of a frame. The contract is pure Python so it can be
validated before audio synthesis and FFmpeg rendering.
"""
from __future__ import annotations

ILLUSTRATED_VISUALS = frozenset({
    "planet", "orbit", "compare", "tidal_lock", "iss_orbit",
    "pitch", "screen", "keys", "ship", "signal", "door",
    "robot", "forest",
})
FALLBACK_ASSETS = frozenset({"", "kinetic-type", "none"})

# Deliberate non-intersecting vertical zones in the 1080 x 1920 master.
# Foreground visual animations are confined to the subject stage and cannot
# move into the title, caption or platform-control regions.
SAFE_REGIONS = {
    "headline": (64, 105, 1016, 392),
    "subject": (55, 485, 1025, 1370),
    "caption": (90, 1430, 990, 1680),
}
FRAME_SIZE = (1080, 1920)


def overlap_area(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    return max(0, x1 - x0) * max(0, y1 - y0)


def scene_layers(shot):
    """Return the ONLY permitted foreground composition for a shot.

    Preserve the handcrafted story subject, rather than stacking unrelated
    editor/director animations on top of it. Cached stills and synthetic
    assets are alternate subject sources, never another simultaneous layer.
    """
    visual = str(shot.get("visual") or "").lower().strip()
    resolved = shot.get("resolved_asset") or {}
    has_media = (
        resolved.get("status") == "ready" and
        bool(resolved.get("cache_image"))
    )
    if visual in ILLUSTRATED_VISUALS:
        foreground = "illustration"
    elif visual == "media":
        foreground = "cached_media" if has_media else "missing_media"
    elif has_media:
        foreground = "cached_media"
    elif str(shot.get("director_asset") or "").lower().strip() not in FALLBACK_ASSETS:
        foreground = "director_asset"
    else:
        foreground = "illustration"

    # Rendering stage: ONE foreground; titles and captions are drawn later
    # in their reserved zones. Transitions are limited to the scene edges.
    return {
        "foreground": foreground,
        "draw_visual": foreground == "illustration",
        "draw_cached_media": foreground == "cached_media",
        "draw_director_asset": foreground == "director_asset",
        "visual_style_overlay": False,
        "composition_overlay": False,
        "attention_overlay": False,
        "director_motion_overlay": False,
    }


def verify_scene_layout(scenes):
    """Hard fail when two foreground sources, missing media or unsafe zones exist."""
    failures = []
    for name, bounds in SAFE_REGIONS.items():
        x0, y0, x1, y1 = bounds
        if not (0 <= x0 < x1 <= FRAME_SIZE[0] and 0 <= y0 < y1 <= FRAME_SIZE[1]):
            failures.append("invalid_" + name + "_bounds")
    for a, b in (("headline", "subject"), ("subject", "caption"), ("headline", "caption")):
        if overlap_area(SAFE_REGIONS[a], SAFE_REGIONS[b]):
            failures.append("unsafe_region_overlap:" + a + ":" + b)
    rows = []
    for index, scene in enumerate(scenes):
        layers = scene_layers(scene)
        count = sum(1 for name in ("draw_visual", "draw_cached_media", "draw_director_asset") if layers[name])
        if count != 1 or layers["foreground"] == "missing_media":
            failures.append("scene_" + str(index + 1) + ":foreground_missing_or_competing")
        if any(layers[name] for name in ("visual_style_overlay", "composition_overlay",
                                         "attention_overlay", "director_motion_overlay")):
            failures.append("scene_" + str(index + 1) + ":competing_motion_overlay")
        rows.append({
            "scene": index + 1,
            "visual": str(scene.get("visual") or ""),
            "foreground": layers["foreground"],
            "competing_foreground_count": count,
        })
    return {"pass": not failures, "failures": failures, "scenes": rows,
            "safe_regions": SAFE_REGIONS}
