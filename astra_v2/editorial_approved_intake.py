"""Read-only handoff from explicit editorial approvals to production intake.

This does not upload, render, publish, or modify live queue state.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path
from astra_v2.editorial_approval_manifest import validate_manifest
from astra_v2.proposal_history import load_history


def approved_intake(stories, reviews, history=()):
    audit = validate_manifest(stories, reviews, history)
    approved_ids = {entry["content_id"] for entry in audit["results"] if entry["approved"]}
    approved = []
    for reviewed in stories:
        if reviewed["content_id"] not in approved_ids:
            continue
        # Normalize only after hash-bound editorial approval validation.
        # Preserve original reviewed files and their signed content hashes.
        story = dict(reviewed)
        if story.get("kind") == "authored_causal_story" and story.get("story_beats"):
            if story.get("genre") not in (None, "", "fiction"):
                raise ValueError("reviewed_authored_story_genre_conflict")
            story["genre"] = "fiction"
        approved.append(story)
    return {"stories": approved, "audit": audit, "intake_count": len(approved),
            "publication_triggered": False}


def intake_files(stories_path, reviews_path, output_path,
                 publisher_path="astra_v2_state.json", story_history_path="astra_story_history.json"):
    # A failed audit must never leave a previously approved export reusable.
    output = Path(output_path)
    output.unlink(missing_ok=True)
    story_doc = json.loads(Path(stories_path).read_text(encoding="utf-8"))
    review_doc = json.loads(Path(reviews_path).read_text(encoding="utf-8"))
    # Production intake must never treat absent history as an empty history.
    if not Path(publisher_path).is_file() or not Path(story_history_path).is_file():
        raise FileNotFoundError("editorial_intake_requires_complete_history")
    history = load_history(publisher_path, story_history_path)
    result = approved_intake(story_doc["stories"], review_doc["reviews"], history)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix=".astra-intake-", suffix=".tmp",
                                         delete=False) as handle:
            temporary = Path(handle.name)
            json.dump({"stories": result["stories"]}, handle, indent=2)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories", required=True)
    parser.add_argument("--reviews", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--publisher-state", default="astra_v2_state.json")
    parser.add_argument("--story-history", default="astra_story_history.json")
    args = parser.parse_args()
    result = intake_files(args.stories, args.reviews, args.output,
                          args.publisher_state, args.story_history)
    print("ASTRA_EDITORIAL_INTAKE=" + json.dumps({
        "intake_count": result["intake_count"],
        "rejected_count": len(result["audit"]["results"]) - result["intake_count"],
        "publication_triggered": False}))
