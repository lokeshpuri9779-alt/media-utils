"""Provider failover controller for ASTRA OmniRoute; zero-spend routes only."""
import hashlib
import json
import os
import urllib.error
import urllib.request

from astra_v2.openai_creative import VISUALS, ROLES

PROMPT = (
    "Write one genuinely original, coherent, family-safe science-fiction short "
    "with four cinematic story beats and an unexpected ending. Return only JSON "
    "keys title, question, answer, beats. Each beat needs headline, speech, visual, "
    "label, story_beat. Speech 10-24 words; visual one of planet, robot, signal, "
    "ship, forest, door; story_beat one of reveal, build, mechanism, twist, payoff. "
    "Beat one reveal, beat four payoff, middle beats build/mechanism/twist. "
    "Title 8-75 chars. Avoid copyrighted characters and prior titles: "
)


def _enabled(name, secret):
    return os.getenv(name) == "1" and bool(os.getenv(secret))


def enabled():
    return any((_enabled("ASTRA_GEMINI_ENABLED", "GEMINI_API_KEY"),
                _enabled("ASTRA_GROQ_ENABLED", "GROQ_API_KEY"),
                _enabled("ASTRA_OPENROUTER_ENABLED", "OPENROUTER_API_KEY")))


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
    for i, beat in enumerate(beats):
        if not isinstance(beat, dict):
            raise ValueError(provider + " invalid beat")
        for key in ("headline", "speech", "label"):
            if not isinstance(beat.get(key), str) or not 2 <= len(beat[key]) <= 220:
                raise ValueError(provider + " invalid beat text")
        if beat.get("visual") not in VISUALS or beat.get("story_beat") not in ROLES:
            raise ValueError(provider + " invalid visual or narrative role")
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


def generate(excluded_ids, excluded_titles, prior_stories=()):
    """Try enabled providers in configured order; never relax publication gates."""
    order = [x.strip().lower() for x in os.getenv(
        "ASTRA_OMNIROUTE_ORDER", "gemini,groq,openrouter").split(",") if x.strip()]
    errors = []
    for provider in order:
        try:
            if provider == "gemini" and _enabled("ASTRA_GEMINI_ENABLED", "GEMINI_API_KEY"):
                from astra_v2.omniroute_gemini import generate as gemini_generate
                story = gemini_generate(excluded_ids, excluded_titles, prior_stories)
                if story:
                    print("ASTRA_OMNIROUTE_PROVIDER=gemini")
                    return story
            elif provider == "groq" and _enabled("ASTRA_GROQ_ENABLED", "GROQ_API_KEY"):
                data = _openai_compatible("Groq", "https://api.groq.com/openai/v1/chat/completions",
                    os.getenv("ASTRA_GROQ_MODEL", "llama-3.3-70b-versatile"), "GROQ_API_KEY", excluded_titles)
                story = _validate(data, "Groq", excluded_ids, excluded_titles, prior_stories)
                print("ASTRA_OMNIROUTE_PROVIDER=groq")
                return story
            elif provider == "openrouter" and _enabled("ASTRA_OPENROUTER_ENABLED", "OPENROUTER_API_KEY"):
                model = os.getenv("ASTRA_OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
                if not model.endswith(":free"):
                    raise ValueError("OpenRouter model must use :free to enforce zero-spend policy")
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
