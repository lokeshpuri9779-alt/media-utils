"""Compare legacy drafts and plot-first proposals without publishing either."""
from collections import Counter
import random
from astra_v2.story_forge import draft_catalog
from astra_v2.plot_first_proposals import proposals
from astra_v2.story_editorial import editorial_issues, semantic_signature


def _stats(stories):
    issues = Counter()
    signatures = []
    for story in stories:
        issues.update(editorial_issues(story))
        signatures.append(semantic_signature(story))
    overlaps = []
    for i, left in enumerate(signatures):
        for right in signatures[:i]:
            union = left | right
            overlaps.append(len(left & right) / len(union) if union else 1.0)
    return {
        "count": len(stories),
        "editorial_issues": dict(sorted(issues.items())),
        "max_pairwise_token_jaccard": round(max(overlaps, default=0), 4),
        "mean_pairwise_token_jaccard": round(sum(overlaps) / len(overlaps), 4) if overlaps else 0.0,
        "publication_approved": 0,
    }


def compare(limit=30, seed=20261020):
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    # Draw across the full legacy pool rather than taking the first N actor swaps.
    legacy_pool = draft_catalog()
    rng = random.Random(seed)
    legacy_rows = rng.sample(legacy_pool, limit)
    legacy = []
    for key, title, genre, beats in legacy_rows:
        legacy.append({
            "content_id": key, "title": title, "kind": "unreviewed_causal_draft",
            "production_ready": False,
            "story_beats": [
                {"story_beat": role, "speech": speech, "visual": visual}
                for role, (_, speech, visual, _) in zip(
                    ("reveal", "build", "twist", "payoff"), beats)
            ],
        })
    plot_pool = proposals(limit=100)
    plot_rows = rng.sample(plot_pool, limit)
    return {"legacy": _stats(legacy), "plot_first": _stats(plot_rows),
            "comparison_scope": "seeded samples across legacy pool (996) and plot-first pool (100); distinct pool sizes",
            "seed": seed}


if __name__ == "__main__":
    import json
    print(json.dumps(compare(), indent=2, sort_keys=True))
