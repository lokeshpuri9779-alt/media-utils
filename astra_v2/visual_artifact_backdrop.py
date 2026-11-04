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
    # Bare "station" also means the International Space Station; require rail context.
    "railway": ("railway", "train", "train station", "railway station",
                "rail station", "metro station", "subway station", "railroad", "locomotive"),
    "village": ("village", "hamlet", "countryside"),
    "mountain": ("mountain", "summit", "mountains", "cliff", "peak"),
    "desert": ("desert", "dune", "sand dunes", "oasis"),
    "underwater": ("underwater", "ocean", "coral", "seabed", "reef", "deep sea"),
    "space": ("space", "iss", "orbital", "orbit", "planet", "galaxy", "cosmos", "astronaut"),
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
    # Keep a consistent palette per environment; story identity may vary details,
    # but must not make a snowfield look like a desert or vice versa.
    palette=PALETTES[SCENES.index(scene)%len(PALETTES)]
    bg,accent,light,star=palette
    # A quiet atmospheric background avoids the former shared skyline/triangle
    # shapes colliding with the recognizable, scene-specific focal objects.
    overlay=Image.new("RGBA",image.size,(0,0,0,0))
    d=ImageDraw.Draw(overlay)
    if scene in {"underwater","harbor","island"}:
        d.arc((-120,710,1200,1100),180,350,fill=light+"55",width=13)
    elif scene in {"space","observatory","snowfield"}:
        for i in range(8):
            x=90+(seed//(i+1)+i*127)%900
            y=220+(seed//(i+3)+i*71)%330
            d.ellipse((x,y,x+8,y+8),fill=light+"99")
    elif scene in {"forest","garden","mountain","desert"}:
        d.arc((-200,730,1280,1150),180,355,fill=accent+"88",width=18)
    else:
        d.line((90,950,990,950),fill=accent+"99",width=16)
    # Three atmospheric planes give depth without external assets or
    # covering the actor/caption-owned lower part of the frame.
    # Shapes stay behind the recognizable scene motifs drawn below.
    if scene in {"forest","garden","mountain","snowfield","desert","island","cave"}:
        d.polygon(((0,730),(240,610),(450,720),(730,570),(1080,700),(1080,1100),(0,1100)),
                  fill=accent+"30")
        d.polygon(((0,850),(220,760),(510,850),(830,720),(1080,840),(1080,1100),(0,1100)),
                  fill=light+"20")
    elif scene in {"underwater","harbor","lighthouse","space","observatory"}:
        d.ellipse((-240,680,1320,1320),outline=accent+"44",width=90)
        d.ellipse((-120,760,1200,1220),outline=light+"22",width=36)
    else:
        for i in range(4):
            x=55+i*285
            height=145+(seed//(i+1))%125
            d.rectangle((x,950-height,x+190,950),fill=accent+"30")
        d.line((0,960,1080,960),fill=light+"33",width=12)
    # Readable scene-specific motifs replace artificial identity barcodes.
    # The backdrop is still opt-in and remains behind foreground actors.
    if scene == "observatory":
        d.ellipse((390,370,690,670), fill=accent+"dd", outline=light, width=12)
        d.rectangle((510,650,570,950), fill=light+"bb")
        d.line((550,500,790,310), fill=light, width=32)
    elif scene == "forest":
        for x in (130,450,810):
            d.rectangle((x,590,x+40,950), fill=accent)
            d.ellipse((x-95,390,x+135,690), fill=light+"77")
    elif scene == "harbor":
        d.polygon(((280,860),(550,860),(480,920),(340,920)), fill=light+"bb")
        d.line((405,850,405,470),fill=light,width=12)
        d.polygon(((415,490),(415,810),(630,810)),fill=accent)
    elif scene == "library":
        for x in (130,430,730):
            d.rectangle((x,420,x+220,900),outline=light,width=18)
            for k in range(5):
                d.rectangle((x+20+k*38,490,x+45+k*38,750),fill=accent+"dd")
    elif scene == "railway":
        d.polygon(((450,950),(490,560),(590,560),(630,950)),fill=light+"99")
        d.rectangle((320,410,760,710),fill=accent,outline=light,width=14)
        d.rectangle((380,465,700,580),fill=light+"aa")
    elif scene == "village":
        for x in (110,440,760):
            d.rectangle((x,680,x+200,940),fill=accent)
            d.polygon(((x-20,680),(x+100,530),(x+220,680)),fill=light+"aa")
    elif scene == "mountain":
        d.polygon(((130,930),(460,320),(800,930)),fill=accent)
        d.polygon(((360,500),(460,320),(570,520),(460,480)),fill=light)
    elif scene == "desert":
        d.arc((50,620,1030,1130),180,350,fill=light,width=22)
        d.line((700,870,700,540),fill=light,width=26)
        d.arc((630,600,710,760),0,180,fill=light,width=23)
    elif scene == "underwater":
        d.ellipse((300,540,710,780),fill=accent,outline=light,width=10)
        d.polygon(((300,650),(190,540),(190,760)),fill=light+"aa")
        for x,y in ((180,390),(850,480),(780,300)):
            d.ellipse((x,y,x+65,y+65),outline=light,width=8)
    elif scene == "space":
        d.ellipse((340,410,750,820),fill=accent,outline=light,width=14)
        d.ellipse((180,530,900,710),outline=light,width=18)
    elif scene == "laboratory":
        d.polygon(((440,430),(580,430),(580,620),(710,900),(310,900),(440,620)),fill=accent,outline=light)
        d.line((370,770,650,770),fill=light,width=18)
    elif scene == "garden":
        for x in (230,530,830):
            d.line((x,950,x,590),fill=light,width=16)
            d.ellipse((x-75,490,x+75,640),fill=accent,outline=light,width=12)
    elif scene == "lighthouse":
        d.polygon(((420,930),(460,400),(610,400),(660,930)),fill=accent,outline=light)
        d.rectangle((440,370,625,455),fill=light+"dd")
        d.polygon(((420,370),(535,290),(645,370)),fill=accent)
    elif scene == "cave":
        d.polygon(((0,200),(240,420),(390,210),(560,470),(800,190),(1080,390),(1080,0),(0,0)),fill=accent)
        d.ellipse((380,660,700,1050),fill=light+"77")
    elif scene == "city":
        for x in (100,370,660):
            d.rectangle((x,380,x+230,940),fill=accent,outline=light,width=8)
            for y in (480,600,720):
                d.rectangle((x+50,y,x+100,y+55),fill=light+"aa")
    elif scene == "workshop":
        d.ellipse((330,470,750,890),outline=light,width=45)
        d.ellipse((455,595,625,765),fill=accent)
        d.line((230,450,420,640),fill=light,width=30)
    elif scene == "castle":
        d.rectangle((230,540,850,940),fill=accent)
        for x in (220,690):
            d.rectangle((x,370,x+180,940),fill=accent,outline=light,width=10)
        d.arc((455,720,625,1050),180,360,fill=light,width=22)
    elif scene == "snowfield":
        d.polygon(((70,940),(420,400),(710,940)),fill=light+"aa")
        d.polygon(((300,580),(420,400),(540,590)),fill=light)
        for x,y in ((190,380),(740,480),(850,310)):
            d.line((x-20,y,x+20,y),fill=light,width=7)
            d.line((x,y-20,x,y+20),fill=light,width=7)
    elif scene == "island":
        d.arc((90,750,990,1130),180,360,fill=light,width=26)
        d.line((530,870,560,470),fill=accent,width=28)
        for end in ((330,420),(760,430),(520,280)):
            d.arc((min(530,end[0]),min(450,end[1]),max(570,end[0]+50),570),190,350,fill=light,width=20)
    elif scene == "museum":
        d.polygon(((180,460),(540,270),(900,460)),fill=light+"aa")
        for x in (260,430,600,770):
            d.rectangle((x,480,x+65,900),fill=accent,outline=light,width=8)
        d.rectangle((180,900,900,950),fill=light+"aa")
    # Confine environmental art to the upper scene region. Existing subject,
    # headline, and caption drawing retain ownership of their own layers.
    overlay.paste((0, 0, 0, 0), (0, 1100, 1080, 1920))
    image.paste(Image.alpha_composite(image.convert("RGBA"),overlay).convert("RGB"))
    return image
