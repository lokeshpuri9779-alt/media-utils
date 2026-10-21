"""Convert a review storyboard into the existing Studio renderer story contract.

Never approves a story, downloads a new voice engine, or publishes to YouTube.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from astra.background_factory import SCENES
from astra.asset_library import load_assets


def build_story(path, artwork_manifest=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("title"), str):
        raise ValueError("invalid_story_title")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not 3 <= len(scenes) <= 12:
        raise ValueError("invalid_story_scene_count")
    approved = {}
    if artwork_manifest is not None:
        approved = {str(a['id']): a for a in load_assets(artwork_manifest)
                    if a.get('category') == 'background'}
    beats = []
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise ValueError("invalid_story_scene")
        background = scene.get("background")
        caption = scene.get("caption")
        narration = scene.get("narration")
        if background not in SCENES:
            raise ValueError("unknown_story_background")
        if not isinstance(caption, str) or not 2 <= len(caption.strip()) <= 100:
            raise ValueError("invalid_story_caption")
        if not isinstance(narration, str) or not 10 <= len(narration.strip()) <= 500:
            raise ValueError("invalid_story_narration")
        if artwork_manifest is not None and background not in approved:
            raise ValueError("story_background_not_approved_or_missing")
        beats.append({"headline": caption.strip(), "speech": narration.strip(),
                      "visual": "forest" if "forest" in background else "signal",
                      "visual_prompt": background.replace("-", " "),
                      "label": caption.strip(), "story_beat": (
                          "reveal" if index == 0 else "payoff" if index == len(scenes)-1 else "build"),
                      "duration": 2.1,
                      **({"artwork_manifest_path": str(Path(artwork_manifest).resolve())}
                         if artwork_manifest is not None else {})})
    title = data["title"].strip()
    if not 8 <= len(title) <= 75:
        raise ValueError("invalid_story_title")
    digest = hashlib.sha256(json.dumps(beats, sort_keys=True).encode()).hexdigest()[:20]
    return {"genre": "fiction", "kind": "microfiction", "title": title,
            "content_id": "astra-artwork-review-" + digest,
            "hook": beats[0]["headline"], "question": beats[0]["speech"],
            "answer": beats[-1]["speech"], "story_beats": beats,
            "production_ready": False, "review_status": "pending_review",
            "source": "astra.artwork_story_bridge"}


def render_review(path, output, artwork_manifest=None):
    """Reuse production Kokoro voice and Studio animation; output is review-only."""
    story = build_story(path, artwork_manifest=artwork_manifest)
    if story["production_ready"] or story["review_status"] != "pending_review":
        raise ValueError("review_story_must_remain_unapproved")
    from studio_renderer import render_short
    return render_short(story, Path(output))
