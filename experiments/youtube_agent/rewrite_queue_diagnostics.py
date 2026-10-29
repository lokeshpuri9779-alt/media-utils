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
        hook_words = len(fields["hook"].split()) if fields["hook"] else 0
        diagnostics = analyze(fields)
        if "hook" in diagnostics:
            # No heuristic hook score may be used for an editorial decision.
            diagnostics["hook"]["quality_decision_allowed"] = False
            diagnostics["hook"]["interpretation"] = (
                "short_label_not_spoken_hook" if 0 < hook_words < 9
                else "unvalidated_heuristic_not_quality_gate"
            )
        results.append({
            "index": idx,
            "hook_score_applicability": "limited_short_fiction_label" if 0 < hook_words < 9 else ("not_available" if hook_words == 0 else "heuristic_only"),
            "content_id": story.get("content_id"),
            "has_hook": bool(fields["hook"]),
            "has_title": bool(fields["title"]),
            "has_thumbnail": bool(fields["thumbnail"]),
            "diagnostics": diagnostics,
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
