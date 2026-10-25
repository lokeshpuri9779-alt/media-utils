"""Opt-in backdrop composition for ASTRA Studio's existing Pillow renderer.

Preserves full-frame size and leaves captions/foreground actor compositing intact.
Uses original SVG library's scene/palette identities, drawn natively by Pillow
so no new runtime rasterization dependency is required.
"""
from __future__ import annotations
import hashlib
import re
import os
import math
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw
from astra_v2.visual_artifact_library import SCENES, PALETTES

SCENE_TERMS = {
    "observatory": ("observatory", "telescope", "planetarium", "stargazing"),
    "forest": ("forest", "woods", "woodland", "jungle", "rainforest"),
    "harbor": ("harbor", "dock", "port", "marina", "seaport", "pier"),
    "library": ("library", "bookshelf", "bookstore", "reading room"),
    "railway": ("railway", "train", "station", "railroad", "locomotive"),
    "village": ("village", "hamlet", "countryside"),
    "mountain": ("mountain", "summit", "mountains", "cliff", "peak"),
    "desert": ("desert", "dune", "sand dunes", "oasis"),
    "underwater": ("underwater", "ocean", "coral", "seabed", "reef", "deep sea"),
    "space": ("space", "orbital", "orbit", "planet", "galaxy", "cosmos", "astronaut"),
    "laboratory": ("laboratory", "lab", "research lab", "science lab"),
    "garden": ("garden", "greenhouse", "botanical garden", "flower garden"),
    "lighthouse": ("lighthouse", "beacon tower"),
    "cave": ("cave", "cavern", "grotto", "underground cavern"),
    "city": ("city", "street", "downtown", "skyscraper", "metropolis"),
    "workshop": ("workshop", "mechanic", "garage", "repair shop"),
    "castle": ("castle", "fortress", "citadel"),
    "snowfield": ("snowfield", "snow", "ice", "blizzard", "glacier", "tundra"),
    "island": ("island", "archipelago", "tropical island"),
    "museum": ("museum", "exhibition hall", "art gallery"),
}

def analyze_story_scene(shot):
    """One deterministic, side-effect-free scene decision for the full pipeline.

    Explicit storyboard locations outrank narration. Unknown environments stay
    unresolved rather than silently selecting unrelated artwork.
    """
    for key in ("story_environment", "scene_environment", "scene_location", "setting", "visual_prompt", "visual_intent", "visual", "speech", "headline", "story_title"):
        value = shot.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        text = value.lower()
        for scene in SCENES:
            for term in SCENE_TERMS[scene]:
                if re.search(r"\b" + re.escape(term) + r"\b", text):
                    return {"scene": scene, "source_field": key,
                            "matched_term": term, "needs_background": False}
    return {"scene": None, "source_field": None,
            "matched_term": None, "needs_background": True}


def choose_scene(shot):
    return analyze_story_scene(shot)["scene"]

