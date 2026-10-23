"""Offline comparison of existing artifact backdrops and layered prototype.

Usage: python -m astra_v2.visual_layered_comparison --output runtime-artifacts/layered-comparison
Never uploads, publishes, or modifies the production renderer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
from astra_v2.visual_artifact_library import SCENES
from astra_v2.visual_artifact_backdrop import apply_backdrop
from astra_v2.visual_layered_prototype import render_layered_scene
from astra_v2.visual_hybrid_prototype import render_hybrid_scene


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (1080, 20 * 355), (15, 19, 30))
    draw = ImageDraw.Draw(sheet)
    hashes = set()
    for i, scene in enumerate(SCENES):
        shot = {"story_environment": scene}
        original = apply_backdrop(Image.new("RGB", (1080, 1920), (14, 22, 40)), shot, f"compare-{i}")
        layered = render_layered_scene(scene, f"compare-{i}")
        digest = hashlib.sha256(layered.tobytes()).hexdigest()
        if digest in hashes:
            raise ValueError(f"Layered scene collision: {scene}")
        hashes.add(digest)
        hybrid = render_hybrid_scene(scene, f"compare-{i}")
        y = i * 355
        draw.text((10, y + 4), scene + " | current opt-in", fill="white")
        draw.text((370, y + 4), scene + " | layered prototype", fill="white")
        sheet.paste(original.resize((350, 320)), (0, y + 28))
        sheet.paste(layered.resize((350, 320)), (360, y + 28))
        draw.text((730, y + 4), scene + " | hybrid candidate", fill="white")
        sheet.paste(hybrid.resize((350, 320)), (720, y + 28))
    sheet.save(output / "layered-side-by-side.png", optimize=True)
    report = {
        "scenes": len(SCENES), "unique_layered_scenes": len(hashes),
        "visual_quality_approved": False, "production_ready": False,
        "publishing_integration": False,
        "hybrid_evaluation": True,
        "note": "Offline synthetic visual comparison; human visual review required",
    }
    (output / "layered-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return output / "layered-side-by-side.png"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runtime-artifacts/layered-comparison")
    print(generate(parser.parse_args().output))
