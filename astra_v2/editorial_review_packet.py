"""Generate a review packet from authored stories; never approve automatically."""
import argparse
import json
from pathlib import Path
from astra_v2.editorial_approval_manifest import story_digest
from astra_v2.production_story_gate import candidate_issues


def build_packet(stories, history=()):
    if not isinstance(stories, list):
        raise ValueError("Expected list of authored stories")
    items = []
    seen_ids = set()
    for story in stories:
        if not isinstance(story, dict) or not story.get("content_id"):
            raise ValueError("Invalid story")
        content_id = story["content_id"]
        if content_id in seen_ids:
            raise ValueError("Duplicate content ID")
        seen_ids.add(content_id)
        issues = candidate_issues(story, history)
        items.append({
            "content_id": content_id,
            "title": story.get("title"),
            "kind": story.get("kind"),
            "story_sha256": story_digest(story),
            "candidate_issues": issues,
            "reviewable": not issues,
            "story_beats": story.get("story_beats", []),
            "review_template": {
                "content_id": content_id,
                "story_sha256": story_digest(story),
                "decision": "pending",
                "reviewer": "",
                "review_notes": "",
            },
        })
    return {"items": items, "reviewable_count": sum(i["reviewable"] for i in items),
            "approved_count": 0, "publication_triggered": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = json.loads(Path(args.stories).read_text(encoding="utf-8"))
    result = build_packet(source["stories"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("ASTRA_EDITORIAL_PACKET=" + json.dumps({
        "count": len(result["items"]), "reviewable_count": result["reviewable_count"],
        "approved_count": 0, "publication_triggered": False}))
