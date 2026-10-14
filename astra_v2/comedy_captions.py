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
    """Route pilot dialogue through the shared format-aware caption engine."""
    from astra_v2.shared_caption_engine import draw_shared_caption
    phrase = caption_text(action, t, storybook)
    if not phrase:
        return None
    return draw_shared_caption(image, phrase, style="comedy", position="top")
