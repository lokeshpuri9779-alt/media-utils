"""Read-only end-to-end triage comparison; identical candidates, exact report parity."""
import argparse
import json
import time

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_editorial import triage


def benchmark(count=500):
    if not 1 <= count <= 1000:
        raise ValueError("count must be between 1 and 1000")
    stories = [proposal(i) for i in range(count)]
    start = time.perf_counter()
    exhaustive = triage(stories)
    exhaustive_seconds = time.perf_counter() - start
    start = time.perf_counter()
    indexed = triage(stories, use_semantic_index=True)
    indexed_seconds = time.perf_counter() - start
    if exhaustive != indexed:
        raise AssertionError("Indexed triage report differs from reference")
    return {
        "count": count,
        "exhaustive_seconds": round(exhaustive_seconds, 4),
        "indexed_seconds": round(indexed_seconds, 4),
        "report_parity": True,
        "ready_for_review": len(indexed["ready_for_review"]),
        "needs_work": len(indexed["needs_work"]),
        "publication_enabled": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.count), indent=2, sort_keys=True))
