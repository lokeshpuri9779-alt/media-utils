"""Offline hybrid compositor: layered atmosphere plus recognizable scene motifs.

No production entry point imports this module. Evaluation only.
"""
from __future__ import annotations
from PIL import Image, ImageChops
from astra_v2.visual_artifact_backdrop import apply_backdrop
from astra_v2.visual_layered_prototype import render_layered_scene


def render_hybrid_scene(scene: str, identity: str) -> Image.Image:
    background = render_layered_scene(scene, identity)
    baseline = Image.new("RGB", (1080, 1920), (14, 22, 40))
    motifs = apply_backdrop(baseline.copy(), {"story_environment": scene}, identity)
    # Isolate non-baseline pixels from the existing scene-specific motif painter.
    # The mask includes its subtle atmospheric marks; no scene labels are invented.
    difference = ImageChops.difference(motifs, baseline).convert("L")
    mask = difference.point(lambda value: 255 if value > 8 else 0)
    # The existing painter owns only the upper scene region.
    mask.paste(0, (0, 1100, 1080, 1920))
    background.paste(motifs, (0, 0), mask)
    return background
