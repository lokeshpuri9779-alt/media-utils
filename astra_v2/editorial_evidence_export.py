"""Attach non-publishing editorial evidence to the exported review packet.

Evidence is advisory and never modifies story payloads, review decisions,
production_ready, or the publisher's approved intake manifest.
"""
import argparse
import json
from pathlib import Path

from astra_v2.automated_editorial_evidence import assess


def write_evidence(stories_file, output_file):
    source = json.loads(Path(stories_file).read_text(encoding="utf-8"))
    stories = source.get("stories")
    if not isinstance(stories, list):
        raise ValueError("Invalid editorial review stories")
    ids = [story.get("content_id") for story in stories if isinstance(story, dict)]
    if len(ids) != len(stories) or len(set(ids)) != len(ids):
        raise ValueError("Invalid or duplicate review story identities")
    evidence = [assess(story) for story in stories]
    payload = {
        "schema_version": 1,
        "story_count": len(evidence),
        "recommended_for_review": sum(x["recommendation"] == "editorial_review" for x in evidence),
        "approved_count": 0,
        "publication_triggered": False,
        "assessments": evidence,
    }
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = write_evidence(args.stories, args.output)
    print("ASTRA_EDITORIAL_EVIDENCE=" + json.dumps({
        key: result[key] for key in ("story_count", "recommended_for_review",
                                    "approved_count", "publication_triggered")
    }, sort_keys=True))
