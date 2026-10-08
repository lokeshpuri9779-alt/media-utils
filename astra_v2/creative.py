"""Reusable Creative Director adapter and independent video integrity gate."""
import json
import subprocess


class CreativeSkip(Exception):
    """No sufficiently good original candidate is available in this slot."""


def inspect_video(path):
    if not path.is_file() or path.stat().st_size < 30_000:
        raise CreativeSkip("missing_or_tiny_video")
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=35, check=False,
    )
    if proc.returncode:
        raise CreativeSkip("ffprobe_decode_failed")
    data = json.loads(proc.stdout)
    video = next((x for x in data.get("streams", []) if x.get("codec_type") == "video"), {})
    audio = next((x for x in data.get("streams", []) if x.get("codec_type") == "audio"), {})
    width, height = int(video.get("width") or 0), int(video.get("height") or 0)
    seconds = float((data.get("format") or {}).get("duration") or 0)
    if not (8 <= seconds <= 180 and width >= 360 and height >= 640 and height > width and audio):
        raise CreativeSkip("short_must_have_portrait_video_audio_and_8_to_180_seconds")
    return {"seconds": round(seconds, 2), "size": path.stat().st_size,
            "width": width, "height": height}


def make_candidate(path, excluded_ids, excluded_titles):
    import cloud_once as legacy
    from ypp_safety import enforce
    # First use original curated premium stories; only fall back to the
    # broader learned idea engine if none passes every existing quality gate.
    from premium_stories import catalog as prior_catalog
    from astra_v2.original_stories import catalog as original_catalog
    from studio_renderer import render_short
    from quality_lab import evaluate_studio_render
    premium_stories = original_catalog() + prior_catalog()
    print("Premium pool:", len(premium_stories), "seen IDs:", len(excluded_ids),
          "seen titles:", len(excluded_titles))
    for story in premium_stories:
        if not (story.get("production_ready") or story.get("validation_candidate")):
            continue
        if story["content_id"] in excluded_ids or story["title"].casefold().strip() in excluded_titles:
            continue
        try:
            rendered = render_short(story, path)
            evaluation = evaluate_studio_render(story, rendered, video_path=path)
            if not evaluation.get("pass"):
                print("Premium QA rejected:", story["content_id"],
                      (evaluation.get("director") or {}).get("action"))
                continue
            legacy.CONTENT_META = {
                "genre": story["genre"], "content_id": story["content_id"],
                "source": story.get("source"), "creative_director": evaluation["director"],
                "renderer": rendered.get("renderer"), "format": "short",
            }
            title = story["title"]
            if story["genre"] == "fiction":
                attribution = "\nOriginal fictional story. No real person or event is depicted."
            else:
                attribution = "\nSource: " + story.get("source", "")
            description = (story["question"] + "\n" + story["answer"]
                + attribution
                + "\nOriginal visuals; AI-assisted synthetic narration. #Shorts"
                + "\nSubscribe: https://www.youtube.com/channel/" + legacy.expected_channel_id())
            break
        except Exception as exc:
            print("Premium candidate rejected:", story.get("content_id"), type(exc).__name__)
    else:
        try:
            title, description = legacy.make_short(
                path, excluded_ids=excluded_ids, excluded_titles=excluded_titles)
        except RuntimeError as exc:
            message = str(exc).lower()
            if any(word in message for word in (
                "quality", "creative", "novelty", "fresh", "no candidates", "weak",
            )):
                raise CreativeSkip(str(exc)[:250]) from exc
            raise
    meta = dict(legacy.CONTENT_META)
    content_id = str(meta.get("content_id") or "").strip()
    if not (title and description and content_id):
        raise CreativeSkip("missing_story_identity_or_script")
    # A previous legacy-loop edge case could return its final rejected render.
    # V2 independently checks the final Creative Director decision.
    director = meta.get("creative_director") or {}
    if not director or not director.get("publish_allowed", False):
        raise CreativeSkip("creative_director_did_not_approve")
    if meta.get("genre") in {"space", "tech", "football", "current"} and not meta.get("source"):
        raise CreativeSkip("unsourced_factual_claim")
    if meta.get("copyright_unlicensed") or meta.get("reused_third_party_media"):
        raise CreativeSkip("unlicensed_material_flagged")
    verdict = enforce(title, description, meta, legacy.load_performance())
    if verdict.get("pass") is False:
        raise CreativeSkip("monetization_safety_rejected")
    media = inspect_video(path)
    synthetic = bool(verdict.get("ai_disclosure_required"))
    return {"title": title, "description": description, "content_id": content_id,
            "media": media, "synthetic": synthetic,
            "genre": str(meta.get("genre") or "")}
