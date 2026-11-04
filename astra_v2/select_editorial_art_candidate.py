"""Select one eligible, approved, unpublished editorial story for art staging."""
import json
import sys
from astra_v2.editorial_creative_source import load_editorial_stories


def main():
    stories = load_editorial_stories()
    eligible = sorted(
        (story for story in stories if story.get("content_id")),
        key=lambda story: story["content_id"],
    )
    if not eligible:
        print("ASTRA_ART_SELECTION=no_eligible_approved_unpublished_story", file=sys.stderr)
        return 2
    selected = eligible[0]
    print(json.dumps({"content_id": selected["content_id"], "title": selected.get("title", "")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
