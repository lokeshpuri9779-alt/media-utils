"""Generate reproducible vertical background artwork for manual QA before approval.

Run: python -m astra.background_factory --output /tmp/astra-art
Does not publish, spend API credits, or change the live asset manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

SCENES = {
    "dawn-valley": ((19, 33, 70), (241, 151, 107), "mountains"),
    "twilight-valley": ((11, 18, 55), (103, 83, 158), "mountains"),
    "moonlit-valley": ((8, 21, 43), (42, 80, 119), "mountains"),
    "emerald-forest": ((9, 42, 52), (68, 132, 101), "forest"),
    "misty-forest": ((35, 67, 80), (150, 173, 149), "forest"),
    "golden-forest": ((57, 48, 53), (212, 147, 87), "forest"),
    "ocean-sunrise": ((24, 40, 86), (237, 157, 118), "ocean"),
    "ocean-night": ((6, 18, 47), (35, 82, 127), "ocean"),
    "ocean-storm": ((17, 32, 51), (86, 111, 133), "ocean"),
    "desert-dusk": ((29, 24, 64), (213, 112, 104), "desert"),
    "desert-day": ((73, 117, 165), (247, 193, 124), "desert"),
    "desert-night": ((9, 19, 47), (87, 65, 99), "desert"),
}


def render(name, size=(540, 960)):
    if name not in SCENES:
        raise ValueError("unknown_background")
    width, height = size
    if width < 540 or height < 960:
        raise ValueError("background_below_renderer_minimum")
    top, bottom, terrain = SCENES[name]
    rng = random.Random(int(hashlib.sha256(name.encode()).hexdigest()[:16], 16))
    im = Image.new("RGB", size)
    draw = ImageDraw.Draw(im)
    for y in range(height):
        t = y / max(height - 1, 1)
        color = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        draw.line((0, y, width, y), fill=color)
    if "night" in name or "moonlit" in name or "twilight" in name:
        for _ in range(95):
            x, y = rng.randrange(width), rng.randrange(height // 2)
            radius = rng.choice((1, 1, 2))
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(195, 214, 224))
    else:
        x, y, rad = int(width * .73), int(height * .29), 48
        draw.ellipse((x-rad, y-rad, x+rad, y+rad), fill=(255, 224, 177))
    horizon = int(height * .64)
    if terrain == "mountains":
        for layer in range(3):
            base = horizon + layer * 95
            points = [(0, height), (0, base)]
            for x in range(0, width + 40, 40):
                points.append((x, base-rng.randrange(50, 200-layer*35)))
            points.extend([(width, base), (width, height)])
            shade = (26+layer*13, 45+layer*14, 67+layer*12)
            draw.polygon(points, fill=shade)
    elif terrain == "forest":
        draw.rectangle((0, horizon, width, height), fill=(16, 58, 58))
        for layer in range(3):
            for _ in range(30):
                x = rng.randrange(-20, width+20)
                y = rng.randrange(horizon-100, height)
                h = rng.randrange(100, 230)
                shade = (11+layer*8, 41+layer*12, 39+layer*9)
                draw.polygon(((x, y-h), (x-38, y), (x+38, y)), fill=shade)
    elif terrain == "ocean":
        draw.rectangle((0, horizon, width, height), fill=(19, 70, 100))
        for _ in range(110):
            x, y = rng.randrange(width), rng.randrange(horizon, height)
            draw.line((x, y, x+rng.randrange(12, 65), y), fill=(91, 155, 168), width=2)
    else:
        for layer in range(3):
            base = horizon + layer*100
            points = [(0, height), (0, base)]
            for x in range(0, width+60, 60):
                points.append((x, base-rng.randrange(10, 90)))
            points.extend([(width, height)])
            draw.polygon(points, fill=(123+layer*19, 71+layer*14, 68+layer*9))
    return im.filter(ImageFilter.GaussianBlur(radius=.4))


def generate(output):
    root = Path(output)
    art = root / "art"
    art.mkdir(parents=True, exist_ok=True)
    assets = []
    for name in sorted(SCENES):
        filename = name + ".png"
        render(name).save(art / filename, optimize=True)
        tags = name.replace("-", " ").split()
        assets.append({"id": name, "status": "pending_review", "category": "background",
                       "path": "art/" + filename, "tags": tags,
                       "source": "astra.background_factory", "license": "original_procedural"})
    manifest = root / "art" / "manifest.json"
    manifest.write_text(json.dumps({"assets": assets}, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(generate(args.output))


if __name__ == "__main__":
    main()
