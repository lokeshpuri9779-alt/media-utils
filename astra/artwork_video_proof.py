"""Render an isolated vertical MP4 proof from ASTRA's generated artwork.

This is a QA artifact, not a YouTube publication or final storytelling renderer.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from astra.background_factory import generate
from astra.asset_library import draw_asset_for_scene


def make_preview(output, *, seconds_per_scene=2, fps=8):
    output = Path(output)
    if not 1 <= seconds_per_scene <= 10 or not 1 <= fps <= 30:
        raise ValueError("invalid_preview_timing")
    with tempfile.TemporaryDirectory(prefix="astra-video-proof-") as temp:
        root = Path(temp)
        manifest = generate(root / "generated")
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        # Fixture-only approval: the production asset manifest is never modified.
        for item in payload["assets"]:
            item["status"] = "approved"
        fixture = root / "generated/art/fixture-only.json"
        fixture.write_text(json.dumps(payload), encoding="utf-8")
        frames = root / "frames"
        frames.mkdir()
        count = 0
        for item in payload["assets"]:
            for step in range(seconds_per_scene * fps):
                frame = Image.new("RGB", (540, 960), "black")
                scene = {"visual_prompt": item["id"].replace("-", " ")}
                if not draw_asset_for_scene(frame, scene, step / fps, fixture):
                    raise ValueError("asset_not_rendered:" + item["id"])
                # Visible proof labels only; not production captions.
                draw = ImageDraw.Draw(frame)
                draw.rounded_rectangle((22, 830, 518, 904), radius=16, fill=(9, 16, 30))
                draw.text((38, 854), item["id"].replace("-", " ").upper(), fill="white")
                frame.save(frames / f"{count:05d}.png")
                count += 1
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-framerate", str(fps), "-i", str(frames / "%05d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(output)], check=True, timeout=180)
        if not output.is_file() or output.stat().st_size == 0:
            raise ValueError("empty_preview_video")
        return {"scenes": len(payload["assets"]), "frames": count,
                "width": 540, "height": 960, "fps": fps,
                "production_approved": 0, "video_bytes": output.stat().st_size}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(make_preview(args.output), sort_keys=True))


if __name__ == "__main__":
    main()
