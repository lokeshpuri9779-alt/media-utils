"""Offline integration smoke: approved per-scene images -> real Studio MP4.

Generated images are CI-only fixtures, NOT provider-generated or editorially approved.
Never calls a publisher.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw
from premium_stories import catalog
from studio_renderer import make_plan


def main():
    story = dict(catalog()[0])
    story.setdefault("content_id", "ci-approved-artwork-smoke")
    with tempfile.TemporaryDirectory(prefix="astra-approved-studio-") as temp:
        root = Path(temp)
        art = root / "art"
        art.mkdir()
        shots = make_plan(dict(story))
        if not shots:
            raise AssertionError("Studio returned no shots")
        assets = []
        for index, _shot in enumerate(shots, 1):
            scene = f"{index:03d}"
            filename = art / f"{scene}.png"
            frame = Image.new("RGB", (540, 960), (35 + index * 7 % 100, 65, 120))
            draw = ImageDraw.Draw(frame)
            draw.rectangle((65, 190, 475, 780), fill=(60, 110 + index * 11 % 100, 160))
            frame.save(filename)
            assets.append({"id": f"ci-scene-{scene}", "path": f"art/{scene}.png",
                           "category": "background", "status": "approved",
                           "story_content_id": story["content_id"], "scene_id": scene,
                           "sha256": hashlib.sha256(filename.read_bytes()).hexdigest(),
                           "review_scope": "ci_fixture_only"})
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"assets": assets}), encoding="utf-8")
        source = root / "story.json"
        source.write_text(json.dumps(story), encoding="utf-8")
        output = root / "review.mp4"
        subprocess.run([sys.executable, "studio_renderer.py", "--preview", str(output),
                        "--story-json", str(source), "--reviewed-art-manifest", str(manifest),
                        "--stills-dir", str(root / "stills")],
                       check=True, timeout=240)
        report = json.loads(output.with_suffix(".json").read_text())
        if len(report["scenes"]) != len(assets):
            raise AssertionError("Rendered shot count differs from approved manifest")
        if not all(shot.get("artwork_asset_id") for shot in report["scenes"]):
            raise AssertionError("At least one shot omitted approved artwork")
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams",
                                "-of", "json", str(output)],
                               check=True, capture_output=True, text=True, timeout=30)
        streams = json.loads(probe.stdout)["streams"]
        video = next(s for s in streams if s["codec_type"] == "video")
        if (video["width"], video["height"]) != (540, 960):
            raise AssertionError("Incorrect vertical video dimensions")
        if not any(s["codec_type"] == "audio" for s in streams):
            raise AssertionError("Missing narration audio")
        if len(list((root / "stills").glob("scene_*.jpg"))) != len(assets):
            raise AssertionError("Missing rendered scene stills")
        print("ASTRA_APPROVED_STUDIO_MP4_E2E_PASS", len(assets), output.stat().st_size)


if __name__ == "__main__":
    main()
