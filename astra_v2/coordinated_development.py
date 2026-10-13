"""ASTRA coordinated offline asset-to-scene pipeline.

Generates reproducible scene assignments, storyboard previews, and an optional
local MP4. This is an experimental production candidate, never a publisher.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageChops
from astra_v2.character_object_catalog import (
    CHARACTER_COUNT, OBJECT_COUNT, character, prop, draw_character, draw_prop,
)

W, H = 540, 960
BG = (19, 27, 43)


def stable_index(seed, lane, scene, size):
    payload = f"{seed}|{lane}|{scene}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % size


def build_plan(seed, count=12):
    if not seed or not 1 <= count <= 120:
        raise ValueError("seed required; scenes must be 1..120")
    scenes = []
    used_cast, used_props = set(), set()
    for i in range(count):
        ci = stable_index(seed, "character", i, CHARACTER_COUNT)
        oi = stable_index(seed, "object", i, OBJECT_COUNT)
        # Resolve collisions within this plan, deterministically.
        while ci in used_cast:
            ci = (ci + 1) % CHARACTER_COUNT
        while oi in used_props:
            oi = (oi + 1) % OBJECT_COUNT
        used_cast.add(ci)
        used_props.add(oi)
        scenes.append({
            "scene": i + 1, "character_id": ci, "object_id": oi,
            "character": character(ci), "object": prop(oi),
            "duration_seconds": 2.0,
        })
    return {"seed": seed, "scene_count": count, "scenes": scenes,
            "publication_allowed": False, "quality_approved": False}


def frame(scene, t):
    image = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(image)
    # Keep the cast and object in separate composition zones.
    d.rounded_rectangle((24, 80, W - 24, 550), radius=28,
                        fill=(31, 44, 65))
    d.rounded_rectangle((24, 570, W - 24, 870), radius=28,
                        fill=(34, 49, 68))
    # Catalog artwork is authored at 1080x1920 scale; render on a
    # full-size transparent layer then downsample for consistent geometry.
    canvas = Image.new("RGB", (1080, 1920), BG)
    draw_character(canvas, scene["character_id"], t, 540, 420)
    draw_prop(canvas, scene["object_id"], t, 540, 1420)
    artwork = canvas.resize((W, H), Image.Resampling.LANCZOS)
    # Use separate crops to avoid replacing panel backgrounds wholesale.
    image.paste(artwork.crop((0, 0, W, 560)), (0, 0))
    image.paste(artwork.crop((0, 560, W, 910)), (0, 560))
    d = ImageDraw.Draw(image)
    d.text((30, 28), f"SCENE {scene['scene']:02d} / ASTRA EXPERIMENT", fill=(238, 237, 220))
    d.text((30, 922), "NOT APPROVED FOR PUBLICATION", fill=(245, 176, 121))
    return image


def render(plan, output, fps=8, seconds_per_scene=2, video=False):
    if not 2 <= fps <= 24 or not 1 <= seconds_per_scene <= 10:
        raise ValueError("fps or duration outside safe range")
    output.mkdir(parents=True, exist_ok=True)
    previews = []
    motion_failures = []
    scene_fingerprints = []
    visual_collisions = []
    for scene in plan["scenes"]:
        first, later = frame(scene, 0.0), frame(scene, 0.75)
        if ImageChops.difference(first, later).getbbox() is None:
            motion_failures.append(scene["scene"])
        # Frame fingerprints catch visually identical scene openings despite
        # different catalog identifiers. This is not semantic quality scoring.
        # Exclude scene labels: different scene numbers must not disguise
        # identical artwork. Compare only the two artwork regions.
        artwork_only = Image.new("RGB", (W, 860), BG)
        artwork_only.paste(first.crop((0, 80, W, 550)), (0, 0))
        artwork_only.paste(first.crop((0, 570, W, 870)), (0, 500))
        fingerprint = hashlib.sha256(artwork_only.resize((108, 172)).tobytes()).hexdigest()
        if fingerprint in scene_fingerprints:
            visual_collisions.append(scene["scene"])
        scene_fingerprints.append(fingerprint)
        if len(previews) < 12:
            previews.append(first.resize((270, 480)))
    sheet = Image.new("RGB", (270 * 4, 480 * math.ceil(len(previews) / 4)), BG)
    for i, image in enumerate(previews):
        sheet.paste(image, ((i % 4) * 270, (i // 4) * 480))
    sheet.save(output / "storyboard.png")
    report = {
        "scene_count": len(plan["scenes"]),
        "unique_characters": len({s["character_id"] for s in plan["scenes"]}),
        "unique_objects": len({s["object_id"] for s in plan["scenes"]}),
        "motion_failures": motion_failures,
        "visually_duplicate_scene_openings": visual_collisions,
        "unique_scene_frame_fingerprints": len(set(scene_fingerprints)),
        "publication_allowed": False,
        "quality_approved": False,
        "note": "Offline technical candidate; manual creative review required.",
    }
    if video:
        import imageio_ffmpeg
        encoder = imageio_ffmpeg.write_frames(
            str(output / "preview.mp4"), (W, H), fps=fps,
            codec="libx264", output_params=["-pix_fmt", "yuv420p", "-crf", "27"],
        )
        encoder.send(None)
        try:
            for scene in plan["scenes"]:
                for k in range(fps * seconds_per_scene):
                    encoder.send(frame(scene, k / fps).tobytes())
        finally:
            encoder.close()
    (output / "plan.json").write_text(json.dumps(plan, indent=2))
    (output / "report.json").write_text(json.dumps(report, indent=2))
    if motion_failures or visual_collisions:
        raise RuntimeError(f"Preview quality gate failed: motion={motion_failures}, duplicate_openings={visual_collisions}")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="astra-development-v1")
    parser.add_argument("--scenes", type=int, default=12)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("development-output"))
    parser.add_argument("--video", action="store_true")
    args = parser.parse_args()
    plan = build_plan(args.seed, args.scenes)
    print(json.dumps(render(plan, args.output, fps=args.fps, video=args.video), indent=2))


if __name__ == "__main__":
    main()
