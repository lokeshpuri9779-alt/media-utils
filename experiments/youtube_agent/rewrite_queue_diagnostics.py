#!/usr/bin/env python3
"""Read-only diagnostics for actual ASTRA Story Factory rewrite queue JSON."""
import argparse
import json
from pathlib import Path
from advisory_adapter import analyze
from story_diagnostics import from_story

def inspect_queue(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("rewrites"), list):
        raise ValueError("Expected Story Factory rewrite queue with rewrites array")
    results = []
    for idx, entry in enumerate(payload["rewrites"]):
        story = entry.get("story") if isinstance(entry, dict) else None
        if not isinstance(story, dict):
            results.append({"index": idx, "error": "missing story object"})
            continue
        fields = from_story(story)
        results.append({
            "index": idx,
            "content_id": story.get("content_id"),
            "has_hook": bool(fields["hook"]),
            "has_title": bool(fields["title"]),
            "has_thumbnail": bool(fields["thumbnail"]),
            "diagnostics": analyze(fields),
        })
    return {
        "schema_version": 1,
        "source": "story_factory_rewrite_queue",
        "advisory_only": True,
        "publication_triggered": False,
        "entries_checked": len(results),
        "results": results,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect_queue(json.loads(args.queue.read_text(encoding="utf-8"))), indent=2))

if __name__ == "__main__":
    main()
