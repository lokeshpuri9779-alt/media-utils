from __future__ import annotations

"""Experimental HyperFrames backend for Astra premium Shorts.

The story brain, source verification, media acquisition, narration and safety
gates remain Astra-owned. HyperFrames is used only as a deterministic visual
render backend. This keeps renderer choice replaceable.
"""

import argparse
import html
import json
import math
import shutil
from pathlib import Path

from astra_errors import CreativeReject
from premium_stories import catalog
from studio_renderer import (
    RATE,
    _repair_plan,
    acquire_story_media,
    asset_manifest,
    asset_resolution_gate,
    creative_quality_gate,
    make_plan,
    prepare_media_cache,
    resolve_assets,
    score_audio,
    voice_plan,
)

VERSION = "hyperframes-adapter-0.1"

THEMES = {
    "space": ("#070b17", "#221438", "#f5a253"),
    "current": ("#080d18", "#172a3d", "#55b6ff"),
    "tech": ("#07111b", "#112a35", "#43d0c0"),
    "fiction": ("#110817", "#32162c", "#df6c9e"),
    "football": ("#08130d", "#173322", "#74c98b"),
    "challenge": ("#0b0b12", "#25233a", "#f2c65c"),
}


def _esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _prepare_plan(story: dict, work: Path) -> tuple[list[dict], float, dict]:
    genre = str(story.get("genre") or "space")
    plan = make_plan(story)
    repair_attempts = 0
    while True:
        try:
            creative_quality_gate(story, plan)
            break
        except CreativeReject:
            if repair_attempts >= 2:
                raise
            repair_attempts += 1
            plan = _repair_plan(story, plan, repair_attempts)

    assets = asset_manifest(story, plan)
    resolved = prepare_media_cache(resolve_assets(assets))
    resolved = acquire_story_media(resolved)
    asset_report = asset_resolution_gate(resolved)

    if story.get("premium_story"):
        verified = sum(1 for x in resolved if x.get("provider") == "wikimedia-commons")
        required = sum(1 for x in resolved if x.get("strategy") == "external-verified")
        if not required or verified != required:
            raise CreativeReject(
                f"HyperFrames preflight rejected premium story: verified media {verified}/{required}"
            )
        asset_report["verified_subject_media"] = verified
        asset_report["required_subject_media"] = required

    for shot, item in zip(plan, resolved):
        shot["resolved_asset"] = item

    duration = voice_plan(
        plan,
        genre,
        max_duration=float(story.get("target_duration_max", 36)),
        voice_name=str(story.get("voice_profile") or "af_heart"),
        voice_speed=float(story.get("voice_speed") or 1.09),
    )
    audio = work / "mix.wav"
    audio_info = score_audio(plan, duration, genre, audio)
    return plan, duration, {"assets": asset_report, "audio": audio_info}


def _caption_clips(scene: dict, scene_index: int) -> tuple[list[str], list[str]]:
    words = str(scene.get("speech") or "").split()
    if not words:
        return [], []
    voice_len = len(scene["audio"]) / RATE
    start = float(scene["voice_start"])
    chunk_size = 5
    chunks = [words[i : i + chunk_size] for i in range(0, len(words), chunk_size)]
    total_words = max(1, len(words))
    cursor = start
    html_parts, tweens = [], []
    for idx, chunk in enumerate(chunks):
        share = max(0.32, voice_len * len(chunk) / total_words)
        remaining = start + voice_len - cursor
        dur = max(0.26, min(share, remaining if remaining > 0 else share))
        clip_id = f"cap-{scene_index}-{idx + 1}"
        text = _esc(" ".join(chunk))
        html_parts.append(
            f'<div class="clip caption-layer" id="{clip_id}" '
            f'data-start="{cursor:.3f}" data-duration="{dur:.3f}" data-track-index="4">'
            f'<div class="caption">{text}</div></div>'
        )
        tweens.append(
            f'tl.fromTo("#{clip_id} .caption", '
            '{opacity:0,y:20},{opacity:1,y:0,duration:0.16,ease:"power2.out"},'
            f'{cursor:.3f});'
        )
        cursor += dur
    return html_parts, tweens


