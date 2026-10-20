"""Read-only batch preparation for exported editorial story bundles."""
import argparse
import json
from pathlib import Path

from astra_v2.editorial_preparation import prepare_for_editorial_review


def prepare_batch(document):
    if not isinstance(document, dict) or not isinstance(document.get("stories"), list):
        raise ValueError("stories_document_invalid")
    stories = document["stories"]
    ids = [s.get("content_id") for s in stories if isinstance(s, dict)]
    if (len(ids) != len(stories)
            or any(not isinstance(cid, str) or not cid.strip() for cid in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError("duplicate_or_invalid_story_ids")
    prepared = [prepare_for_editorial_review(story) for story in stories]
    return {
        "schema_version": 1,
        "count": len(prepared),
        "stories": prepared,
        "approved_count": 0,
        "publication_triggered": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.unlink(missing_ok=True)
    result = prepare_batch(json.loads(Path(args.stories).read_text(encoding="utf-8")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("ASTRA_EDITORIAL_PREPARATION=" + json.dumps({
        "count": result["count"], "approved_count": 0, "publication_triggered": False
    }))


if __name__ == "__main__":
    main()
