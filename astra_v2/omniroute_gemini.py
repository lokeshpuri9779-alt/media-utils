"""Free-tier Gemini provider for ASTRA OmniRoute. No billing enablement or paid fallback."""
import json
import os
import re
import urllib.error
import urllib.request

from astra_v2.openai_creative import VISUALS, ROLES


def enabled():
    return os.getenv("ASTRA_GEMINI_ENABLED") == "1" and bool(os.getenv("GEMINI_API_KEY"))


def generate(excluded_ids, excluded_titles, prior_stories=(), premise=None):
    if not enabled():
        return None
    model = os.getenv("ASTRA_GEMINI_MODEL", "gemini-3.1-flash-lite")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", model):
        raise ValueError("Invalid Gemini model")
    prompt = (
        "Write one genuinely original, coherent, family-safe science-fiction short "
        "with four cinematic story beats, causal progression and an unexpected ending. "
        "Return only JSON keys title, question, answer, beats. Each beat must have "
        "headline, speech, visual, label, story_beat. Speech 12-24 words in every beat (at least 48 words total); use at least three distinct visual types across the four beats; "
        "visual one of planet, robot, signal, ship, forest, door; story_beat one "
        "of reveal, build, mechanism, twist, payoff. "
        "Use story_beat reveal for beat one and payoff for beat four; "
        "beats two and three must be build, mechanism or twist. "
        "Title 8-75 characters. "
        "Avoid recycled plots, copyrighted characters and these prior titles: "
        + json.dumps(sorted(excluded_titles)[:100]) + "."
    )
    if premise is not None:
        if not isinstance(premise, dict) or premise.get("production_ready") is not False or premise.get("review_status") != "awaiting_editorial_review":
            raise ValueError("Premise must be an unapproved editorial-review candidate")
        beats = premise.get("story_beats")
        if not isinstance(beats, list) or len(beats) != 4 or any(not isinstance(x, str) or len(x) > 500 for x in beats):
            raise ValueError("Invalid premise beats")
        guidance = json.dumps({"premise_key": premise.get("premise_key"), "beats": beats}, ensure_ascii=False)
        if len(guidance) > 2600:
            raise ValueError("Premise exceeds prompt limit")
        prompt += (" Use this unapproved premise only as inspiration; independently rewrite "
                   "all dialogue, character decisions, setting details, causal mechanism and ending. "
                   "Do not copy its narration or claim approval. Premise: " + guidance)
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json",
                             "temperature": 0.9, "maxOutputTokens": 1500}}).encode()
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
        data=body, method="POST", headers={
            "x-goog-api-key": os.environ["GEMINI_API_KEY"],
            "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Gemini HTTP " + str(exc.code)) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Gemini transport failed: " + type(exc).__name__) from exc
    candidates = result.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini returned no candidates")
    if candidates[0].get("finishReason") not in (None, "STOP"):
        raise ValueError("Gemini response incomplete")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    data = json.loads("".join(part.get("text", "") for part in parts))
    title = data.get("title")
    beats = data.get("beats")
    if (not isinstance(title, str) or not 8 <= len(title) <= 75
            or title.casefold().strip() in excluded_titles
            or not isinstance(beats, list) or len(beats) != 4):
        raise ValueError("Generated story title or beat count invalid")
    from astra_v2.omniroute import validate_beat_quality
    validate_beat_quality(beats, "Gemini")
    for beat in beats:
        if not isinstance(beat, dict):
            raise ValueError("Invalid beat")
        for key in ("headline", "speech", "label"):
            if not isinstance(beat.get(key), str) or not 2 <= len(beat[key]) <= 220:
                raise ValueError("Invalid beat text")
        if beat.get("visual") not in VISUALS or beat.get("story_beat") not in ROLES:
            raise ValueError("Invalid beat visual or narrative role")
    for key in ("question", "answer"):
        if not isinstance(data.get(key), str) or not 8 <= len(data[key]) <= 400:
            raise ValueError("Invalid story summary")
    import hashlib
    cid = "rayvan-gemini-" + hashlib.sha256(
        (title.casefold().strip() + "|" + data["answer"].casefold().strip()).encode()
    ).hexdigest()[:20]
    if cid in excluded_ids:
        raise ValueError("Duplicate story content")
    from astra_v2.shorts_novelty import is_near_duplicate
    from astra_v2.story_planning import planning_issues
    story = {
        "genre": "fiction", "kind": "microfiction",
        "production_ready": True, "content_id": cid,
        "title": title, "hook": beats[0]["headline"],
        "question": data["question"], "answer": data["answer"],
        "source": "", "keywords": ["original science fiction", "short story"],
        "story_beats": [
            {**beat, "sub": "AN ORIGINAL RAYVAN STORY", "duration": 2.1}
            for beat in beats
        ],
    }
    # Model generation is not an originality guarantee. Validate the full
    # narration and reject known published/pending/reserved narratives.
    from astra_v2.story_forge import plot_fingerprint
    story["plot_fingerprint"] = plot_fingerprint([
        ("", beat["speech"], "", "") for beat in story["story_beats"]
    ])
    if planning_issues(story):
        raise ValueError("Generated story failed causal planning")
    from astra_v2.story_editorial import editorial_issues
    editorial = editorial_issues(story, prior_stories)
    if editorial:
        raise ValueError("Generated story failed editorial review: " + ",".join(editorial))
    if is_near_duplicate(story, prior_stories):
        raise ValueError("Generated story repeats narrative history")
    return story
