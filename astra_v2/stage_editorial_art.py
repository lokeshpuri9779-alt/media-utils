"""Manual fail-closed artwork staging for one hash-approved editorial story."""
import argparse
import json
import os
from pathlib import Path

from astra_v2.editorial_creative_source import load_editorial_stories
from astra_v2.gemini_art_staging import generate_staged_art


def stage(content_id, destination):
    stories = load_editorial_stories()
    matches = [s for s in stories if s.get("content_id") == content_id]
    if len(matches) != 1:
        raise ValueError("story_not_uniquely_editorially_approved")
    return generate_staged_art(matches[0], destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    print(stage(args.content_id, args.destination))
