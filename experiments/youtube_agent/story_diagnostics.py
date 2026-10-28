#!/usr/bin/env python3
"""Extract optional advisory fields from ASTRA-like JSON without modifying source."""
import argparse
import json
from pathlib import Path
from advisory_adapter import analyze

def first_text(record, keys):
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None

def from_story(record):
    if not isinstance(record, dict):
        raise ValueError("Story must be an object")
    meta = record.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
    script = record.get("script")
    if not isinstance(script, dict):
        script = {}
    hook = first_text(record, ("hook", "opening_hook")) or first_text(script, ("hook", "opening", "intro"))
    title = first_text(record, ("youtube_title", "title")) or first_text(meta, ("youtube_title", "title"))
    thumbnail = first_text(record, ("thumbnail_text", "thumb_text")) or first_text(meta, ("thumbnail_text",))
    return {"hook": hook, "title": title, "thumbnail": thumbnail}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("story", type=Path)
    args = parser.parse_args()
    story = json.loads(args.story.read_text(encoding="utf-8"))
    diagnostics = analyze(from_story(story))
    diagnostics["source"] = "story_metadata"
    print(json.dumps(diagnostics, indent=2))

if __name__ == "__main__":
    main()
