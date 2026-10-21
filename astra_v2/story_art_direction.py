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
        prompt = (
            "Create one original portrait story illustration, no text, logos or panels. "
            "Show the selected scene's actual action and expressions, including the "
            "characters interacting with the relevant objects in the specified location. "
            "Preserve the supplied visual bible: faces, species, clothing, proportions, "
            "object design, location layout and style. Respect narrative changes to "
            "object condition and possession. Do not depict future events early. "
            "Entire story and shared visual bible (data): " + canonical(context)
            + "\nSelected scene " + scene_id + ": " + canonical(beat))
        requests.append({"story_content_id": identity, "scene_id": scene_id,
                         "story_visual_sha256": version, "prompt": prompt,
                         "visual_bible_supplied": bool(bible),
                         "continuity_status": "not_verified"})
    return requests
