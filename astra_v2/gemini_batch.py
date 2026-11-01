"""Generate a bounded inventory of distinct Gemini proposals for later review."""
import argparse
import json
from pathlib import Path
from astra_v2.omniroute_gemini import generate


def _failure_reason(exc):
    """Classify only known failure signatures; never persist exception text."""
    message = str(exc)
    if "Gemini HTTP " in message:
        code = message.split("Gemini HTTP ", 1)[1].split()[0]
        return "provider_http_" + code if code.isdigit() else "provider_http_error"
    if message.startswith("Gemini transport failed:"):
        return "provider_transport_error"
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
            "Invalid story summary": "invalid_story_summary",
            "Invalid Gemini model": "invalid_model_configuration",
            "Invalid Gemini fallback model": "invalid_model_configuration",
        }
        if message.startswith("Generated story failed editorial review:"):
            return "editorial_rejected"
        return known.get(message, "validation_error_unclassified")
    return "runtime_error_unclassified"


def generate_batch(count, generator=generate, history=()):
    if not 1 <= count <= 50:
        raise ValueError("count must be 1..50")
    stories, failures = [], []
    history = tuple(history)
    ids = {str(item.get('content_id')) for item in history if isinstance(item, dict) and item.get('content_id')}
    titles = {str(item.get('title')).casefold().strip() for item in history if isinstance(item, dict) and item.get('title')}
    for i in range(count):
        try:
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
            if reason.startswith("provider_http_") or reason == "provider_transport_error":
                break
    return {"status": "unreviewed", "requested": count, "stories": stories,
            "generated": len(stories), "failures": failures}


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
    result = generate_batch(args.count, history=load_history(publisher, story_history))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print("ASTRA_GEMINI_BATCH=" + json.dumps({
        "requested": result["requested"], "generated": result["generated"],
        "failures": result["failures"]}))
    if not result["generated"]:
        raise SystemExit("No stories generated")


if __name__ == "__main__":
    main()
