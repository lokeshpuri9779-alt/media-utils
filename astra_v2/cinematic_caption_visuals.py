"""Procedural cinematic scene plates and floating caption overlays.

All visuals are generated locally with Pillow. No stock footage, network calls,
hosted image models, or paid APIs are used. Background motion is applied by FFmpeg
during the final render; caption overlays remain crisp and independently positioned.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH, HEIGHT = 1080, 1920


def _font(size: int):
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _palette(phrase: str, index: int) -> tuple[tuple[int, int, int], ...]:
    digest = hashlib.sha256(f"{index}:{phrase}".encode("utf-8")).digest()
    palettes = (
        ((5, 12, 30), (12, 45, 72), (37, 102, 126)),
        ((18, 8, 32), (65, 24, 76), (132, 57, 89)),
        ((5, 24, 25), (12, 72, 67), (51, 126, 103)),
        ((22, 14, 7), (84, 47, 19), (153, 94, 42)),
        ((8, 13, 34), (34, 49, 100), (83, 91, 153)),
    )
    return palettes[digest[0] % len(palettes)]


def _gradient(size: tuple[int, int], colors):
    width, height = size
    top, middle, bottom = colors
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(height):
        t = y / max(1, height - 1)
        if t < 0.62:
            u = t / 0.62
            a, b = top, middle
        else:
            u = (t - 0.62) / 0.38
            a, b = middle, bottom
        color = tuple(int(a[c] * (1 - u) + b[c] * u) for c in range(3))
        for x in range(width):
            pixels[x, y] = color
    return image


def create_scene_plate(phrase: str, output: str | Path, index: int = 0) -> Path:
    """Create a full-bleed abstract cinematic plate with layered visual depth."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    image = _gradient((WIDTH, HEIGHT), _palette(phrase, index)).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    digest = hashlib.sha256(f"scene:{index}:{phrase}".encode("utf-8")).digest()
    # Large soft orbital forms give the camera move visible parallax-like detail.
    cx = 160 + digest[1] * 2.3
    cy = 360 + digest[2] * 3.1
    radius = 260 + digest[3]
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow, "RGBA")
    gd.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
               fill=(95, 190, 220, 26))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    image = Image.alpha_composite(image, glow)
    draw = ImageDraw.Draw(image, "RGBA")
    # Horizon arcs and fine lines create a cinematic, non-card composition.
    for n in range(7):
        offset = n * 42
        draw.arc((300-offset, 520-offset, 1180+offset, 1400+offset),
                 start=188, end=345, fill=(205, 231, 245, 24 + n * 2), width=3)
    for n in range(12):
        x = (digest[(n + 4) % len(digest)] * 4 + n * 73) % WIDTH
        y = (digest[(n + 12) % len(digest)] * 6 + n * 117) % HEIGHT
        r = 2 + digest[(n + 20) % len(digest)] % 5
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(224, 242, 255, 90))
    # A strong off-centre geometric subject; the lower half stays quiet for captions.
    anchor_x = 260 + digest[5] * 2
    anchor_y = 500 + digest[6] * 2
    draw.ellipse((anchor_x-180, anchor_y-180, anchor_x+180, anchor_y+180),
                 outline=(220, 239, 255, 95), width=5)
    draw.ellipse((anchor_x-125, anchor_y-125, anchor_x+125, anchor_y+125),
                 outline=(220, 239, 255, 55), width=2)
    draw.line((anchor_x-300, anchor_y+210, anchor_x+360, anchor_y-250),
              fill=(210, 235, 255, 55), width=3)
    # Subtle vignette preserves contrast without a text panel.
    vignette = Image.new("L", (WIDTH, HEIGHT), 0)
    vd = ImageDraw.Draw(vignette)
    vd.ellipse((-240, -180, WIDTH+240, HEIGHT+180), fill=210)
    vignette = vignette.filter(ImageFilter.GaussianBlur(180))
    shade = Image.new("RGBA", image.size, (0, 0, 0, 95))
    shade.putalpha(Image.eval(vignette, lambda p: 95 - int(p * 0.35)))
    image = Image.alpha_composite(image, shade)
    image.convert("RGB").save(target, "PNG", optimize=True)
    return target


def create_floating_caption(phrase: str, output: str | Path, index: int = 0) -> Path:
    """Create transparent, shadowed text with no opaque card or lower-third strip."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    words = str(phrase).split()
    font_size = 76 if len(words) <= 4 else 68
    font = _font(font_size)
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] > 900 and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    while len(lines) > 2 and font_size > 48:
        font_size -= 4
        font = _font(font_size)
        lines, current = [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if draw.textbbox((0, 0), candidate, font=font)[2] > 900 and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
    if len(lines) > 2:
        raise ValueError("Caption phrase exceeds the two-line floating-caption limit")
    line_height = font_size + 22
    block_height = len(lines) * line_height
    # Alternate between two safe floating positions; never reserve a fixed strip.
    y = 1040 + (index % 3 - 1) * 92
    y = min(max(820, y), HEIGHT - block_height - 250)
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text((x+3, y+5), line, font=font, fill=(0, 0, 0, 185),
                  stroke_width=5, stroke_fill=(0, 0, 0, 150))
        draw.text((x, y), line, font=font, fill=(250, 252, 255, 255),
                  stroke_width=2, stroke_fill=(8, 16, 30, 210))
        y += line_height
    overlay.save(target, "PNG", optimize=True)
    return target


def camera_motion_filter(duration: float, fps: int = 30, reverse: bool = False) -> str:
    """FFmpeg zoompan filter: slow continuous camera drift on the background only."""
    frames = max(1, int(round(float(duration) * int(fps))))
    zoom = "max(1.0,1.045-on*0.00045)" if reverse else "min(1.045,1+on*0.00045)"
    return (
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)+sin(on/47)*9':"
        f"y='ih/2-(ih/zoom/2)+cos(on/61)*12':d={frames}:"
        f"s={WIDTH}x{HEIGHT}:fps={int(fps)},setsar=1"
    )
