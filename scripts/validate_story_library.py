"""Validate external ASTRA JSONL story drafts without enabling auto-publication.

Usage: python scripts/validate_story_library.py path/to/library_studio.jsonl
"""
import argparse
import collections
import json
from pathlib import Path

SUPPORTED = {
    "observatory", "forest", "harbor", "library", "railway", "village",
    "mountain", "desert", "underwater", "space", "laboratory", "garden",
    "lighthouse", "cave", "city", "workshop", "castle", "snowfield",
    "island", "museum",
}


def validate(path):
    seen_ids = set()
    seen_titles = set()
    settings = collections.Counter()
    failures = []
    count = 0
    with Path(path).open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            count += 1
            try:
                story = json.loads(line)
                if not isinstance(story, dict):
                    raise ValueError("record must be an object")
                sid = story.get("content_id")
                title = story.get("title")
                if not isinstance(sid, str) or not sid.strip() or sid in seen_ids:
                    raise ValueError("missing or duplicate content_id")
                if not isinstance(title, str) or not title.strip() or title in seen_titles:
                    raise ValueError("missing or duplicate title")
                seen_ids.add(sid)
                seen_titles.add(title)
                if story.get("genre") != "fiction":
                    raise ValueError("genre must be fiction")
                env = story.get("story_environment")
                if env not in SUPPORTED:
                    raise ValueError("unsupported or absent story_environment")
                beats = story.get("story_beats")
                if not isinstance(beats, list) or len(beats) < 3:
                    raise ValueError("at least three story_beats required")
                for beat in beats:
                    if not isinstance(beat, dict):
                        raise ValueError("beat must be an object")
                    if not str(beat.get("speech") or "").strip():
                        raise ValueError("beat missing speech")
                    if not str(beat.get("visual") or "").strip():
                        raise ValueError("beat missing visual")
                    if beat.get("story_environment") not in SUPPORTED:
                        raise ValueError("beat missing supported setting")
                settings[env] += 1
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                failures.append({"line": line_no, "error": str(exc)})
    return {"records": count, "valid": count - len(failures),
            "invalid": len(failures), "settings": dict(sorted(settings.items())),
            "failures": failures[:25], "approved_for_publication": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    report = validate(args.path)
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if report["invalid"] or not report["records"] else 0)


if __name__ == "__main__":
    main()
