"""Whole-story illustration requests. Prompts are direction, not visual approval."""
import hashlib
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def illustration_requests(story):
    """Keep narrative and supplied appearance bible identical across all shots.

    A missing bible is reported, never replaced with invented character details.
    Requests remain review-only until actual images pass continuity review.
    """
    identity = story.get("content_id")
    beats = story.get("story_beats")
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("Story identity required")
    if not isinstance(beats, list) or not beats:
        raise ValueError("Story beats required")
    if any(not isinstance(beat, dict) or not str(beat.get("speech", "")).strip()
           for beat in beats):
        raise ValueError("Every scene requires narrative action")
    bible = story.get("visual_bible") or {}
    if not isinstance(bible, dict):
        raise ValueError("visual_bible must be an object")
    context = {"content_id": identity, "title": story.get("title", ""),
               "visual_bible": bible,
               "story_cast": story.get("story_cast", []),
               "story_environment": story.get("story_environment", ""),
               "beats": beats}
    version = hashlib.sha256(canonical(context).encode()).hexdigest()
    requests = []
    for index, beat in enumerate(beats):
        scene_id = f"{index + 1:03d}"
        # Cloudflare FLUX accepts at most 2048 prompt characters. The previous
        # full-story-first layout silently dropped the selected scene, causing
        # different shots to depict the same action. Put scene action first.
        prompt = (
            "Create one original portrait story illustration. Show ONLY the selected "
            "scene action and characters, not other story events. No text, logos, "
            "labels, speech bubbles or panels. Keep faces, clothing, props and style "
            "consistent. "
            + "Story: " + str(story.get("title", "")) + ". Context ID: " + version[:16]
            + ". Scene " + scene_id + ": "
            + canonical({"action": beat.get("visual_prompt") or beat["speech"],
                         "narration": beat["speech"]})
            + " Visual bible: " + canonical(bible)
        )
        if len(prompt) > 2048:
            raise ValueError("Scene illustration prompt exceeds 2048 characters; "
                             "shorten visual direction or bible before generation")
        requests.append({"story_content_id": identity, "scene_id": scene_id,
                         "story_visual_sha256": version, "prompt": prompt,
                         "visual_bible_supplied": bool(bible),
                         "continuity_status": "not_verified"})
    return requests


def bind_reviewed_scenes(plan, content_id, manifest_path):
    """Bind every directed beat to its independently approved exact-scene art.

    Return a new plan; never accept partial coverage or a scene from another story.
    """
    from astra.asset_library import load_assets
    if not isinstance(content_id, str) or not content_id.strip() or not plan:
        raise ValueError("Story identity and nonempty directed plan required")
    assets = load_assets(manifest_path)
    bound = []
    for index, shot in enumerate(plan):
        scene_id = f"{index + 1:03d}"
        matches = [asset for asset in assets
                   if asset.get("story_content_id") == content_id
                   and asset.get("scene_id") == scene_id
                   and asset.get("category") == "background"
                   and asset.get("sha256")]
        if len(matches) != 1:
            raise ValueError(f"Missing or ambiguous approved illustration for scene {scene_id}")
        bound.append({**shot, "artwork_asset_id": matches[0]["id"],
                      "story_content_id": content_id, "scene_id": scene_id,
                      "artwork_manifest_path": str(manifest_path)})
    return bound
