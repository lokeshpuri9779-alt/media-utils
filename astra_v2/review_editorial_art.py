"""Review staged art against the exact editorially approved story."""
import argparse
import json
from pathlib import Path

from astra_v2.editorial_creative_source import load_editorial_stories
from astra_v2.gemini_art_semantic_review import review


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    stories = [s for s in load_editorial_stories() if s.get("content_id") == args.content_id]
    if len(stories) != 1:
        raise SystemExit("Semantic review requires one eligible editorial story")
    report = review(stories[0], args.manifest)
    Path(args.output).write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    if not report["semantic_pass"]:
        raise SystemExit("Semantic QA rejected artwork; no approval granted")


if __name__ == "__main__":
    main()
