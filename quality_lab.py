from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from creative_director import evaluate as evaluate_director, production_feedback
from output_contract import validate_output_contract


def structural_quality_penalties(report: dict) -> dict:
    """Cheap deterministic QA from the render plan before heavier media analysis."""
    scenes=report.get("scenes") or []
    penalties=[]
    score=100.0

    genre = str(report.get("genre") or "").lower()
    narrative = genre in {"fiction", "suspense", "thriller", "microfiction"}
    durations=[float(s.get("duration") or 0) for s in scenes if float(s.get("duration") or 0)>0]
    if durations:
        longest=max(durations)
        if not narrative and longest>4.8:
            p=min(18.0,(longest-4.8)*6.0)
            score-=p; penalties.append({"type":"static-shot","points":round(p,2),"detail":f"longest scene {longest:.2f}s"})
        spread=max(durations)-min(durations)
        if not narrative and len(durations)>=4 and spread<0.35:
            score-=8.0; penalties.append({"type":"uniform-pacing","points":8.0,"detail":"scene durations are too uniform"})

    signatures=[]
    for s in scenes:
        signatures.append((
            str(s.get("visual") or ""),
            str(s.get("media_fit") or ""),
            str(s.get("treatment") or ""),
        ))
    if signatures and len(set(signatures)) <= max(1,len(signatures)//2):
        score-=12.0; penalties.append({"type":"visual-diversity","points":12.0,"detail":"too few distinct scene treatments"})

    text_over=0
    for s in scenes:
        words=len(str(s.get("headline") or "").split())
        if words>8:
            text_over += words-8
    if text_over:
        p=min(12.0,text_over*1.5)
        score-=p; penalties.append({"type":"text-density","points":round(p,2),"detail":f"{text_over} headline words above limit"})

    preflight=report.get("scene_preflight") or {}
    warnings=preflight.get("warnings") or []
    low_res=sum("low_resolution" in str(x) for x in warnings)
    repetitive=sum("repetitive_scene_signature" in str(x) for x in warnings)
    if low_res:
        p=min(15.0,low_res*7.5)
        score-=p; penalties.append({"type":"source-quality","points":p,"detail":f"{low_res} low-resolution scene(s)"})
    if repetitive:
        p=min(15.0,repetitive*7.5)
        score-=p; penalties.append({"type":"repetition","points":p,"detail":f"{repetitive} repetitive scene signature(s)"})

    hook=str((scenes[0] if scenes else {}).get("headline") or "")
    hook_words=len(hook.split())
    if hook_words>9:
        p=min(12.0,(hook_words-9)*2.0)
        score-=p; penalties.append({"type":"hook-legibility","points":p,"detail":f"hook has {hook_words} words"})

    layout=report.get("layout_qa") or {}
    if layout and not layout.get("safe_area_pass",False):
        score-=20.0; penalties.append({"type":"safe-area","points":20.0,"detail":"caption/headline safe-area validation failed"})

    # Contain-framed extreme aspect ratios can leave too much unused canvas.
    preflight_scenes=(report.get("scene_preflight") or {}).get("scenes") or []
    empty_risk=0
    for row in preflight_scenes:
        ratio=float(row.get("aspect_ratio") or 0)
        fit=str(row.get("media_fit") or "")
        if fit in {"contain","wide"} and ratio and (ratio>1.95 or ratio<0.62):
            empty_risk += 1
    if empty_risk:
        p=min(15.0,empty_risk*5.0)
        score-=p; penalties.append({"type":"empty-space","points":p,"detail":f"{empty_risk} scene(s) risk excessive letterbox/pillarbox space"})

    return {"score":round(max(0.0,score),2),"penalties":penalties,"pass":score>=78.0}


def assess_render(report: dict) -> dict:
    failures = []
    duration = float(report.get("duration") or 0)
    scenes = report.get("scenes") or []
    cq = report.get("creative_quality") or {}
    assets = cq.get("asset_resolution") or {}
    if len(scenes) < 3:
        failures.append("too few scenes")
    if cq.get("score", 100) < 76:
        failures.append("creative quality score below gate")
    required = int(assets.get("required_subject_media") or 0)
    verified = int(assets.get("verified_subject_media") or 0)
    if required and verified != required:
        failures.append(f"verified editorial media {verified}/{required}")

    structural = structural_quality_penalties(report)
    if not structural["pass"]:
        failures.append(f"structural visual quality below gate: {structural['score']:.1f}")

    output_contract = validate_output_contract(report)
    if not output_contract["pass"]:
        failures.extend("output-contract:" + x for x in output_contract["failures"])
    peak=float((report.get("audio") or {}).get("peak_dbfs") or -99)
    if peak > -0.2 or peak < -15.0:
        failures.append(f"audio peak outside target window: {peak:.2f} dBFS")

    return {
        "pass": not failures,
        "failures": failures,
        "duration": duration,
        "structural_quality": structural,
        "output_contract": output_contract,
    }


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


def director_input_from_render(story: dict, render_report: dict, media_qa: dict | None = None, detected: dict | None = None, identity: dict | None = None) -> dict:
    """Translate Studio's real render telemetry into Creative Director inputs."""
    scenes = render_report.get("scenes") or []
    durations = [float(s.get("duration") or 0) for s in scenes if float(s.get("duration") or 0) > 0]
    if detected and detected.get("available") and detected.get("detected_scenes"):
        raw_detected = [float(s.get("duration") or 0) for s in detected["detected_scenes"] if float(s.get("duration") or 0) > 0]
        planned_count = len(durations)
        detected_count = len(raw_detected)
        # Smooth editorial animation often has no hard pixel discontinuity, so
        # PySceneDetect can collapse a real 7–8 beat edit into one long scene.
        # Treat detector output as authoritative only when it captures enough of
        # the renderer's explicit timeline to be a credible pacing measurement.
        min_credible = max(2, int(math.ceil(planned_count * 0.50))) if planned_count else 2
        detected_reliable = detected_count >= min_credible
        detected_durations = raw_detected if detected_reliable else []
    else:
        raw_detected = []
        detected_reliable = False
        detected_durations = []
    duration = float(render_report.get("duration") or 0)
    visual_edit = render_report.get("visual_edit") or {}
    visual_scene_count = int(visual_edit.get("visual_scene_count") or 0)
    visual_scene_rate = float(visual_edit.get("visual_scene_rate_per_second") or 0)
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
    if len(scenes) < 3:
        retention_score -= 25.0
    # Narrative retention cannot be inferred from shot length alone.
    # Keep duration and missing-story-beat checks; use measured audience
    # analytics separately rather than inventing retention from cut frequency.
    narrative_genre = str(story.get("genre") or "").lower() in {
        "fiction", "microfiction", "suspense", "thriller"}
    if durations and not narrative_genre and max(durations) > 4.5:
        retention_score -= min(25.0, (max(durations) - 4.5) * 8.0)

    peak = float(audio.get("peak_dbfs") or -99)
    audio_score = 94.0 if -12.0 <= peak <= -0.3 else 72.0
    caption_score = 86.0
    caption_stage = "studio-timing-provisional"
    if media_qa and media_qa.get("available"):
        audio_score = float(media_qa.get("audio_score") or 0)
        caption_score = float(media_qa.get("caption_score") or 0)
        caption_stage = "measured-post-render"

    visual_score = float(cq.get("score") or 0)
    novelty_score = float((identity or {}).get("novelty_score") if identity else min(100.0, visual_score + 4.0))
    coherence_score = 92.0 if all(str(s.get("speech") or s.get("narration") or "").strip() for s in scenes) else 70.0

    hard = list(cq.get("hard_failures") or [])
    if media_qa:
        hard.extend(media_qa.get("hard_failures") or [])
        if media_qa.get("pass") is False:
            hard.append("post_render_media_validation_failed")
    if identity and not identity.get("pass", True):
        hard.append("creative identity too similar to a recent upload")
    if visual_scene_count > 0 and 1.0 <= visual_scene_rate <= 2.0:
        effective_scene_count = visual_scene_count
        effective_avg = duration / visual_scene_count if duration else 0.0
        effective_max = float(visual_edit.get("micro_scene_seconds") or effective_avg)
        pacing_source = "studio-micro-edit"
    else:
        effective_scene_count = len(detected_durations) if detected_durations else len(scenes)
        effective_avg = (sum(detected_durations) / len(detected_durations)) if detected_durations else ((sum(durations) / len(durations)) if durations else 0.0)
        effective_max = max(detected_durations) if detected_durations else (max(durations) if durations else 0.0)
        pacing_source = "pyscenedetect" if detected_durations else "studio-plan"

    return {
        "genre": ("suspense" if str(story.get("genre") or "").lower() in ("suspense", "thriller") else "fiction" if str(story.get("genre") or "").lower() in ("fiction", "microfiction") else str(story.get("genre") or "default").lower()),
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
            "scene_count": effective_scene_count,
            "avg_scene_duration": effective_avg,
            "max_scene_duration": effective_max,
            "source": pacing_source,
            "visual_scene_rate_per_second": visual_scene_rate,
            "target_scene_rate_range": visual_edit.get("target_scene_rate_range"),
            "detector_reliable": detected_reliable,
            "detected_scene_count_raw": len(raw_detected),
            "planned_scene_count": len(scenes),
        },
        "audio": {"score": audio_score, **audio, "media_qa": media_qa or {}},
        "captions": {"score": caption_score, "stage": caption_stage, "media_qa": media_qa or {}},
        "technical": {"pass": duration > 0 and bool(scenes), "score": 100.0 if duration > 0 and scenes else 0.0},
        "hard_failures": hard,
    }


