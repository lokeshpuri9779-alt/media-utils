"""Produce before/after artifact backdrop contact sheets without publishing.

Usage: python -m astra_v2.visual_artifact_comparison --output runtime-artifacts/artifact-comparison
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw
from astra_v2.visual_artifact_backdrop import apply_backdrop, choose_scene

# Exercise every supported procedural environment, not just a curated subset.
from astra_v2.visual_artifact_library import SCENES
SAMPLES = tuple((scene, f"A mystery in the {scene}") for scene in SCENES)


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    unique_hashes = set()
    for i, (expected, speech) in enumerate(SAMPLES):
        shot = {"speech": speech, "story_environment": expected}
        actual = choose_scene(shot)
        if actual != expected:
            raise ValueError(f"Scene mismatch: {expected} != {actual}")
        identity = f"artifact-comparison-{i}"
        before = Image.new("RGB", (1080, 1920), (14, 22, 40))
        after = apply_backdrop(before.copy(), shot, identity)
        if before.tobytes() == after.tobytes():
            raise ValueError(f"Artifact failed to alter scene: {expected}")
        import hashlib
        digest = hashlib.sha256(after.tobytes()).hexdigest()
        if digest in unique_hashes:
            raise ValueError(f"Duplicate backdrop output for {expected}")
        unique_hashes.add(digest)
        before.thumbnail((270, 480))
        after.thumbnail((270, 480))
        rows.append((expected, before, after))
    sheet = Image.new("RGB", (540 * 2, 520 * len(rows)), (12, 16, 28))
    draw = ImageDraw.Draw(sheet)
    for i, (name, before, after) in enumerate(rows):
        y = i * 520
        draw.text((10, y + 5), name + " — BASELINE", fill="white")
        draw.text((550, y + 5), name + " — ARTIFACT ON", fill="white")
        sheet.paste(before.resize((540, 480)), (0, y + 35))
        sheet.paste(after.resize((540, 480)), (540, y + 35))
    image_path = output / "backdrop-comparison.png"
    sheet.save(image_path, optimize=True)
    report = {"samples": len(rows), "unique_backdrops": len(unique_hashes),
              "visual_quality_approved": False,
              "production_ready": False,
              "review_required": ["scene readability", "depth", "lighting", "composition", "full-video integration"],
              "scenes": [x[0] for x in rows],
              "artifact_mode": "opt-in", "scope": "backdrop layer only",
              "note": "Synthetic baseline; passing pixel checks does not constitute visual approval or production readiness"}
    (output / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    return image_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runtime-artifacts/artifact-comparison")
    args = parser.parse_args()
    print(generate(args.output))
