"""Optional OpenAI original-story ideation with explicit paid-API opt-in.

Default: no network calls, no charges. Every model-generated story must pass
the existing render/Creative Director/monetization QA gates.
"""
import json
import os
import re
import urllib.error
import urllib.request

VISUALS = {"planet", "robot", "signal", "ship", "forest", "door"}
ROLES = {"reveal", "build", "mechanism", "twist", "payoff"}


def enabled():
    return (os.getenv("ASTRA_OPENAI_ENABLED") == "1"
            and os.getenv("ASTRA_OPENAI_ALLOW_PAID_API") == "1"
            and bool(os.getenv("OPENAI_API_KEY")))


def generate(excluded_ids, excluded_titles):
    """Return a validated original microfiction story, or None when disabled."""
    if not enabled():
        return None
    model = os.getenv("ASTRA_OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", model):
        raise ValueError("Invalid configured OpenAI model")
    prompt = (
        "Create exactly one entirely original, emotionally engaging, family-safe "
        "vertical-video science-fiction microstory with 4 cinematic beats and a "
        "surprising but coherent ending. Avoid generic inspirational cliches, "
        "copyrighted characters, real news claims, and any existing titles or ideas. "
        "Return ONLY a JSON object with title, question, answer, and beats. "
        "Each beat has headline, speech, visual, label, story_beat. "
        "visual must be one of: planet, robot, signal, ship, forest, door. "
        "story_beat must be one of: reveal, build, mechanism, twist, payoff. "
        "Speech: 10-24 words per beat. Title under 75 characters. "
        "Exclude these titles: " + json.dumps(sorted(excluded_titles)[:60]) +
        ". Exclude these content IDs: " + json.dumps(sorted(excluded_ids)[:60])
    )
    payload = json.dumps({
        "model": model,
        "input": prompt,
        "max_output_tokens": 900,
        "text": {"format": {"type": "json_object"}},
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses", data=payload, method="POST",
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            raw = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("OpenAI creative request failed: " + type(exc).__name__) from exc
    if raw.get("status") != "completed":
        raise RuntimeError("OpenAI creative response incomplete")
    output = "".join(item.get("text", "")
                     for msg in raw.get("output", [])
                     for item in msg.get("content", [])
                     if item.get("type") == "output_text")
    data = json.loads(output)
    title = data.get("title")
    beats = data.get("beats")
    if (not isinstance(title, str) or not 8 <= len(title) <= 75
            or title.casefold().strip() in excluded_titles
            or not isinstance(beats, list) or len(beats) != 4):
        raise ValueError("Generated story title or beat count invalid")
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
    cid = "rayvan-openai-" + hashlib.sha256(
        (title.casefold().strip() + "|" + data["answer"].casefold().strip()).encode()
    ).hexdigest()[:20]
    if cid in excluded_ids:
        raise ValueError("Duplicate story content")
    return {
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
