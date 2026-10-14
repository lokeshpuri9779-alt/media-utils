"""Large, mobile-readable caption overlays for the isolated cartoon pilot."""
from PIL import ImageDraw, ImageFont

CUES = {
    "approach": "WHAT IS THAT?",
    "point": "DON'T TOUCH IT!",
    "carry": "TOO LATE...",
    "react": "OH NO!",
    "celebrate": "I DID IT!",
}
CAPTION_FONT_SIZE = 43
CAPTION_MIN_FONT_SIZE = 32
CAPTION_TOP = 111
CAPTION_BOTTOM_LIMIT = 260


def caption_text(action, t, storybook=False):
    if action not in CUES:
        return None
    if storybook and action == "celebrate" and t >= 1.65:
        return "HONK?!"
    return CUES[action]


def _font(size):
    # GitHub's Ubuntu runner provides DejaVu Sans; local fallback is safe.
    for name in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
                 "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_caption(image, action, t, storybook=False):
    """Draw bold two-line maximum captions with outline and strong contrast.

    No captions are added to uncaptioned scenes. Captions stay in a safe top
    zone below the experiment label, outside the lower mobile UI controls.
    """
    phrase = caption_text(action, t, storybook)
    if not phrase:
        return None
    draw = ImageDraw.Draw(image)
    width, _ = image.size
    words = phrase.split()
    font = _font(CAPTION_FONT_SIZE)
    # Split long phrases at word boundaries, never truncate the punchline.
    lines = [phrase]
    max_text_width = width - 100
    if draw.textbbox((0, 0), phrase, font=font, stroke_width=3)[2] > max_text_width:
        best = None
        for i in range(1, len(words)):
            left, right = " ".join(words[:i]), " ".join(words[i:])
            w1 = draw.textbbox((0, 0), left, font=font, stroke_width=3)[2]
            w2 = draw.textbbox((0, 0), right, font=font, stroke_width=3)[2]
            candidate = (max(w1, w2), [left, right])
            if best is None or candidate[0] < best[0]:
                best = candidate
        if best is not None:
            lines = best[1]
    while font.size > CAPTION_MIN_FONT_SIZE and any(
        draw.textbbox((0, 0), line, font=font, stroke_width=3)[2] > max_text_width
        for line in lines
    ):
        font = _font(font.size - 1)
    spacing = 5
    heights = [draw.textbbox((0, 0), line, font=font, stroke_width=3)[3] -
               draw.textbbox((0, 0), line, font=font, stroke_width=3)[1]
               for line in lines]
    text_height = sum(heights) + spacing * (len(lines) - 1)
    pad = 17
    box_height = text_height + pad * 2
    y0 = CAPTION_TOP
    y1 = min(CAPTION_BOTTOM_LIMIT, y0 + box_height)
    draw.rounded_rectangle((32, y0, width - 32, y1), radius=18,
                           fill=(13, 19, 32), outline=(255, 214, 107), width=3)
    y = y0 + pad
    for line, h in zip(lines, heights):
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=3)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) / 2 - bbox[0]
        draw.text((x, y - bbox[1]), line, font=font,
                  fill=(255, 242, 208), stroke_width=3,
                  stroke_fill=(0, 0, 0))
        y += h + spacing
    return {"text": phrase, "font_size": font.size, "lines": lines,
            "box": (32, y0, width - 32, y1)}
