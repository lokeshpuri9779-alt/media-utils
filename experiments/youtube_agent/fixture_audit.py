#!/usr/bin/env python3
"""Offline read-only fixture compatibility report for ASTRA story JSON."""
import argparse
import json
from pathlib import Path
from story_diagnostics import from_story
from advisory_adapter import analyze

def report(paths):
    results = []
    for path in paths:
        item = {"file": str(path), "parsed": False, "has_hook": False, "has_title": False, "has_thumbnail": False}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Story JSON root is not an object")
            data = from_story(raw)
            item.update(parsed=True, has_hook=bool(data["hook"]), has_title=bool(data["title"]), has_thumbnail=bool(data["thumbnail"]))
            item["diagnostics"] = analyze(data)
        except (ValueError, OSError, TypeError, KeyError) as exc:
            item["error"] = str(exc)
        results.append(item)
    return {"schema_version": 1, "read_only": True, "files_checked": len(results), "results": results}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("paths", nargs="+", type=Path)
    args = p.parse_args()
    print(json.dumps(report(args.paths), indent=2))

if __name__ == "__main__":
    main()
