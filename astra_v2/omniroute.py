"""Provider failover controller for ASTRA OmniRoute; zero-spend routes only."""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter

from astra_v2.openai_creative import VISUALS, ROLES, visual_subject_matches
from astra_v2.visual_artifact_library import SCENES
from astra_v2.renderer_aware_writing import background_scene_authoring_guidance

PROMPT = (
    "Write one genuinely original, coherent, family-safe short story using "
    "exactly one or two recurring animal protagonist species supported by ASTRA Studio; "
    "no third animal species, even in the background. Vary settings, motivations, "
    "conflict types, emotional stakes and endings; avoid humans, "
    "humanoids, robots, clothing, complex machinery, bridge/cable repairs, "
    "large-gap jumps and simultaneous multi-prop actions. Ground each story "
    "in a concrete choice and consequence. Use four cinematic story beats. "
    "Return only JSON keys title, question, answer, beats. Each beat needs "
    "headline, speech, visual, visual_prompt, story_environment, label, story_beat. "
    "visual must be one of: " + ", ".join(sorted(VISUALS)) + ". It names the "
    "same animal explicitly shown in visual_prompt. Keep at least one main "
    "protagonist visual tag consistent across two or more beats; do not change "
    "tags merely for variety. story_environment must be exactly one of: "
    + ", ".join(SCENES) + ". The exact story_environment token must appear "
    "in visual_prompt. Every visual_prompt describes one simple visible "
    "animal action in that environment. Across four beats, create at least "
    "three genuinely different shots through action, composition, location or "
    "a supported prop; do not create variety by changing animal tags. "
    "Speech 12-24 words per beat. "
    "story_beat one of reveal, build, mechanism, twist, payoff; beat one reveal, "
    "beat four payoff, middle beats build/mechanism/twist. Title 8-75 chars. "
    "Avoid copyrighted characters. "
)
PROMPT += background_scene_authoring_guidance() + " Prior titles to avoid: "



def validate_beat_quality(beats, provider="OmniRoute"):
    """Require supported animal subjects and explicit compositor environments."""
    if not isinstance(beats, list) or len(beats) != 4:
        raise ValueError(provider + " requires exactly four beats")
    if any(not isinstance(beat, dict) for beat in beats):
        raise ValueError(provider + " invalid beat")
    if any(len(str(beat.get("speech") or "").split()) < 12 for beat in beats):
        raise ValueError(provider + " narration needs at least 12 words per beat")
    visual_tags = []
    for beat in beats:
        visual = beat.get("visual")
        prompt = beat.get("visual_prompt")
        if visual not in VISUALS:
            raise ValueError(provider + " visual must name a supported animal subject")
        if not isinstance(prompt, str) or len(prompt.strip()) < 20:
            raise ValueError(provider + " requires a concrete visual_prompt")
        if not visual_subject_matches(visual, prompt):
            raise ValueError(provider + " visual tag does not match the depicted animal")
        environment = beat.get("story_environment")
        if environment not in SCENES:
            raise ValueError(provider + " requires a supported story_environment")
        if not re.search(r"\b" + re.escape(environment) + r"\b", prompt, re.I):
            raise ValueError(provider + " story_environment must appear in visual_prompt")
        visual_tags.append(visual)
    if len(set(visual_tags)) > 2:
        raise ValueError(provider + " must use at most two animal protagonist species")
    from astra_v2.story_visuals import SUBJECTS
    subject_patterns = dict(SUBJECTS)
    story_text = " ".join(
        str(beat.get(key) or "") for beat in beats
        for key in ("speech", "visual_prompt")
    )
    mentioned_animals = {
        species for species in VISUALS
        if re.search(subject_patterns[species], story_text, re.I)
    }
    if len(mentioned_animals) > 2 or not mentioned_animals.issubset(set(visual_tags)):
        raise ValueError(provider + " contains an untagged or third animal species")
    if not any(count >= 2 for count in Counter(visual_tags).values()):
        raise ValueError(provider + " must preserve a protagonist visual across beats")