def _media_visual(scene: dict, media_name: str, scene_index: int) -> str:
    labels = scene.get("comparison_labels") or []
    label_html = ""
    if len(labels) == 2:
        label_html = (
            '<div class="compare-label left">' + _esc(labels[0]) + '</div>'
            '<div class="compare-label right">' + _esc(labels[1]) + '</div>'
        )
    fit = "contain" if str(scene.get("media_fit") or "") in {"contain", "wide"} else "cover"
    return (
        '<div class="media-stage">'
        f'<img class="media" id="media-{scene_index}" src="media/{_esc(media_name)}" '
        f'alt="" style="object-fit:{fit}">'
        f'{label_html}</div>'
    )


def _tidal_lock_visual(scene_index: int) -> str:
    return f"""
<div class="diagram tidal">
  <div class="earth">EARTH</div>
  <div class="orbit-ring"></div>
  <div class="arm" id="moon-arm-{scene_index}">
    <div class="moon" id="moon-{scene_index}"><span class="marker"></span></div>
  </div>
  <div class="metric">1 ORBIT = 1 SPIN</div>
</div>
"""


def _iss_orbit_visual(scene_index: int) -> str:
    return f"""
<div class="diagram iss">
  <div class="earth">EARTH</div>
  <div class="orbit-ring"></div>
  <div class="arm" id="iss-arm-{scene_index}">
    <div class="station"><span></span><b></b><span></span></div>
  </div>
  <div class="metric">~90 MINUTES / ORBIT</div>
</div>
"""


def _fallback_visual(scene: dict) -> str:
    label = _esc(scene.get("label") or scene.get("headline") or "RAYVAN")
    sub = _esc(scene.get("sub") or "")
    return (
        '<div class="fallback-visual"><div class="orb"></div>'
        f'<div class="fallback-label">{label}</div>'
        f'<div class="fallback-sub">{sub}</div></div>'
    )


def _scene_html(scene: dict, idx: int, media_name: str | None) -> str:
    visual = str(scene.get("visual") or "")
    if visual == "media" and media_name:
        body = _media_visual(scene, media_name, idx)
    elif visual == "tidal_lock":
        body = _tidal_lock_visual(idx)
    elif visual == "iss_orbit":
        body = _iss_orbit_visual(idx)
    else:
        body = _fallback_visual(scene)
    start = float(scene["start"])
    duration = float(scene["duration"])
    headline = _esc(scene.get("headline") or "")
    return f"""
<section class="clip scene" id="scene-{idx}" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="1">
  <div class="scene-body">
    <div class="brand">RAYVAN</div>
    <div class="headline">{headline}</div>
    {body}
  </div>
</section>
"""


