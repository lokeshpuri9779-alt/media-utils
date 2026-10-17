"""Read-only, deterministic novelty benchmark for future mystery proposals.

Fixed history and disjoint index windows make runs comparable. No approvals.
"""
import argparse
import json
from astra_v2.autonomous_story_proposals import proposal
from astra_v2.proposal_novelty_index import NoveltyIndex
from astra_v2.story_editorial import _semantic_features, _semantic_match_features


def benchmark(history_start=0, history_count=200, sample_start=10000, sample_count=100):
    if min(history_start, history_count, sample_start, sample_count) < 0:
        raise ValueError("Negative index or count")
    if not history_count or not sample_count or history_count > 10000 or sample_count > 1000:
        raise ValueError("Benchmark size out of range")
    if not (sample_start >= history_start + history_count or
            history_start >= sample_start + sample_count):
        raise ValueError("History and sample index windows overlap")
    history = [proposal(i) for i in range(history_start, history_start + history_count)]
    novelty = NoveltyIndex(history)
    semantic = [(story, _semantic_features(story)) for story in history]
    duplicate_count = 0
    duplicate_by_index = []
    for i in range(sample_start, sample_start + sample_count):
        story = proposal(i)
        flagged = novelty.is_near_duplicate(story) or (
            _semantic_match_features(story, _semantic_features(story), semantic, 0.72) is not None
        )
        if flagged:
            duplicate_count += 1
            duplicate_by_index.append(i)
        # Do not add sampled candidates to history: this is a fixed-baseline
        # benchmark, not a simulated publication or ledger mutation.
    return {
        "history_start": history_start,
        "history_count": history_count,
        "sample_start": sample_start,
        "sample_count": sample_count,
        "duplicate_count": duplicate_count,
        "duplicate_rate": round(duplicate_count / sample_count, 4),
        "duplicate_indices": duplicate_by_index,
        "publication_approved": 0,
        "history_mutated": False,
    }


def compare_generators(history_start=0, history_count=200, sample_start=10000, sample_count=100):
    """Compare old and current generator against identical frozen legacy history."""
    from astra_v2.mystery_generator_baseline import legacy_proposal
    from astra_v2.autonomous_story_proposals import proposal as current_proposal
    if min(history_start, history_count, sample_start, sample_count) < 0:
        raise ValueError("Negative index or count")
    if not history_count or not sample_count or history_count > 10000 or sample_count > 1000:
        raise ValueError("Benchmark size out of range")
    if not (sample_start >= history_start + history_count or
            history_start >= sample_start + sample_count):
        raise ValueError("History and sample index windows overlap")
    history = [legacy_proposal(i) for i in range(history_start, history_start + history_count)]
    novelty = NoveltyIndex(history)
    semantic = [(story, _semantic_features(story)) for story in history]
    results = {}
    for label, generator in (("legacy", legacy_proposal), ("current", current_proposal)):
        duplicates = []
        for index in range(sample_start, sample_start + sample_count):
            story = generator(index)
            if novelty.is_near_duplicate(story) or _semantic_match_features(
                story, _semantic_features(story), semantic, 0.72
            ) is not None:
                duplicates.append(index)
        results[label] = {
            "duplicate_count": len(duplicates),
            "duplicate_rate": round(len(duplicates) / sample_count, 4),
            "duplicate_indices": duplicates,
        }
    return {
        "history_start": history_start,
        "history_count": history_count,
        "sample_start": sample_start,
        "sample_count": sample_count,
        "results": results,
        "duplicate_rate_change": round(results["current"]["duplicate_rate"] - results["legacy"]["duplicate_rate"], 4),
        "publication_approved": 0,
        "history_mutated": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-start", type=int, default=0)
    parser.add_argument("--history-count", type=int, default=200)
    parser.add_argument("--sample-start", type=int, default=10000)
    parser.add_argument("--sample-count", type=int, default=100)
    args = parser.parse_args()
    print("ASTRA_MYSTERY_GENERATOR_COMPARISON=" + json.dumps(compare_generators(
        args.history_start, args.history_count, args.sample_start, args.sample_count
    ), sort_keys=True))
    print("ASTRA_MYSTERY_NOVELTY_BENCHMARK=" + json.dumps(benchmark(
        args.history_start, args.history_count, args.sample_start, args.sample_count
    ), sort_keys=True))
