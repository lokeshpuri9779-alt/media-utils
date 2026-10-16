"""Regression tests for ASTRA species-specific Pillow silhouettes."""
from PIL import Image, ImageDraw

from astra_v2.pillow_duo_scene import _ears_and_tail


def _render_tail(actor):
    image = Image.new("RGB", (640, 640), (250, 250, 250))
    draw = ImageDraw.Draw(image)
    _ears_and_tail(draw, actor, 250, 250, 0.4, (199, 128, 75))
    return image


def _non_background_bbox(image):
    background = (250, 250, 250)
    pixels = image.load()
    xs, ys = [], []
    for y in range(image.height):
        for x in range(image.width):
            if pixels[x, y] != background:
                xs.append(x)
                ys.append(y)
    assert xs, "renderer should draw a visible silhouette"
    return min(xs), min(ys), max(xs), max(ys)


def test_squirrel_tail_has_larger_silhouette_than_cat_tail():
    cat_bbox = _non_background_bbox(_render_tail("cat"))
    squirrel_bbox = _non_background_bbox(_render_tail("squirrel"))
    # Both use the same anchor; the squirrel plume should extend farther
    # right than the cat's compact tail, keeping the species silhouettes distinct.
    assert squirrel_bbox[2] > cat_bbox[2] + 35


def test_species_tail_rendering_is_deterministic():
    first = _render_tail("squirrel")
    second = _render_tail("squirrel")
    assert first.tobytes() == second.tobytes()
