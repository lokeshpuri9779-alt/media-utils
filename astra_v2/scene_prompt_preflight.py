"""Offline prompt preflight: no image generation, approvals, or publishing."""
import argparse
import json
from pathlib import Path

from astra_v2.story_art_direction import illustration_requests


def audit(queue):
    rows = []
    for entry in queue.get("rewrites", []):
        story = entry.get("story")
        if not isinstance(story, dict):
            continue
        content_id = story.get("content_id")
        if entry.get("status") != "awaiting_independent_editorial_approval":
            rows.append({"content_id": content_id, "status": "not_in_review_queue",
                         "production_ready": False})
            continue
        try:
            requests = illustration_requests(story)
            lengths = [len(x["prompt"]) for x in requests]
            rows.append({"content_id": content_id, "status": "prompt_preflight_pass",
                         "scene_count": len(requests), "prompt_lengths": lengths,
                         "visual_bible_supplied": all(x["visual_bible_supplied"] for x in requests),
                         "production_ready": False, "editorial_approval": False})
        except (ValueError, TypeError, KeyError) as exc:
            rows.append({"content_id": content_id, "status": "prompt_preflight_failed",
                         "error": str(exc), "production_ready": False,
                         "editorial_approval": False})
    return {"schema_version": 1, "kind": "offline_prompt_preflight",
            "provider_calls": 0, "approval_granted": False,
            "production_ready": False, "stories": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = audit(json.loads(Path(args.queue).read_text(encoding="utf-8")))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("ASTRA_PROMPT_PREFLIGHT=" + json.dumps({
        "stories": len(report["stories"]),
        "passed": sum(x["status"] == "prompt_preflight_pass" for x in report["stories"]),
        "provider_calls": 0, "approval_granted": False}, sort_keys=True))


if __name__ == "__main__":
    main()
