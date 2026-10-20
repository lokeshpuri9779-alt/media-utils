"""Read-only diagnostic of semantic candidate fan-out on persisted proposals.

No approvals, publishing actions, or changes to matching semantics.
"""
import argparse
import json
import statistics
from pathlib import Path

from astra_v2.semantic_candidate_index import SemanticCandidateIndex
from astra_v2.story_editorial import _semantic_features


def diagnose(stories, limit=1000):
    index = SemanticCandidateIndex()
    rows = []
    for story in stories[:limit]:
        if not isinstance(story, dict):
            continue
        signature, words, fingerprint = _semantic_features(story)
        positions = set()
        for token in signature:
            positions.update(index.signature_postings.get(token, ()))
        for token in words:
            positions.update(index.word_postings.get(token, ()))
        if fingerprint:
            positions.update(index.fingerprint_postings.get(fingerprint, ()))
        rows.append({
            "history": len(index.items),
            "candidates": len(positions),
            "ratio": len(positions) / len(index.items) if index.items else 0,
        })
        index.add(story)
    if not rows:
        raise ValueError("No valid story proposals")
    ratios = [row["ratio"] for row in rows if row["history"]]
    return {
        "sample_count": len(rows),
        "comparison_count": sum(row["candidates"] for row in rows),
        "exhaustive_comparison_count": sum(row["history"] for row in rows),
        "mean_candidate_fraction": round(statistics.mean(ratios), 4) if ratios else 0,
        "median_candidate_fraction": round(statistics.median(ratios), 4) if ratios else 0,
        "max_candidate_fraction": round(max(ratios), 4) if ratios else 0,
        "publication_enabled": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", default="runtime-health/story_proposals.json")
    parser.add_argument("--sample", type=int, default=1000)
    args = parser.parse_args()
    if not 1 <= args.sample <= 5000:
        raise ValueError("sample must be 1..5000")
    ledger = json.loads(Path(args.ledger).read_text())
    print(json.dumps(diagnose(ledger["proposals"], args.sample), sort_keys=True))