@lru_cache(maxsize=64)
def _cached_pack_background(root_path, scene, identity, video_format, size, shot_number=None):
    """Return both decoded art and its verified provenance, cached per shot."""
    from astra_v2.quality_asset_selector import select_assets
    from PIL import ImageOps
    root = Path(root_path)
    candidates = select_assets(root, kind="background", tags=(scene,),
                               video_format=video_format, limit=50)
    if not candidates:
        return None
    seed = int.from_bytes(hashlib.sha256(str(identity).encode()).digest()[:4], "big")
    # Reuse an environment's style but vary the actual artwork viewpoint by
    # authored shot. A story-stable identity alone previously reused ONE PNG
    # for every beat, even when 50 verified alternatives were available.
    count = len(candidates)
    stride = max(1, count // 4)
    while math.gcd(stride, count) != 1:
        stride += 1
    offset = (int(shot_number) - 1) if shot_number is not None else 0
    chosen = candidates[(seed + offset * stride) % count]
    with Image.open(root / chosen["path"]) as source:
        backdrop = ImageOps.fit(source.convert("RGB"), size,
                                method=Image.Resampling.LANCZOS)
    return backdrop, chosen


def apply_pack_background(image, shot, identity, *, root=None, video_format="shorts",
                          shot_number=None):
    """Apply a validated background and audit what the compositor really used."""
    from astra_v2.asset_usage_audit import observe
    if video_format not in ("shorts", "long"):
        raise ValueError("invalid video format")
    if shot_number is not None and (not isinstance(shot_number, int) or shot_number < 1):
        raise ValueError("shot_number must be a positive integer")
    analysis = analyze_story_scene(shot)
    scene = analysis["scene"]
    if analysis["needs_background"]:
        observe(shot_number, analysis, "scene_unresolved", identity)
        return image
    configured = root or os.getenv("ASTRA_ASSET_PACK_ROOT")
    if not configured:
        observe(shot_number, analysis, "root_unconfigured", identity)
        return image
    root_path = str(Path(configured).resolve())
    if not (Path(root_path) / "art" / "manifest.json").is_file():
        observe(shot_number, analysis, "manifest_missing", identity)
        return image
    # Avoid reusing decoded artwork across calls unless the restored pack is
    # explicitly immutable. Otherwise selection must revalidate changed files.
    cache_allowed = (os.getenv("ASTRA_ASSET_PACK_ENABLED") == "1" and
                     os.getenv("ASTRA_ASSET_PACK_IMMUTABLE") == "1")
    loader = _cached_pack_background if cache_allowed else _cached_pack_background.__wrapped__
    selection = loader(root_path, scene, str(identity), video_format, image.size, shot_number)
    if selection is None:
        observe(shot_number, analysis, "no_matching_background", identity)
        return image
    backdrop, chosen = selection
    rendered = Image.blend(image.convert("RGB"), backdrop, 0.65)
    observe(shot_number, analysis, "selected", identity,
            asset=chosen, before=image, after=rendered)
    return rendered

def apply_backdrop(image, shot, identity):
    if image.mode != "RGB" or image.size != (1080,1920):
        raise ValueError("ASTRA artifact backdrop requires RGB 1080x1920")
    scene=choose_scene(shot)
    if scene is None:
        return image
    seed=int.from_bytes(hashlib.sha256((str(identity) + "|" + scene).encode()).digest()[:4],"big")
    palette=PALETTES[seed%len(PALETTES)]
    bg,accent,light,star=palette
    # Upper half environmental silhouette; actors and captions remain rendered
    # later by the existing Studio pipeline.
    overlay=Image.new("RGBA",image.size,(0,0,0,0))
    d=ImageDraw.Draw(overlay)
    if scene in {"city","village","castle","library","museum","workshop","laboratory"}:
        for i in range(7):
            x=i*165-25
            h=200+(seed//(i+1))%230
            d.rectangle((x,940-h,x+130,940),fill=accent+"99")
            for yy in range(940-h+35,925,65):
                d.rectangle((x+30,yy,x+55,yy+22),fill=light+"88")
    elif scene in {"forest","garden","island","snowfield","mountain","desert"}:
        for i in range(7):
            x=i*190-80
            peak=380+(seed//(i+1))%260
            d.polygon(((x,950),(x+100,950-peak),(x+220,950)),fill=accent+"99")
    elif scene in {"observatory","lighthouse","railway","harbor","space"}:
        d.ellipse((240,380,840,980),outline=light+"99",width=22)
        d.polygon(((280,940),(360,530),(720,530),(800,940)),fill=accent+"88")
    else:
        for i in range(11):
            x=(seed+i*193)%1080
            y=300+(seed//(i+1))%600
            r=15+(i*11)%70
            d.ellipse((x-r,y-r,x+r,y+r),outline=light+"99",width=7)
    # Distinct scene identity marker prevents identical silhouette variants.
    scene_code = SCENES.index(scene) + 1
    for bit in range(5):
        if scene_code & (1 << bit):
            x = 80 + bit * 32
            d.rounded_rectangle((x, 1000, x + 22, 1022), radius=5, fill=light + "bb")
    # Confine environmental art to the upper scene region. Existing subject,
    # headline, and caption drawing retain ownership of their own layers.
    overlay.paste((0, 0, 0, 0), (0, 1100, 1080, 1920))
    image.paste(Image.alpha_composite(image.convert("RGBA"),overlay).convert("RGB"))
    return image