def _project_html(story: dict, plan: list[dict], duration: float, media_names: dict[int, str]) -> str:
    genre = str(story.get("genre") or "space")
    top, bottom, accent = THEMES.get(genre, THEMES["space"])
    scenes, captions, tweens = [], [], []

    for idx, scene in enumerate(plan, start=1):
        scenes.append(_scene_html(scene, idx, media_names.get(idx)))
        cap_html, cap_tweens = _caption_clips(scene, idx)
        captions.extend(cap_html)
        tweens.extend(cap_tweens)

        start = float(scene["start"])
        dur = float(scene["duration"])
        tweens.append(
            f'tl.fromTo("#scene-{idx} .scene-body",'
            '{opacity:0,y:28},{opacity:1,y:0,duration:0.22,ease:"power2.out"},'
            f'{start:.3f});'
        )
        if scene.get("visual") == "media" and media_names.get(idx):
            scale_to = 1.09 if str(scene.get("media_motion") or "") == "push" else 1.035
            tweens.append(
                f'tl.fromTo("#media-{idx}",{{scale:1.01}},'
                f'{{scale:{scale_to:.3f},duration:{dur:.3f},ease:"none"}},{start:.3f});'
            )
        elif scene.get("visual") == "tidal_lock":
            tweens.append(
                f'tl.fromTo("#moon-arm-{idx}",{{rotation:0}},'
                f'{{rotation:360,duration:{dur:.3f},ease:"none"}},{start:.3f});'
            )
            tweens.append(
                f'tl.fromTo("#moon-{idx}",{{rotation:0}},'
                f'{{rotation:-360,duration:{dur:.3f},ease:"none"}},{start:.3f});'
            )
        elif scene.get("visual") == "iss_orbit":
            tweens.append(
                f'tl.fromTo("#iss-arm-{idx}",{{rotation:-60}},'
                f'{{rotation:300,duration:{dur:.3f},ease:"none"}},{start:.3f});'
            )

    tween_script = "\n      ".join(tweens)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1080, height=1920">
  <title>{_esc(story.get("title") or "RAYVAN")}</title>
  <script src="./gsap.min.js"></script>
  <style>
    html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:{top};color:white;font-family:sans-serif}}
    #root{{position:relative;width:100%;height:100%;overflow:hidden;background:
      radial-gradient(circle at 70% 34%,color-mix(in srgb,{accent} 13%,transparent),transparent 42%),
      linear-gradient(180deg,{top} 0%,{bottom} 100%)}}
    .clip{{position:absolute;inset:0}}
    .scene{{overflow:hidden}}
    .scene-body{{position:absolute;inset:0}}
    .brand{{position:absolute;left:68px;top:96px;font-size:22px;font-weight:700;letter-spacing:1.5px;color:#d7ddec}}
    .headline{{position:absolute;z-index:8;left:68px;right:68px;top:170px;font-size:50px;line-height:1.05;font-weight:850;letter-spacing:.2px}}
    .media-stage{{position:absolute;left:34px;right:34px;top:465px;height:820px;display:flex;align-items:center;justify-content:center;overflow:hidden}}
    .media{{width:100%;height:100%;display:block;transform-origin:50% 50%}}
    .compare-label{{position:absolute;bottom:22px;font-size:23px;font-weight:800;color:#d7ddec;letter-spacing:1px}}
    .compare-label.left{{left:23%}} .compare-label.right{{right:23%}}
    .caption-layer{{display:flex;align-items:flex-end;justify-content:center;padding-bottom:330px;box-sizing:border-box;pointer-events:none}}
    .caption{{max-width:720px;background:#070b15e8;border:1px solid #ffffff14;border-radius:20px;padding:17px 30px;font-size:40px;line-height:1.12;font-weight:800;text-align:center;box-shadow:0 16px 45px #0008}}
    .diagram{{position:absolute;left:90px;right:90px;top:430px;height:900px}}
    .diagram .earth{{position:absolute;left:50%;top:46%;width:210px;height:210px;margin:-105px;border-radius:50%;display:grid;place-items:center;background:#3978ad;border:4px solid #a8dcff;font-size:29px;font-weight:800;box-shadow:0 0 90px #4d9ed944}}
    .orbit-ring{{position:absolute;left:50%;top:46%;width:720px;height:520px;margin-left:-360px;margin-top:-260px;border:4px solid #7d86a866;border-radius:50%}}
    .arm{{position:absolute;left:50%;top:46%;width:720px;height:1px;margin-left:-360px;transform-origin:360px 0}}
    .moon{{position:absolute;right:-56px;top:-56px;width:112px;height:112px;border-radius:50%;background:#c8ced8;border:3px solid #fff;display:grid;place-items:center}}
    .marker{{display:block;width:17px;height:17px;border-radius:50%;background:{accent};position:absolute;left:10px;top:45px;box-shadow:0 0 18px {accent}}}
    .station{{position:absolute;right:-94px;top:-24px;width:188px;height:48px;display:flex;align-items:center;justify-content:center;gap:8px}}
    .station b{{display:block;width:74px;height:32px;background:#e0e5ed;border-radius:8px}}
    .station span{{display:block;width:48px;height:22px;background:#4c82cf}}
    .metric{{position:absolute;left:50%;top:78%;transform:translateX(-50%);background:#070b15e8;border-radius:22px;padding:17px 30px;font-size:34px;font-weight:850;white-space:nowrap}}
    .fallback-visual{{position:absolute;left:100px;right:100px;top:500px;height:720px;display:flex;flex-direction:column;align-items:center;justify-content:center}}
    .orb{{width:360px;height:360px;border-radius:50%;background:radial-gradient(circle at 35% 28%,#fff8,{accent} 25%,#18243e 72%);box-shadow:0 0 110px {accent}44}}
    .fallback-label{{margin-top:42px;font-size:46px;font-weight:850;text-align:center}}
    .fallback-sub{{margin-top:12px;font-size:28px;color:#c8d1e2;text-align:center}}
  </style>
</head>
<body>
<div id="root" data-composition-id="rayvan" data-start="0" data-width="1080" data-height="1920" data-duration="{duration:.3f}" data-fps="30">
  {''.join(scenes)}
  {''.join(captions)}
  <audio id="astra-mix" src="mix.wav" data-start="0" data-duration="{duration:.3f}" data-track-index="3" data-volume="1"></audio>
</div>
<script>
  const tl = gsap.timeline({{paused:true}});
  {tween_script}
  window.__timelines["rayvan"] = tl;
</script>
</body>
</html>
"""


def build_project(story: dict, root: Path, gsap_source: Path | None = None) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    media_dir = root / "media"
    media_dir.mkdir(exist_ok=True)

    plan, duration, prep = _prepare_plan(story, root)
    media_names: dict[int, str] = {}
    provenance = []
    for idx, scene in enumerate(plan, start=1):
        item = scene.get("resolved_asset") or {}
        src = Path(str(item.get("cache_image") or ""))
        if scene.get("visual") == "media" and item.get("provider") == "wikimedia-commons":
            if not src.exists():
                raise CreativeReject(f"Verified media cache missing for scene {idx}: {src}")
            name = f"scene-{idx}{src.suffix or '.png'}"
            shutil.copy2(src, media_dir / name)
            media_names[idx] = name
        provenance.append({
            "scene": idx,
            "visual": scene.get("visual"),
            "provider": item.get("provider"),
            "license": item.get("license"),
            "source_url": item.get("source_url"),
            "license_url": item.get("license_url"),
            "commons_title": item.get("commons_title"),
        })

    if gsap_source:
        if not gsap_source.exists():
            raise FileNotFoundError(gsap_source)
        shutil.copy2(gsap_source, root / "gsap.min.js")

    index = _project_html(story, plan, duration, media_names)
    (root / "index.html").write_text(index, encoding="utf-8")
    report = {
        "adapter": VERSION,
        "content_id": story.get("content_id"),
        "title": story.get("title"),
        "duration": round(duration, 3),
        "scene_count": len(plan),
        "provenance": provenance,
        "prep": prep,
    }
    (root / "astra-project.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--gsap", type=Path)
    parser.add_argument("--story-id")
    args = parser.parse_args()

    stories = [x for x in catalog() if x.get("production_ready")]
    if args.story_id:
        stories = [x for x in stories if x.get("content_id") == args.story_id]
    if not stories:
        raise RuntimeError("No matching production-ready premium stories.")

    summary = []
    for story in stories:
        folder = args.batch_root / str(story["content_id"])
        summary.append(build_project(story, folder, gsap_source=args.gsap))
    args.batch_root.mkdir(parents=True, exist_ok=True)
    (args.batch_root / "batch.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
