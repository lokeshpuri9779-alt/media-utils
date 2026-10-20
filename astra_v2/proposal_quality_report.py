"""Measure plot-first candidate quality without authorizing publication."""
from collections import Counter
from astra_v2.plot_first_proposals import proposals
from astra_v2.story_editorial import semantic_signature


def quality_report(limit=100):
    candidates = proposals(limit=limit)
    issues = Counter(issue for item in candidates for issue in item["editorial_issues"])
    signatures = [semantic_signature(item) for item in candidates]
    similarities = []
    for i, left in enumerate(signatures):
        for right in signatures[:i]:
            union = left | right
            similarities.append(len(left & right) / len(union) if union else 1.0)
    return {
        "candidates": len(candidates),
        "editorial_issue_counts": dict(sorted(issues.items())),
        "unique_fingerprints": len({item["plot_fingerprint"] for item in candidates}),
        "unique_titles": len({item["title"].casefold() for item in candidates}),
        "max_pairwise_token_jaccard": round(max(similarities, default=0.0), 4),
        "mean_pairwise_token_jaccard": round(sum(similarities) / len(similarities), 4) if similarities else 0.0,
        "publication_approved": 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(quality_report(), indent=2, sort_keys=True))