def _enabled(name, secret):
    return os.getenv(name) == "1" and bool(os.getenv(secret))


def enabled():
    return any((_enabled("ASTRA_GEMINI_ENABLED", "GEMINI_API_KEY"),
                _enabled("ASTRA_GROQ_ENABLED", "GROQ_API_KEY"),
                _enabled("ASTRA_OPENROUTER_ENABLED", "OPENROUTER_API_KEY"),
                _enabled("ASTRA_NVIDIA_ENABLED", "NVIDIA_API_KEY") and os.getenv("ASTRA_NVIDIA_FREE_CONFIRMED") == "1"))


def _openai_compatible(provider, base_url, model, secret, excluded_titles):
    prompt = PROMPT + json.dumps(sorted(excluded_titles)[:100])
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": "Return valid JSON only. Follow schema exactly."},
                     {"role": "user", "content": prompt}],
        "temperature": 0.8, "max_tokens": 1800,
        "response_format": {"type": "json_object"}
    }).encode()
    req = urllib.request.Request(base_url, data=body, method="POST", headers={
        "Authorization": "Bearer " + os.environ[secret],
        "Content-Type": "application/json", "HTTP-Referer": "https://github.com/lokeshpuri9779-alt/media-utils",
        "X-Title": "ASTRA OmniRoute"})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(provider + " HTTP " + str(exc.code)) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(provider + " transport failed: " + type(exc).__name__) from exc
    choices = result.get("choices") or []
    if not choices or not isinstance(choices[0].get("message", {}).get("content"), str):
        raise ValueError(provider + " returned no message")
    return json.loads(choices[0]["message"]["content"])


def _validate(data, provider, excluded_ids, excluded_titles, prior_stories):
    title, beats = data.get("title"), data.get("beats")
    if (not isinstance(title, str) or not 8 <= len(title) <= 75
            or title.casefold().strip() in excluded_titles
            or not isinstance(beats, list) or len(beats) != 4):
        raise ValueError(provider + " story title or beat count invalid")
    validate_beat_quality(beats, provider)
    for i, beat in enumerate(beats):
        if not isinstance(beat, dict):
            raise ValueError(provider + " invalid beat")
        for key in ("headline", "speech", "label"):
            if not isinstance(beat.get(key), str) or not 2 <= len(beat[key]) <= 220:
                raise ValueError(provider + " invalid beat text")
        if beat.get("story_beat") not in ROLES:
            raise ValueError(provider + " invalid narrative role")
        words = len(beat["speech"].split())
        if not 10 <= words <= 24:
            raise ValueError(provider + " narration word count invalid")
        if i == 0 and beat["story_beat"] != "reveal":
            raise ValueError(provider + " first beat must reveal")
        if i == 3 and beat["story_beat"] != "payoff":
            raise ValueError(provider + " final beat must pay off")
    for key in ("question", "answer"):
        if not isinstance(data.get(key), str) or not 8 <= len(data[key]) <= 400:
            raise ValueError(provider + " invalid story summary")
    cid = "rayvan-" + provider.lower() + "-" + hashlib.sha256(
        (title.casefold().strip() + "|" + data["answer"].casefold().strip()).encode()
    ).hexdigest()[:20]
    if cid in excluded_ids:
        raise ValueError(provider + " duplicate story identity")
    from astra_v2.shorts_novelty import is_near_duplicate
    from astra_v2.story_planning import planning_issues
    from astra_v2.story_forge import plot_fingerprint
    story = {"genre":"fiction","kind":"microfiction","production_ready":True,
        "content_id":cid,"title":title,"hook":beats[0]["headline"],
        "question":data["question"],"answer":data["answer"],"source":"",
        "keywords":["original science fiction","short story"],
        "story_beats":[{**beat,"sub":"AN ORIGINAL RAYVAN STORY","duration":2.1} for beat in beats]}
    story["plot_fingerprint"] = plot_fingerprint([("", b["speech"], "", "") for b in story["story_beats"]])
    issues = planning_issues(story)
    if issues:
        raise ValueError(provider + " failed causal planning")
    from astra_v2.story_editorial import editorial_issues
    editorial = editorial_issues(story, prior_stories)
    if editorial:
        raise ValueError(provider + " failed editorial review: " + ",".join(editorial))
    if is_near_duplicate(story, prior_stories):
        raise ValueError(provider + " repeats narrative history")
    return story