def evaluate_studio_render(story: dict, render_report: dict, video_path: str | Path | None = None) -> dict:
    detected = scene_change_report(Path(video_path)) if video_path else None
    from creative_identity import fingerprint_from_scenes, identity_gate
    fingerprint = fingerprint_from_scenes(render_report.get("scenes") or [])
    identity = identity_gate(fingerprint, story.get("recent_creative_fingerprints") or [])
    media_qa = None
    if video_path:
        try:
            from caption_audio_qa import validate_rendered_media
            media_qa = validate_rendered_media(video_path, render_report)
        except Exception as exc:
            media_qa = {
                "available": False,
                "pass": False,
                "audio_score": 0.0,
                "caption_score": 0.0,
                "hard_failures": ["post-render media QA unavailable: " + str(exc)[:180]],
            }
    director_input = director_input_from_render(story, render_report, media_qa=media_qa, detected=detected, identity=identity)
    decision = evaluate_director(director_input)
    # A high creative score cannot override physically competing subject
    # animations or missing safe-zone evidence. Require the compositor's
    # independent contract on every Studio production render.
    layer_qa=render_report.get("layer_qa") or {}
    if str(render_report.get("renderer") or "").startswith("studio") and layer_qa.get("pass") is not True:
        decision=dict(decision)
        decision["publish_allowed"]=False
        decision["action"]="rebuild_or_block"
        decision["layer_collision_reasons"]=layer_qa.get("failures") or ["layer_contract_missing"]
    return {
        "layer_qa": layer_qa,
        "director_input": director_input,
        "scene_detection": detected,
        "media_qa": media_qa,
        "creative_fingerprint": fingerprint,
        "creative_identity": identity,
        "director": decision,
        "feedback": production_feedback(decision),
        "pass": bool(decision.get("publish_allowed")),
    }


