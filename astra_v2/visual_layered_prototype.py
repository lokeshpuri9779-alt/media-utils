"""Experimental layered scene painter. Not connected to publishing.

Produces an RGB 1080x1920 background with a reserved caption/actor region.
This is a prototype for richer visual comparison, not a production renderer.
"""
from __future__ import annotations

import hashlib
from PIL import Image, ImageDraw, ImageFilter
from astra_v2.visual_artifact_library import SCENES

THEMES = {
    "forest": ((23, 54, 72), (115, 174, 143), (33, 83, 61)),
    "snowfield": ((43, 76, 117), (207, 227, 239), (113, 162, 194)),
    "desert": ((77, 53, 76), (244, 185, 117), (185, 111, 83)),
    "underwater": ((5, 42, 78), (24, 143, 158), (12, 92, 115)),
    "space": ((10, 16, 44), (54, 60, 111), (27, 35, 75)),
    "city": ((27, 42, 72), (153, 113, 139), (64, 65, 100)),
    "garden": ((32, 72, 79), (152, 193, 135), (47, 112, 86)),
    "mountain": ((29, 62, 99), (171, 193, 201), (74, 107, 139)),
}

def _blend(a, b, t):
    return tuple(round(x * (1-t) + y*t) for x,y in zip(a,b))

def render_layered_scene(scene: str, identity: str) -> Image.Image:
    if scene not in SCENES:
        raise ValueError("Unsupported environment")
    seed = int.from_bytes(hashlib.sha256((scene+"|"+identity).encode()).digest()[:4], "big")
    top, horizon, ground = THEMES.get(scene, ((25, 45, 70), (124, 135, 153), (61, 84, 105)))
    # Paint a genuine vertical atmospheric gradient, unlike flat silhouette fills.
    gradient = Image.new("RGB", (1, 1920))
    for y in range(1920):
        t = min(y / 1050, 1)
        gradient.putpixel((0,y), _blend(top, horizon if y < 1050 else ground, t))
    image = gradient.resize((1080,1920))
    atmosphere = Image.new("RGBA", image.size)
    d = ImageDraw.Draw(atmosphere)
    # Three ordered depth planes: distant low-contrast, middle, near.
    for layer, (base_y, opacity) in enumerate(((720,45),(850,85),(990,135))):
        points = [(0,1100)]
        for i in range(9):
            x = i*150
            offset = (seed // (i+layer+1) + i*71 + layer*109) % 115
            points.append((x,base_y + offset))
        points.extend(((1080,1100),(0,1100)))
        d.polygon(points, fill=(*ground, opacity))
    # Environment-defining foreground silhouettes.
    if scene in ("forest", "garden"):
        for i in range(5):
            x=110+i*220+(seed//(i+1))%50
            d.rectangle((x,590,x+28,1060),fill=(*ground,210))
            d.ellipse((x-75,430,x+105,720),fill=(*ground,170))
    elif scene in ("city","village","castle","museum","library"):
        for i in range(5):
            x=45+i*230
            h=230+(seed//(i+1))%150
            d.rounded_rectangle((x,1000-h,x+180,1000),radius=8,fill=(*ground,175))
            for j in range(3):
                d.rectangle((x+35,1000-h+40+j*65,x+75,1000-h+80+j*65),fill=(245,216,165,125))
    elif scene in ("mountain","snowfield","desert"):
        d.polygon(((90,1000),(420,430),(770,1000)),fill=(*ground,210))
        d.polygon(((320,600),(420,430),(535,610)),fill=(*horizon,210))
    elif scene in ("underwater","harbor","island","lighthouse"):
        for i in range(5):
            y=700+i*65
            d.arc((-100,y,1180,y+180),180,350,fill=(*horizon,90),width=12)
    elif scene in ("space","observatory"):
        d.ellipse((350,380,750,780),fill=(*ground,180),outline=(*horizon,220),width=12)
        d.ellipse((190,490,910,670),outline=(*horizon,200),width=18)
    # Slight atmospheric blur softens distant layers; leave caption region untouched.
    atmosphere = atmosphere.filter(ImageFilter.GaussianBlur(2))
    image.paste(Image.alpha_composite(image.convert("RGBA"),atmosphere).convert("RGB"),(0,0))
    return image
