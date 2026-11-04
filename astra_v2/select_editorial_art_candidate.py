"""Select one hash-approved, unpublished story for review-only artwork staging."""
import contextlib
import json
import sys
from astra_v2.editorial_creative_source import load_editorial_stories


def select_candidate():
    # Editorial intake writes diagnostics to stdout; keep machine output pure JSON.
    with contextlib.redirect_stdout(sys.stderr):
        stories = load_editorial_stories()
    eligible = sorted((story for story in stories
                       if isinstance(story, dict) and isinstance(story.get("content_id"), str)
                       and story["content_id"].strip()), key=lambda story: story["content_id"])
    if not eligible:
        return None
    return {"content_id": eligible[0]["content_id"], "title": eligible[0].get("title", "")}


def main():
    selected = select_candidate()
    if selected is None:
        print("ASTRA_ART_SELECTION=no_eligible_approved_unpublished_story", file=sys.stderr)
        return 2
    print(json.dumps(selected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
