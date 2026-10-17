"""Compare full editorial triage output and elapsed time for optional index mode.

Benchmark only: never promotes, approves, or publishes stories.
"""
import argparse
import json
import time
import statistics

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_editorial import triage


def benchmark(count=500, history_count=100, repeats=3):
    if not 1 <= count <= 1500 or not 0 <= history_count <= 1500:
        raise ValueError("count must be 1..1500 and history_count 0..1500")
    if not 1 <= repeats <= 10:
        raise ValueError("repeats must be 1..10")
    history = [proposal(i) for i in range(history_count)]
    stories = [proposal(i) for i in range(history_count, history_count + count)]
    durations = {"exhaustive": [], "indexed": []}
    reference = None
    for iteration in range(repeats):
        # Alternate execution order to reduce warm-cache/order bias.
        modes = ("exhaustive", "indexed") if iteration % 2 == 0 else ("indexed", "exhaustive")
        for mode in modes:
            start = time.perf_counter()
            result = triage(stories, history, use_semantic_index=(mode == "indexed"))
            durations[mode].append(time.perf_counter() - start)
            if reference is None:
                reference = result
            elif result != reference:
                raise AssertionError("Indexed triage changed the editorial review report")
    exhaustive_seconds = statistics.median(durations["exhaustive"])
    indexed_seconds = statistics.median(durations["indexed"])
    return {
        "candidate_count": count,
        "repeats": repeats,
        "alternating_execution_order": True,
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
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.count, args.history_count, args.repeats), indent=2, sort_keys=True))