def generate(excluded_ids, excluded_titles, prior_stories=(), premise=None):
    """Try enabled providers in configured order; never relax publication gates."""
    order = [x.strip().lower() for x in os.getenv(
        "ASTRA_OMNIROUTE_ORDER", "gemini,groq,openrouter,nvidia").split(",") if x.strip()]
    if premise is not None and "gemini" not in order:
        raise ValueError("Premise-guided generation requires configured Gemini provider")
    errors = []
    for provider in order:
        try:
            if provider == "gemini" and _enabled("ASTRA_GEMINI_ENABLED", "GEMINI_API_KEY"):
                from astra_v2.omniroute_gemini import generate as gemini_generate
                story = gemini_generate(excluded_ids, excluded_titles, prior_stories, premise=premise)
                if story:
                    print("ASTRA_OMNIROUTE_PROVIDER=gemini")
                    return story
            elif premise is not None:
                continue
            elif provider == "groq" and _enabled("ASTRA_GROQ_ENABLED", "GROQ_API_KEY"):
                data = _openai_compatible("Groq", "https://api.groq.com/openai/v1/chat/completions",
                    os.getenv("ASTRA_GROQ_MODEL", "llama-3.3-70b-versatile"), "GROQ_API_KEY", excluded_titles)
                story = _validate(data, "Groq", excluded_ids, excluded_titles, prior_stories)
                print("ASTRA_OMNIROUTE_PROVIDER=groq")
                return story
            elif provider == "nvidia" and _enabled("ASTRA_NVIDIA_ENABLED", "NVIDIA_API_KEY"):
                if os.getenv("ASTRA_NVIDIA_FREE_CONFIRMED") != "1":
                    raise ValueError("NVIDIA free-tier confirmation required")
                model = os.getenv("ASTRA_NVIDIA_MODEL", "").strip()
                if not model or not all(c.isalnum() or c in "/._-" for c in model):
                    raise ValueError("NVIDIA model must be explicitly configured")
                data = _openai_compatible("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions",
                    model, "NVIDIA_API_KEY", excluded_titles)
                story = _validate(data, "NVIDIA", excluded_ids, excluded_titles, prior_stories)
                print("ASTRA_OMNIROUTE_PROVIDER=nvidia")
                return story
            elif provider == "openrouter" and _enabled("ASTRA_OPENROUTER_ENABLED", "OPENROUTER_API_KEY"):
                model = os.getenv("ASTRA_OPENROUTER_MODEL", "openrouter/free")
                if model != "openrouter/free" and not model.endswith(":free"):
                    raise ValueError("OpenRouter model must be openrouter/free or use :free to enforce zero-spend policy")
                data = _openai_compatible("OpenRouter", "https://openrouter.ai/api/v1/chat/completions",
                    model, "OPENROUTER_API_KEY", excluded_titles)
                story = _validate(data, "OpenRouter", excluded_ids, excluded_titles, prior_stories)
                print("ASTRA_OMNIROUTE_PROVIDER=openrouter")
                return story
        except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            safe = str(exc)[:120]
            errors.append(provider + ":" + safe)
            print("ASTRA_OMNIROUTE_PROVIDER_FAILED=" + provider + ":" + safe)
    if errors:
        raise RuntimeError("All enabled OmniRoute providers failed: " + ";".join(errors)[:350])
    return None
