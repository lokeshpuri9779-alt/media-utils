"""Compare full editorial triage output and elapsed time for optional index mode.

Benchmark only: never promotes, approves, or publishes stories.
"""
import argparse
import json
import time

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_editorial import triage


def benchmark(count=500, history_count=100):
    if not 1 <= count <= 1500 or not 0 <= history_count <= 1500:
        raise ValueError("count must be 1..1500 and history_count 0..1500")
    history = [proposal(i) for i in range(history_count)]
    stories = [proposal(i) for i in range(history_count, history_count + count)]
    start = time.perf_counter()
    reference = triage(stories, history)
    exhaustive_seconds = time.perf_counter() - start
    start = time.perf_counter()
    indexed = triage(stories, history, use_semantic_index=True)
    indexed_seconds = time.perf_counter() - start
    if reference != indexed:
        raise AssertionError("Indexed triage changed the editorial review report")
    return {
        "candidate_count": count,
        "history_count": history_count,
        "exhaustive_triage_seconds": round(exhaustive_seconds, 4),
        "indexed_triage_seconds": round(indexed_seconds, 4),
        "full_report_parity": True,
        "ready_for_review": len(reference["ready_for_review"]),
        "needs_work": len(reference["needs_work"]),
        "publication_enabled": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--history-count", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.count, args.history_count), indent=2, sort_keys=True))
