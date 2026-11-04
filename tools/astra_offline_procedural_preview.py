"""CPU-only procedural 2D proof of rendered ASTRA storyboard actions.

Creates three short, low-resolution MP4s from assistant-authored reference
scene packets. Pixel-difference tests detect motion in the scene area;
they do NOT prove narrative semantics, photorealism, or publication quality.
No AI inference, network access, production routes, or upload credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from tools.astra_offline_storyboard import build_packet
from tools.astra_offline_visual_cues import audit_visible_outcome
from tools.astra_offline_character_rig import render_actor_layer, audit_character_presence

W, H = 320, 180
FPS = 12
FRAMES_PER_SCENE = 12
TOTAL_FRAMES = 4 * FRAMES_PER_SCENE
ROI = (43, 30, 285, 154)
KINDS = ("glasshouse-sunshade", "footbridge-ducklings", "moon-mirror-garden")
STAGES = ("setup", "attempt", "setback", "payoff")


def _disc(draw: ImageDraw.ImageDraw, x: int, y: int, radius: int,
          color: tuple[int, int, int]) -> None:
    draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)


def _greenhouse(draw: ImageDraw.ImageDraw, stage: int, t: float) -> None:
    draw.rectangle((0, 32, W, H), fill=(204, 231, 221))
    for x in (48, 104, 160, 216, 272):
        draw.line((x, 31, x, 176), fill=(124, 156, 145), width=3)
    draw.line((5, 34, 313, 34), fill=(119, 100, 71), width=6)
    for x in (65, 147, 229):
        draw.rectangle((x-21, 126, x+22, 143), fill=(112, 79, 58))
        for offset in (-10, 0, 10):
            draw.line((x+offset, 126, x+offset, 107), fill=(44, 122, 66), width=3)
            _disc(draw, x+offset, 107, 4, (53, 148, 74))
    if stage == 0:
        shade = 18
    elif stage == 1:
        shade = int(18 + 125 * t)
    elif stage == 2:
        shade = int(143 - 125 * t)
    else:
        shade = int(18 + 231 * t)
    draw.rectangle((48, 50, 48+shade, 72), fill=(50, 118, 128))
    draw.line((47, 75, 47+shade, 75), fill=(27, 81, 96), width=3)
    draw.ellipse((48+shade-5, 38, 48+shade+5, 48), fill=(194, 126, 65))
    if stage == 2:
        y = int(77 + 22 * t)
        draw.line((48+shade, 79, 104, y), fill=(117, 70, 41), width=2)
    if stage == 3:
        draw.line((48+shade, 74, 295, 128), fill=(152, 91, 36), width=4)
    if stage == 3:
        # Visible foliage shading progress: darker leaves beneath pulled canopy.
        for x in (65, 147, 229):
            if x < 48+shade:
                _disc(draw, x, 112, 5, (29, 92, 54))


def _bridge(draw: ImageDraw.ImageDraw, stage: int, t: float) -> None:
    draw.rectangle((0, 32, W, 102), fill=(210, 235, 242))
    draw.rectangle((0, 103, W, H), fill=(78, 156, 185))
    draw.ellipse((232, 86, 330, 173), fill=(172, 172, 120))
    draw.ellipse((-18, 89, 85, 174), fill=(167, 172, 118))
    for x in (80, 244):
        draw.rectangle((x-6, 68, x+6, 145), fill=(91, 68, 56))
    for y in (121, 145):
        draw.line((90, y, 236, y), fill=(118, 193, 205), width=2)
    if stage == 0:
        start, end, plank_y = 97, 110, 107
    elif stage == 1:
        start, end, plank_y = 97, int(108+123*t), 107
    elif stage == 2:
        start, end, plank_y = 97, 233, int(106+24*t)
    else:
        start, end, plank_y = 97, 233, 105
    draw.polygon([(start, plank_y), (end, plank_y),
                  (end, plank_y+10), (start, plank_y+10)], fill=(147, 96, 65))
    if stage == 2:
        draw.line((104, plank_y-4, 134, plank_y+8), fill=(230, 215, 180), width=3)
    if stage == 3:
        for x in (101, 225):
            draw.line((x, 106, x+2, 85), fill=(211, 195, 126), width=3)
    for i in range(3):
        if stage == 3:
            duck_x = int(262 - 215 * t) + i*16
            duck_y = 99
        else:
            duck_x = 253+i*16 + int(3*t)
            duck_y = 86
        _disc(draw, duck_x, duck_y, 6, (248, 220, 88))
        draw.polygon([(duck_x+4, duck_y), (duck_x+11, duck_y+2),
                      (duck_x+4, duck_y+4)], fill=(226, 133, 56))


def _mirror(draw: ImageDraw.ImageDraw, stage: int, t: float) -> None:
    draw.rectangle((0, 32, W, 125), fill=(29, 36, 77))
    draw.rectangle((0, 126, W, H), fill=(83, 86, 97))
    for x in (90, 142, 195):
        draw.line((x, 117, x, 145), fill=(64, 92, 65), width=3)
        bloom = stage == 3 and t > 0.55
        petals = (235, 163, 228) if bloom else (85, 89, 145)
        for dx, dy in ((-5, 0), (5, 0), (0, -5), (0, 5)):
            _disc(draw, x+dx, 113+dy, 5 if bloom else 3, petals)
        _disc(draw, x, 113, 3, (223, 178, 96))
    draw.rectangle((245, 50, 271, 85), fill=(137, 144, 166))
    draw.line((259, 84, 259, 128), fill=(133, 112, 117), width=5)
    if stage == 0:
        target = (286, 81)
    elif stage == 1:
        target = (int(286-138*t), int(81+33*t))
    elif stage == 2:
        target = (int(148+138*t), int(114-33*t))
    else:
        target = (int(286-138*t), int(81+33*t))
    draw.polygon([(250, 62), (262, 72),
                  (target[0]+15, target[1]+12), (target[0]-15, target[1]-3)],
                 fill=(119, 124, 166))
    _disc(draw, target[0], target[1], 12, (210, 199, 148))
    draw.line((245, 50, 273, 75), fill=(184, 199, 224), width=5)
    if stage == 2:
        draw.line((267, 67, 281, int(72+16*t)), fill=(210, 112, 87), width=3)
    if stage == 3:
        draw.rectangle((268, 69, 276, 78), fill=(221, 178, 95))


def render_frame(case_id: str, stage: int, progress: float) -> Image.Image:
    if case_id not in KINDS or not isinstance(stage, int) or not 0 <= stage < 4:
        raise ValueError("unsupported procedural scene")
    if not isinstance(progress, (int, float)) or not 0 <= progress <= 1:
        raise ValueError("frame progress out of bounds")
    image = Image.new("RGB", (W, H), (240, 240, 240))
    draw = ImageDraw.Draw(image)
    if case_id == KINDS[0]:
        _greenhouse(draw, stage, progress)
    elif case_id == KINDS[1]:
        _bridge(draw, stage, progress)
    else:
        _mirror(draw, stage, progress)
    # The same small hand-articulated character rig persists across all
    # four shots. This is a pixel-level cue, not semantic identity proof.
    image = Image.alpha_composite(
        image.convert("RGBA"), render_actor_layer(case_id, stage, progress)
    ).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, W, 28), fill=(17, 24, 35))
    draw.text((7, 8), case_id + " | " + STAGES[stage], fill=(230, 236, 240))
    draw.rectangle((0, 160, W, 180), fill=(19, 25, 32))
    draw.text((7, 165), "CPU PROCEDURAL PREVIEW - NOT FINAL VIDEO", fill=(220, 227, 231))
    return image


def changed_action_pixels(first: Image.Image, last: Image.Image) -> int:
    if first.mode != "RGB" or last.mode != "RGB" or first.size != (W, H) or last.size != (W, H):
        raise ValueError("unexpected scene image format")
    diff = ImageChops.difference(first.crop(ROI), last.crop(ROI))
    # Ignore non-scene labels and subpixel noise; detect actual color changes.
    return sum(1 for rgb in diff.getdata() if max(rgb) >= 16)


def _sha_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def render_review_videos(output: Path, *, ffmpeg: str = "ffmpeg",
                         ffprobe: str = "ffprobe") -> dict:
    """Render three isolated MP4 proofs, check decoded frame count and pixels."""
    output = Path(output)
    packet = build_packet()
    stories = packet["packets"]
    if {item["case_id"] for item in stories} != set(KINDS):
        raise ValueError("unrecognized storyboard set")
    if not shutil.which(ffmpeg) or not shutil.which(ffprobe):
        raise ValueError("system ffmpeg and ffprobe are required; no network install")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix="astra-preview-") as temp:
        tempdir = Path(temp)
        for story in stories:
            case = story["case_id"]
            directory = tempdir / case
            directory.mkdir()
            previews, per_shot = [], []
            index = 0
            for stage, shot in enumerate(story["shots"]):
                if shot["stage"] != STAGES[stage]:
                    raise ValueError("storyboard stages out of order")
                start = render_frame(case, stage, 0.0)
                finish = render_frame(case, stage, 1.0)
                changed = changed_action_pixels(start, finish)
                if changed < 64:
                    raise ValueError(f"{case} {STAGES[stage]} no verified action pixels: {changed}")
                per_shot.append({"stage": STAGES[stage], "changed_action_pixels": changed,
                                 "pixel_motion_detected": True,
                                 "pixel_semantics_verified": False})
                previews.append(finish)
                for f in range(FRAMES_PER_SCENE):
                    img = render_frame(case, stage, f/(FRAMES_PER_SCENE-1))
                    img.save(directory / f"frame_{index:04d}.png")
                    index += 1
            if index != TOTAL_FRAMES:
                raise ValueError("wrong output frame count")
            raw_visual_cues = audit_visible_outcome(
                case, render_frame(case, 0, 0.0), render_frame(case, 3, 1.0)
            )
            if not raw_visual_cues["passed"]:
                raise ValueError(f"{case} missing rendered outcome cues: {raw_visual_cues['failed_cues']}")
            raw_actor_audit = audit_character_presence(case, previews)
            if not raw_actor_audit["passed"]:
                raise ValueError(f"{case} missing persistent rendered actor")
            contact = Image.new("RGB", (W*4, H), (15, 15, 15))
            for i, img in enumerate(previews):
                contact.paste(img, (i*W, 0))
            contact_path = output / f"{case}-contact.png"
            contact.save(contact_path)
            mp4 = output / f"{case}.mp4"
            command = [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
                "-y", "-framerate", str(FPS), "-start_number", "0",
                "-i", str(directory / "frame_%04d.png"),
                "-frames:v", str(TOTAL_FRAMES), "-an", "-c:v", "libx264",
                "-threads", "2", "-preset", "veryfast", "-crf", "26",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4),
            ]
            subprocess.run(command, check=True, timeout=90,
                           capture_output=True, text=True)
            probe = subprocess.run(
                [ffprobe, "-v", "error", "-select_streams", "v:0",
                 "-count_frames", "-show_entries",
                 "stream=codec_name,width,height,nb_read_frames,r_frame_rate",
                 "-of", "json", str(mp4)],
                check=True, timeout=30, capture_output=True, text=True,
            )
            streams = json.loads(probe.stdout).get("streams", [])
            if len(streams) != 1:
                raise ValueError("missing or invalid MP4 video stream")
            stream = streams[0]
            if (stream.get("codec_name") != "h264" or
                stream.get("width") != W or stream.get("height") != H or
                int(stream.get("nb_read_frames", 0)) != TOTAL_FRAMES or
                stream.get("r_frame_rate") != f"{FPS}/1"):
                raise ValueError("MP4 decode/frame count mismatch")
            if not 1024 <= mp4.stat().st_size <= 6_000_000:
                raise ValueError("unexpected MP4 size; refuse misleading preview")
            decoded = subprocess.run(
                [ffmpeg, "-v", "error", "-nostdin", "-i", str(mp4),
                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-an", "pipe:1"],
                check=True, timeout=60, capture_output=True,
            )
            frame_bytes = W * H * 3
            if len(decoded.stdout) != TOTAL_FRAMES * frame_bytes:
                raise ValueError("decoded MP4 pixel payload does not contain all frames")
            first_decoded = Image.frombytes("RGB", (W, H), decoded.stdout[:frame_bytes])
            last_decoded = Image.frombytes("RGB", (W, H), decoded.stdout[-frame_bytes:])
            decoded_visual_cues = audit_visible_outcome(
                case, first_decoded, last_decoded
            )
            if not decoded_visual_cues["passed"]:
                raise ValueError(f"{case} encoded MP4 misses outcome cues: {decoded_visual_cues['failed_cues']}")
            decoded_stage_ends = [
                Image.frombytes(
                    "RGB", (W, H),
                    decoded.stdout[
                        ((stage+1)*FRAMES_PER_SCENE-1)*frame_bytes:
                        ((stage+1)*FRAMES_PER_SCENE)*frame_bytes
                    ],
                )
                for stage in range(len(STAGES))
            ]
            decoded_actor_audit = audit_character_presence(case, decoded_stage_ends)
            if not decoded_actor_audit["passed"]:
                raise ValueError(f"{case} encoded MP4 missing character continuity cue: {decoded_actor_audit['marker_pixel_counts']}")
            results.append({
                "case_id": case, "file": mp4.name, "contact_sheet": contact_path.name,
                "sha256": _sha_file(mp4), "bytes": mp4.stat().st_size,
                "frame_count": TOTAL_FRAMES, "fps": FPS,
                "duration_seconds": TOTAL_FRAMES / FPS,
                "codec": "h264", "dimensions": [W, H],
                "shot_pixel_evidence": per_shot,
                "pixel_changes_verified": True,
                "raw_rendered_visual_cues": raw_visual_cues,
                "decoded_mp4_visual_cues": decoded_visual_cues,
                "rendered_character_presence_cues": raw_actor_audit,
                "decoded_character_presence_cues": decoded_actor_audit,
                "decoded_frame_count_verified": TOTAL_FRAMES,
                "visible_story_outcome_cues_verified": True,
                "story_semantic_accuracy": "not_verified",
                "character_continuity_by_visual_model": "not_verified",
                "render_style": "simple_procedural_2d_shapes",
                "review_only": True, "approved": False,
                "production_ready": False, "published": False,
            })
    report = {
        "experiment": "astra-cpu-procedural-motion-proofs-v1",
        "video_count": len(results), "video_previews": results,
        "real_mp4_encoded": True, "actual_scene_pixel_differences_checked": True,
        "decoded_mp4_outcome_cues_checked": True,
        "decoded_mp4_character_presence_cues_checked": True,
        "gpu_used": False, "image_generation_model_used": False,
        "model_inference_executed": False, "audio_included": False,
        "production_quality": "not_verified",
        "human_visual_review_required": True,
        "approved": False, "production_ready": False, "published": False,
    }
    (output / "review-report.json").write_text(json.dumps(report, indent=2)+"\n",
                                                encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path("artifacts/offline-procedural-previews"))
    args = parser.parse_args()
    result = render_review_videos(args.output)
    print(json.dumps({"experiment": result["experiment"],
                      "videos": result["video_count"],
                      "approved": False, "production_ready": False,
                      "published": False}, indent=2))


if __name__ == "__main__":
    main()
