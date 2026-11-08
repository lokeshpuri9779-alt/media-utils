"""Optional OpenAI original-story ideation with explicit paid-API opt-in.

Default: no network calls, no charges. Every model-generated story must pass
the existing render/Creative Director/monetization QA gates.
"""
import json
import os
import re
import urllib.error
import urllib.request
from astra_v2.spending_policy import paid_openai_allowed, assert_no_paid_api
from astra_v2.visual_artifact_library import SCENES

# These are the animal subjects the current Studio character renderer supports.
# A visual tag identifies the depicted actor, not an arbitrary scene symbol.
VISUALS = {"fox", "owl", "duck", "squirrel", "mouse", "mole", "otter",
           "beaver", "penguin", "heron", "crab", "firefly", "cat", "dog",
           "monkey", "bird", "rabbit", "whale"}
ROLES = {"reveal", "build", "mechanism", "twist", "payoff"}


def visual_subject_matches(visual, visual_prompt):
    """Require the visual label's supported animal to appear in the shot prompt."""
    from astra_v2.story_visuals import SUBJECTS
    pattern = dict(SUBJECTS).get(visual)
    return bool(pattern and isinstance(visual_prompt, str)
                and re.search(pattern, visual_prompt, re.I))


def enabled():
    return (paid_openai_allowed()
            and os.getenv("ASTRA_OPENAI_ENABLED") == "1"
            and os.getenv("ASTRA_OPENAI_ALLOW_PAID_API") == "1"
            and bool(os.getenv("OPENAI_API_KEY")))


def generate(excluded_ids, excluded_titles, prior_stories=()):
    """Return a validated original microfiction story, or None when disabled."""
    if not enabled():
        return None
    assert_no_paid_api()
    model = os.getenv("ASTRA_OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", model):
        raise ValueError("Invalid configured OpenAI model")
    prompt = (
        "Create exactly one entirely original, emotionally engaging, family-safe "
        "vertical-video science-fiction microstory with 4 cinematic beats and a "
        "surprising but coherent ending. Avoid generic inspirational cliches, "
        "copyrighted characters, real news claims, and any existing titles or ideas. "
        "Return ONLY a JSON object with title, question, answer, and beats. "
        "Each beat has headline, speech, visual, visual_prompt, story_environment, label, story_beat. "
        "Use only animal protagonists supported by the Studio cast; no humans, humanoids, robots, or clothing. "
        "visual must be one of: " + ", ".join(sorted(VISUALS)) + ". "
        "The visual tag must name the same animal explicitly shown in visual_prompt. "
        "Keep at least one protagonist visual tag consistent across two or more beats; never vary it just for variety. "
        "story_environment must be exactly one of: " + ", ".join(SCENES) + ". "
        "Every visual_prompt must show one simple, filmable animal action in that environment. "
        "Avoid complex machinery, bridge/cable repairs, large-gap jumps, and simultaneous multi-prop actions. "
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
        if (beat.get("visual") not in VISUALS or beat.get("story_beat") not in ROLES
                or beat.get("story_environment") not in SCENES
                or not visual_subject_matches(beat.get("visual"), beat.get("visual_prompt"))):
            raise ValueError("Invalid beat subject, environment, or narrative role")
        if not isinstance(beat.get("visual_prompt"), str) or len(beat["visual_prompt"]) < 20:
            raise ValueError("Invalid beat visual prompt")
    for key in ("question", "answer"):
        if not isinstance(data.get(key), str) or not 8 <= len(data[key]) <= 400:
            raise ValueError("Invalid story summary")
    import hashlib
    cid = "rayvan-openai-" + hashlib.sha256(
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
