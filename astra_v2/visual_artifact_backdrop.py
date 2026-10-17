"""Opt-in backdrop composition for ASTRA Studio's existing Pillow renderer.

Preserves full-frame size and leaves captions/foreground actor compositing intact.
Uses original SVG library's scene/palette identities, drawn natively by Pillow
so no new runtime rasterization dependency is required.
"""
from __future__ import annotations
import hashlib
import re
from PIL import Image, ImageDraw
from astra_v2.visual_artifact_library import SCENES, PALETTES

SCENE_TERMS = {
    "observatory": ("observatory", "telescope"),
    "forest": ("forest", "woods"),
    "harbor": ("harbor", "dock", "port"),
    "library": ("library", "bookshelf"),
    "railway": ("railway", "train", "station"),
    "village": ("village",),
    "mountain": ("mountain", "summit"),
    "desert": ("desert", "dune"),
    "underwater": ("underwater", "ocean", "coral"),
    "space": ("space", "orbital", "planet"),
    "laboratory": ("laboratory", "lab"),
    "garden": ("garden", "greenhouse"),
    "lighthouse": ("lighthouse",),
    "cave": ("cave", "cavern"),
    "city": ("city", "street"),
    "workshop": ("workshop", "mechanic"),
    "castle": ("castle",),
    "snowfield": ("snow", "ice"),
    "island": ("island",),
    "museum": ("museum",),
}

def choose_scene(shot):
    # Authored setting wins over incidental location words in narration.
    for key in ("story_environment", "visual_prompt", "speech", "headline"):
        text = str(shot.get(key) or "").lower()
        for scene in SCENES:
            if any(re.search(r"\b"+re.escape(term)+r"\b",text) for term in SCENE_TERMS[scene]):
                return scene
    return None

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
