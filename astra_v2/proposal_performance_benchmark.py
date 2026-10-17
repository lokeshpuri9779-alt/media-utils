"""Local deterministic benchmark for ASTRA's editorial proposal pipeline.

Run: python -m astra_v2.proposal_performance_benchmark
This benchmark never writes production state or grants publication approval.
"""
import argparse
import json
import time
from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_editorial import triage
from astra_v2.proposal_novelty_index import NoveltyIndex
from astra_v2.story_editorial import _semantic_features, editorial_issues


def benchmark(count=100):
    if not 1 <= count <= 500:
        raise ValueError("count must be between 1 and 500")
    start = time.perf_counter()
    stories = [proposal(i) for i in range(count)]
    generated = time.perf_counter()
    review = triage(stories)
    triaged = time.perf_counter()
    history = []
    index = NoveltyIndex()
    semantic_previous = []
    blocked = 0
    for story in stories:
        issues = editorial_issues(story, history, novelty_index=index,
                                  semantic_previous=semantic_previous)
        blocked += bool(issues)
        history.append(story)
        index.add(story)
        semantic_previous.append((story, _semantic_features(story)))
    audited = time.perf_counter()
    return {
        "count": count,
        "generation_seconds": round(generated - start, 4),
        "triage_seconds": round(triaged - generated, 4),
        "audit_seconds": round(audited - triaged, 4),
        "ready_for_review": len(review["ready_for_review"]),
        "needs_work": len(review["needs_work"]),
        "editorial_issues_present": blocked,
        "publication_enabled": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.count), indent=2, sort_keys=True))
