"""Explain which authored ASTRA stories are actually render-compatible.

This is a read-only supply diagnostic; it does not authorize an upload,
promote drafts, or bypass any publication/rendering quality check.
"""
from __future__ import annotations

import json
from collections import Counter

from astra_v2.publication_quality import publication_rejection
from astra_v2.story_forge import catalog


def audit() -> dict:
    stories = catalog(limit=2000)
    causes = Counter()
    samples = []
    for story in stories:
        reason = publication_rejection(story)
        if reason:
            causes[reason.split(":", 1)[0]] += 1
            if len(samples) < 12:
                samples.append({"content_id": story["content_id"],
                                "title": story["title"],
                                "reason": reason[:210]})
        else:
            causes["eligible"] += 1
    return {
        "schema_version": 1,
        "authored_catalog": len(stories),
        "render_eligible": causes["eligible"],
        "rejected": len(stories) - causes["eligible"],
        "by_reason": dict(sorted(causes.items())),
        "rejection_samples": samples,
        "note": "Editorial authored status is NOT video render/publication proof.",
    }


def main() -> None:
    data = audit()
    print("ASTRA_RENDERER_ELIGIBILITY_AUDIT=" + json.dumps(data, sort_keys=True))
    if data["render_eligible"] < 1:
        raise SystemExit("no_render_eligible_stories")


if __name__ == "__main__":
    main()
