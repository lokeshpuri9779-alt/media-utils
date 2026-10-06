from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from creative_director import evaluate as evaluate_director, production_feedback


def assess_render(report: dict) -> dict:
    failures = []
    duration = float(report.get("duration") or 0)
    scenes = report.get("scenes") or []
    cq = report.get("creative_quality") or {}
    assets = cq.get("asset_resolution") or {}
    if not (8.0 <= duration <= 28.0):
        failures.append(f"duration outside premium-short window: {duration:.2f}s")
    if len(scenes) < 3:
        failures.append("too few scenes")
    if cq.get("score", 100) < 76:
        failures.append("creative quality score below gate")
    required = int(assets.get("required_subject_media") or 0)
    verified = int(assets.get("verified_subject_media") or 0)
    if required and verified != required:
        failures.append(f"verified editorial media {verified}/{required}")
    return {"pass": not failures, "failures": failures, "duration": duration}


def contact_sheet(stills_dir: Path, output: Path, title: str = "RAYVAN review") -> None:
    paths = sorted(stills_dir.glob("*.jpg"))
    if not paths:
        return
    thumbs = []
    for path in paths:
        im = Image.open(path).convert("RGB")
        im.thumbnail((360, 640))
        thumbs.append((path.name, im.copy()))
    width = max(760, len(thumbs) * 380)
    sheet = Image.new("RGB", (width, 760), (10, 12, 18))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except OSError:
        font = small = None
    draw.text((24, 20), title, fill="white", font=font)
    x = 24
    for name, im in thumbs:
        y = 72
        sheet.paste(im, (x, y))
        draw.text((x, y + im.height + 10), name, fill=(220, 225, 235), font=small)
        x += 380
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def write_report(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def scene_change_report(video_path: Path) -> dict:
    """Analyze rendered pacing using the installed PySceneDetect repository."""
    try:
        from scenedetect import ContentDetector, SceneManager, open_video
        video = open_video(str(video_path))
        manager = SceneManager()
        manager.add_detector(ContentDetector(threshold=20.0, min_scene_len=8))
        manager.detect_scenes(video)
        scenes = manager.get_scene_list(start_in_scene=True)
        cuts = []
        for start, end in scenes:
            cuts.append({
                "start": round(start.get_seconds(), 3),
                "end": round(end.get_seconds(), 3),
                "duration": round((end - start).get_seconds(), 3),
            })
        return {
            "available": True,
            "scene_count": len(cuts),
            "detected_scenes": cuts,
        }
    except Exception as exc:
        return {
            "available": False,
            "scene_count": 0,
            "error": str(exc)[:240],
        }


def unified_quality_report(report: dict) -> dict:
    """Combine renderer QA with Astra's creative director.

    This function is intentionally side-effect free. It returns the release
    decision plus a targeted repair plan for the orchestrator.
    """
    base = assess_render(report)
    merged = dict(report)
    hard = list(merged.get("hard_failures") or [])
    hard.extend(base.get("failures") or [])
    merged["hard_failures"] = hard
    decision = evaluate_director(merged)
    return {
        "render_assessment": base,
        "director": decision,
        "feedback": production_feedback(decision),
        "pass": bool(base.get("pass")) and bool(decision.get("publish_allowed")),
    }


def director_input_from_render(story: dict, render_report: dict) -> dict:
    """Translate Studio's real render telemetry into Creative Director inputs."""
    scenes = render_report.get("scenes") or []
    durations = [float(s.get("duration") or 0) for s in scenes if float(s.get("duration") or 0) > 0]
    duration = float(render_report.get("duration") or 0)
    cq = render_report.get("creative_quality") or {}
    audio = render_report.get("audio") or {}
    hook_words = len(str(story.get("hook") or "").split())
    first_start = float((scenes[0] if scenes else {}).get("start") or 0)

    hook_score = 94.0
    if hook_words > 10:
        hook_score -= min(30.0, (hook_words - 10) * 4.0)
    if first_start > 0.15:
        hook_score -= 20.0

    retention_score = 92.0
    if not 8.0 <= duration <= 28.0:
        retention_score -= 35.0
    if len(scenes) < 3:
        retention_score -= 25.0
    if durations and max(durations) > 4.5:
        retention_score -= min(25.0, (max(durations) - 4.5) * 8.0)

    peak = float(audio.get("peak_dbfs") or -99)
    audio_score = 94.0 if -12.0 <= peak <= -0.3 else 72.0

    visual_score = float(cq.get("score") or 0)
    novelty_score = min(100.0, visual_score + 4.0)
    coherence_score = 92.0 if all(str(s.get("speech") or s.get("narration") or "").strip() for s in scenes) else 70.0

    hard = list(cq.get("hard_failures") or [])
    return {
        "duration": duration,
        "scenes": scenes,
        "creative_quality": cq,
        "creative": {
            "hook_score": hook_score,
            "retention_score": retention_score,
            "visual_score": visual_score,
            "novelty_score": novelty_score,
            "coherence_score": coherence_score,
        },
        "scene_analysis": {
            "scene_count": len(scenes),
            "avg_scene_duration": (sum(durations) / len(durations)) if durations else 0.0,
            "max_scene_duration": max(durations) if durations else 0.0,
        },
        "audio": {"score": audio_score, **audio},
        # Studio captions are generated from the same timed narration plan.
        # A later faster-whisper/VideoLingo pass can replace this provisional score.
        "captions": {"score": 86.0, "stage": "studio-timing-provisional"},
        "technical": {"pass": duration > 0 and bool(scenes), "score": 100.0 if duration > 0 and scenes else 0.0},
        "hard_failures": hard,
    }


def evaluate_studio_render(story: dict, render_report: dict) -> dict:
    director_input = director_input_from_render(story, render_report)
    decision = evaluate_director(director_input)
    return {
        "director_input": director_input,
        "director": decision,
        "feedback": production_feedback(decision),
        "pass": bool(decision.get("publish_allowed")),
    }
