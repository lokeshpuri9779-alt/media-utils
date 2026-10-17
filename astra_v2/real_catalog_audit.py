"""Read-only editorial audit of actual ASTRA free-engine catalog stories.

Run: python -m astra_v2.real_catalog_audit
No publication, promotion, ledger mutation or rendering.
"""
import json
from collections import Counter

from astra_v2.free_story_engine import catalog
from astra_v2.story_editorial import editorial_issues


def audit():
    history = []
    results = []
    for candidate in catalog():
        issues = editorial_issues(candidate, history)
        results.append({
            "content_id": candidate.get("content_id"),
            "title": candidate.get("title"),
            "issues": issues,
            "needs_review": bool(issues),
        })
        history.append(candidate)
    counts = Counter(issue for row in results for issue in row["issues"])
    return {
        "source": "astra_v2.free_story_engine.catalog",
        "total": len(results),
        "flagged": sum(row["needs_review"] for row in results),
        "issue_counts": dict(sorted(counts.items())),
        "publication_decision": "unchanged",
        "enforcement": "diagnostic_only",
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
