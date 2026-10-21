"""Generate a bounded inventory of distinct Gemini proposals for later review."""
import argparse
import json
from pathlib import Path
from astra_v2.omniroute_gemini import generate


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
            failures.append({"index": i, "reason": type(exc).__name__})
            if "HTTP 429" in str(exc):
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
