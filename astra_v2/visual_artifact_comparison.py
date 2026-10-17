"""Produce before/after artifact backdrop contact sheets without publishing.

Usage: python -m astra_v2.visual_artifact_comparison --output runtime-artifacts/artifact-comparison
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw
from astra_v2.visual_artifact_backdrop import apply_backdrop, choose_scene

SAMPLES = (
    ("lighthouse", "The lighthouse keeper follows a strange signal"),
    ("forest", "A fox follows the trail through the forest"),
    ("museum", "The museum clock stopped at midnight"),
    ("railway", "The railway station hides a mystery"),
    ("underwater", "An underwater rescue begins"),
    ("garden", "The garden blooms after the rain"),
    ("castle", "A secret inside the castle"),
    ("city", "A strange light over the city"),
)

def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
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
    report = {"samples": len(rows), "scenes": [x[0] for x in rows],
              "artifact_mode": "opt-in", "scope": "backdrop layer only",
              "note": "Synthetic baseline, not full video render or human visual approval"}
    (output / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    return image_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runtime-artifacts/artifact-comparison")
    args = parser.parse_args()
    print(generate(args.output))
