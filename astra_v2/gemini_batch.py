"""Generate a bounded inventory of distinct Gemini proposals for later review."""
import argparse
import json
import os
import time
from pathlib import Path
from astra_v2.omniroute_gemini import generate


# Exact trusted validator messages (provider prefix removed). Classification
# only labels a rejection; it never relaxes the validator that raised it and
# never persists model-authored text.
_VALIDATOR_REASONS = {
    "requires exactly four cinematic beats": "invalid_beat_count",
    "returned an invalid story beat": "invalid_beat",
    "invalid beat": "invalid_beat",
    "narration must be 24-38 words per beat": "beat_word_count_out_of_range",
    "narration must total 96-152 words": "total_word_count_out_of_range",
    "story needs at least one natural dialogue line": "missing_dialogue",
    "story needs at least two scene-ending hooks": "insufficient_scene_hooks",
    "visual must name a supported animal subject": "unsupported_visual_subject",
    "requires a concrete visual_prompt": "missing_visual_prompt",
    "visual tag does not match the depicted animal": "visual_tag_mismatch",
    "requires a supported story_environment": "unsupported_story_environment",
    "story_environment must appear in visual_prompt": "environment_not_in_visual_prompt",
    "must use at most two animal protagonist species": "too_many_protagonist_species",
    "contains an untagged or third animal species": "untagged_or_third_species",
    "must preserve a protagonist visual across beats": "protagonist_not_preserved",
}


def _failure_reason(exc):
    """Classify only known failure signatures; never persist exception text."""
    message = str(exc)
    if "Gemini HTTP " in message:
        code = message.split("Gemini HTTP ", 1)[1].split()[0]
        return "provider_http_" + code if code.isdigit() else "provider_http_error"
    if message.startswith("Gemini transport failed:"):
        return "provider_transport_error"
    # Both configured free-tier models failed after their bounded retries.
    # This is provider unavailability, not a story quality rejection.
    if message == "Gemini exhausted configured free-tier models without a response":
        return "provider_models_exhausted"
    if isinstance(exc, KeyError):
        return "missing_required_field"
    if isinstance(exc, json.JSONDecodeError):
        return "invalid_provider_json"
    if isinstance(exc, ValueError):
        known = {
            "duplicate_candidate": "duplicate_candidate",
            "Duplicate story content": "duplicate_candidate",
            "Generated story repeats narrative history": "narrative_duplicate",
            "Generated story failed causal planning": "causal_planning_rejected",
            "Generated story title or beat count invalid": "invalid_story_structure",
            "Gemini returned no candidates": "empty_provider_response",
            "Gemini response incomplete": "incomplete_provider_response",
            "Invalid visual bible": "invalid_visual_bible",
            "Invalid visual bible entities": "invalid_visual_bible",
            "Invalid beat": "invalid_beat",
            "Invalid beat text": "invalid_beat",
            "Invalid beat visual or narrative role": "invalid_beat",
            # Exact trusted validator messages only; never persist model text.
            "Gemini requires exactly four beats": "invalid_beat_count",
            "Gemini narration needs at least 12 words per beat": "insufficient_beat_narration",
            "Gemini needs at least three distinct visual types": "insufficient_visual_diversity",
            "Invalid story summary": "invalid_story_summary",
            "Invalid Gemini model": "invalid_model_configuration",
            "Invalid Gemini fallback model": "invalid_model_configuration",
        }
        if message.startswith("Generated story failed editorial review:"):
            return "editorial_rejected"
        if message == "Invalid beat subject, environment, or narrative role":
            return "invalid_beat"
        if message in known:
            return known[message]
        for prefix in ("Gemini ", "ASTRA ", "OmniRoute "):
            if message.startswith(prefix):
                suffix = message[len(prefix):]
                if suffix in _VALIDATOR_REASONS:
                    return _VALIDATOR_REASONS[suffix]
        return "validation_error_unclassified"
    return "runtime_error_unclassified"


def generate_batch(count, generator=generate, history=(), *, pace_seconds=0,
                   rate_limit_cooldown=0, max_cooldowns=2, sleep=time.sleep):
    """Generate up to ``count`` unreviewed proposals.

    ``pace_seconds`` spaces provider calls to respect free-tier per-minute
    limits. ``rate_limit_cooldown`` allows one bounded wait-and-retry of a slot
    after an HTTP 429, at most ``max_cooldowns`` times per batch; a 429 that
    persists still stops the batch. Defaults keep the original behaviour.
    """
    if not 1 <= count <= 50:
        raise ValueError("count must be 1..50")
    stories, failures = [], []
    history = tuple(history)
    ids = {str(item.get('content_id')) for item in history if isinstance(item, dict) and item.get('content_id')}
    titles = {str(item.get('title')).casefold().strip() for item in history if isinstance(item, dict) and item.get('title')}
    cooldowns = 0
    for i in range(count):
        if i and pace_seconds > 0:
            sleep(pace_seconds)
        try:
            try:
                story = generator(ids, titles, history + tuple(stories))
            except RuntimeError as first:
                if (_failure_reason(first) != "provider_http_429"
                        or rate_limit_cooldown <= 0 or cooldowns >= max_cooldowns):
                    raise
                cooldowns += 1
                sleep(rate_limit_cooldown)
                story = generator(ids, titles, history + tuple(stories))
            if story is None:
                failures.append({"index": i, "reason": "unavailable"})
                break
            cid, title = story["content_id"], story["title"].casefold().strip()
            if cid in ids or title in titles:
                raise ValueError("duplicate_candidate")
            stories.append(story)
            ids.add(cid)
            titles.add(title)
        except (RuntimeError, ValueError, KeyError) as exc:
            reason = _failure_reason(exc)
            failures.append({"index": i, "reason": reason})
            if reason.startswith("provider_http_") or reason in (
                    "provider_transport_error", "provider_models_exhausted"):
                # Avoid calling the same unavailable service on every slot.
                break
    return {"status": "unreviewed", "requested": count, "stories": stories,
            "generated": len(stories), "failures": failures,
            "attempted": len(stories) + len(failures), "cooldowns": cooldowns}


def _bounded_float(name, default, high):
    try:
        value = float(os.getenv(name, default))
    except ValueError:
        return float(default)
    return min(max(value, 0.0), high)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--output", default="runtime-health/gemini-proposals.json")
    args = parser.parse_args()
    from astra_v2.proposal_history import load_history
    publisher = Path('astra_v2_state.json')
    story_history = Path('astra_story_history.json')
    if not publisher.is_file() or not story_history.is_file():
        raise SystemExit('Gemini batch requires complete publication history')
    result = generate_batch(
        args.count, history=load_history(publisher, story_history),
        pace_seconds=_bounded_float("ASTRA_GEMINI_BATCH_PACE_SECONDS", 6, 30),
        rate_limit_cooldown=_bounded_float(
            "ASTRA_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS", 65, 120))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print("ASTRA_GEMINI_BATCH=" + json.dumps({
        "requested": result["requested"], "generated": result["generated"],
        "attempted": result["attempted"], "cooldowns": result["cooldowns"],
        "failures": result["failures"]}))
    if not result["generated"]:
        raise SystemExit("No stories generated")


if __name__ == "__main__":
    main()
