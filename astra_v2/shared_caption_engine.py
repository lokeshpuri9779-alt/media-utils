"""Shared, opt-in caption compositor for vertical and landscape video.

Pillow-only, deterministic, no API calls, no publication changes.
All coordinates are proportional to the actual image dimensions.
"""
from functools import lru_cache
from pathlib import Path
from PIL import ImageDraw, ImageFont

STYLES = {
    "comedy": {"position": "top", "fill": (255, 242, 208), "border": (255, 214, 107), "size": .079},
    "suspense": {"position": "lower", "fill": (255, 255, 255), "border": (142, 189, 255), "size": .070},
    "documentary": {"position": "lower", "fill": (255, 255, 255), "border": (120, 216, 210), "size": .067},
    "narration": {"position": "lower", "fill": (255, 255, 255), "border": (251, 204, 104), "size": .070},
    "dialogue": {"position": "lower", "fill": (255, 245, 216), "border": (251, 204, 104), "size": .073},
}


@lru_cache(maxsize=128)
def _font(size):
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, int(size))
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(draw, phrase, font, max_width, stroke):
    lines = []
    for paragraph in phrase.split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = (current + " " + word).strip()
            if current and draw.textbbox((0, 0), candidate, font=font,
                                         stroke_width=stroke)[2] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def draw_shared_caption(image, text, *, style="narration", position=None,
                        language="auto", max_lines=2):
    """Draw a measured, outlined, high-contrast caption on a PIL image.

    Returns layout metadata. Refuses text that cannot fit instead of clipping.
    Non-Latin text requires a system font supporting the requested script;
    language is metadata, not a claim of shaping or font coverage.
    """
    if style not in STYLES:
        raise ValueError("unsupported caption style")
    if not isinstance(text, str) or not text.strip():
        return None
    if not 1 <= max_lines <= 4:
        raise ValueError("max_lines must be 1..4")
    if position not in (None, "top", "lower"):
        raise ValueError("invalid caption position")
    width, height = image.size
    if width < 200 or height < 200:
        raise ValueError("caption frame too small")
    conf = STYLES[style]
    placement = position or conf["position"]
    d = ImageDraw.Draw(image)
    margin = round(width * .06)
    outer_w = width - 2 * margin
    inner_w = outer_w - 2 * round(width * .04)
    # Scale from width for both 540x960 and 1080x1920, but use
    # relative limits to avoid oversized lettering in wide frames.
    base_size = round(min(width * conf["size"], height * .065))
    min_size = max(14, round(base_size * .67))
    selected = None
    stroke = max(2, round(width * .005))
    for size in range(base_size, min_size - 1, -1):
        font = _font(size)
        lines = _wrap(d, text.strip(), font, inner_w, stroke)
        if len(lines) > max_lines:
            continue
        bounds = [d.textbbox((0, 0), line or " ", font=font,
                             stroke_width=stroke) for line in lines]
        widths = [b[2] - b[0] for b in bounds]
        heights = [b[3] - b[1] for b in bounds]
        spacing = max(3, round(size * .15))
        padding = round(size * .38)
        total_h = sum(heights) + spacing * (len(lines) - 1) + padding * 2
        if max(widths) <= inner_w and total_h <= height * .20:
            selected = (size, font, lines, bounds, heights, spacing, padding, total_h)
            break
    if selected is None:
        raise ValueError("caption does not fit safely; split into timed chunks")
    size, font, lines, bounds, heights, spacing, padding, total_h = selected
    if placement == "top":
        top = round(height * .116)
    else:
        top = round(height * .77 - total_h / 2)
    top = max(round(height * .09), min(top, round(height * .84 - total_h)))
    box = (margin, top, width - margin, top + total_h)
    outline = max(2, round(width * .004))
    d.rounded_rectangle(box, radius=max(9, round(width * .03)),
                        fill=(13, 19, 32), outline=conf["border"], width=outline)
    y = top + padding
    for line, b, h in zip(lines, bounds, heights):
        x = (width - (b[2] - b[0])) / 2 - b[0]
        d.text((x, y - b[1]), line, font=font, fill=conf["fill"],
               stroke_width=stroke, stroke_fill=(0, 0, 0))
        y += h + spacing
    return {"text": text.strip(), "font_size": size, "lines": lines,
            "box": box, "style": style, "position": placement,
            "language": language, "width": width, "height": height}
