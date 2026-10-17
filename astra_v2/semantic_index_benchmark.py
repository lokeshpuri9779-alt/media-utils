"""Read-only benchmark of exhaustive versus indexed semantic matching.

No production state, approval, or publication is touched.
"""
import argparse
import json
import time

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.semantic_candidate_index import SemanticCandidateIndex
from astra_v2.story_editorial import semantic_duplicate_match


def benchmark(count=500, probes=100):
    if not 1 <= count <= 2000 or not 1 <= probes <= 500:
        raise ValueError("count must be 1..2000 and probes 1..500")
    history = [proposal(i) for i in range(count)]
    queries = [proposal(i) for i in range(count // 2, count // 2 + probes)]
    started = time.perf_counter()
    reference = [semantic_duplicate_match(story, history) for story in queries]
    exhaustive_seconds = time.perf_counter() - started
    started = time.perf_counter()
    index = SemanticCandidateIndex(history)
    build_seconds = time.perf_counter() - started
    started = time.perf_counter()
    indexed = [index.match(story) for story in queries]
    indexed_seconds = time.perf_counter() - started
    mismatches = [i for i, (a, b) in enumerate(zip(reference, indexed)) if a != b]
    result = {
        "history_count": count,
        "probe_count": probes,
        "exhaustive_seconds": round(exhaustive_seconds, 4),
        "index_build_seconds": round(build_seconds, 4),
        "indexed_query_seconds": round(indexed_seconds, 4),
        "mismatch_count": len(mismatches),
        "publication_enabled": False,
    }
    if mismatches:
        raise AssertionError(f"Indexed comparison disagrees for probes: {mismatches[:10]}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--probes", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.count, args.probes), indent=2, sort_keys=True))
