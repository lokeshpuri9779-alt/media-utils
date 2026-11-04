"""Read-only cross-source story audit; never approves or publishes proposals."""
import json
from collections import Counter

from astra_v2.free_story_engine import catalog as free_catalog
from astra_v2.story_forge import catalog as forge_catalog
from astra_v2.genre_story_supply import genre_proposal
from astra_v2.story_editorial import editorial_issues


def audit(genre_count=100, forge_limit=256):
    if not isinstance(genre_count, int) or isinstance(genre_count, bool) or not 0 <= genre_count <= 1000:
        raise ValueError("genre_count must be between 0 and 1000")
    if not isinstance(forge_limit, int) or isinstance(forge_limit, bool) or not 0 <= forge_limit <= 1000:
        raise ValueError("forge_limit must be between 0 and 1000")
    sources = (
        ("free", free_catalog()),
        ("forge", forge_catalog(limit=forge_limit) if forge_limit else []),
        ("genre_drafts", [genre_proposal(i) for i in range(genre_count)]),
    )
    history, results = [], []
    for source, stories in sources:
        for story in stories:
            issues = editorial_issues(story, history)
            results.append({
                "source": source,
                "content_id": story.get("content_id"),
                "issues": issues,
                "requires_review": bool(issues),
                "production_ready": bool(story.get("production_ready")),
            })
            history.append(story)
    return {
        "total": len(results),
        "source_counts": dict(sorted(Counter(r["source"] for r in results).items())),
        "issue_counts": dict(sorted(Counter(i for r in results for i in r["issues"]).items())),
        "flagged": sum(r["requires_review"] for r in results),
        "enforcement": "diagnostic_only",
        "publication_decision": "unchanged",
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True, indent=2))