def evaluate_long_render(render_report: dict, video_path: str | Path) -> dict:
    """Measured QA for long-form renders without Shorts-specific duration rules."""
    path = Path(video_path)
    detected = scene_change_report(path)
    try:
        from caption_audio_qa import validate_rendered_media
        media_qa = validate_rendered_media(path, render_report)
    except Exception as exc:
        media_qa = {
            "available": False,
            "pass": False,
            "audio_score": 0.0,
            "caption_score": 0.0,
            "hard_failures": ["post-render media QA unavailable: " + str(exc)[:180]],
        }

    duration = float(render_report.get("duration") or 0)
    scene_count = int(render_report.get("scene_count") or len(render_report.get("scenes") or []))
    failures = list(media_qa.get("hard_failures") or [])
    if duration < 60:
        failures.append("long-form render is under 60 seconds")
    if scene_count < 6:
        failures.append("long-form render has too few scenes")
    if not path.is_file() or path.stat().st_size <= 0:
        failures.append("long-form output file missing or empty")

    structural_score = 100.0
    if duration < 120:
        structural_score -= 15.0
    if scene_count < 10:
        structural_score -= 10.0
    score = round(
        0.4 * float(media_qa.get("audio_score") or 0)
        + 0.4 * float(media_qa.get("caption_score") or 0)
        + 0.2 * structural_score,
        2,
    )
    return {
        "pass": not failures and score >= 82.0,
        "score": score,
        "media_qa": media_qa,
        "scene_detection": detected,
        "duration": duration,
        "scene_count": scene_count,
        "failures": failures,
    }
