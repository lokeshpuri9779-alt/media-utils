"""Read-only handoff from explicit editorial approvals to production intake.

This does not upload, render, publish, or modify live queue state.
"""
import argparse
import json
from pathlib import Path
from astra_v2.editorial_approval_manifest import validate_manifest


def approved_intake(stories, reviews, history=()):
    audit = validate_manifest(stories, reviews, history)
    approved_ids = {entry["content_id"] for entry in audit["results"] if entry["approved"]}
    approved = [story for story in stories if story["content_id"] in approved_ids]
    return {"stories": approved, "audit": audit, "intake_count": len(approved),
            "publication_triggered": False}


def intake_files(stories_path, reviews_path, output_path):
    story_doc = json.loads(Path(stories_path).read_text(encoding="utf-8"))
    review_doc = json.loads(Path(reviews_path).read_text(encoding="utf-8"))
    result = approved_intake(story_doc["stories"], review_doc["reviews"])
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"stories": result["stories"]}, indent=2),
                      encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories", required=True)
    parser.add_argument("--reviews", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = intake_files(args.stories, args.reviews, args.output)
    print("ASTRA_EDITORIAL_INTAKE=" + json.dumps({
        "intake_count": result["intake_count"],
        "rejected_count": len(result["audit"]["results"]) - result["intake_count"],
        "publication_triggered": False}))
