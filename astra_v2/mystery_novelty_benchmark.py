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



def compare_against_legacy_counterparts(sample_start=10000, sample_count=100):
    """Hard-negative comparison: each candidate faces its same-index old draft.

    Reports exact/near-duplicate flags, not a claim of creative quality.
    """
    from astra_v2.mystery_generator_baseline import legacy_proposal
    from astra_v2.autonomous_story_proposals import proposal as current_proposal
    if sample_start < 0 or not 1 <= sample_count <= 1000:
        raise ValueError("Invalid counterpart window")
    results = {}
    for label, generator in (("legacy", legacy_proposal), ("current", current_proposal)):
        duplicates = []
        for index in range(sample_start, sample_start + sample_count):
            prior = legacy_proposal(index)
            candidate = generator(index)
            if NoveltyIndex([prior]).is_near_duplicate(candidate) or _semantic_match_features(
                candidate, _semantic_features(candidate), [(prior, _semantic_features(prior))], 0.72
            ) is not None:
                duplicates.append(index)
        results[label] = {
            "duplicate_count": len(duplicates),
            "duplicate_rate": round(len(duplicates) / sample_count, 4),
            "duplicate_indices": duplicates,
        }
    return {
        "sample_start": sample_start,
        "sample_count": sample_count,
        "results": results,
        "duplicate_rate_change": round(results["current"]["duplicate_rate"] - results["legacy"]["duplicate_rate"], 4),
        "publication_approved": 0,
        "history_mutated": False,
        "interpretation": "same-index legacy counterpart overlap; not a real-world editorial novelty rate",
    }


def measure_sequential_novelty(sample_start=0, sample_count=300):
    """Measure actual generated sequence pressure, adding each accepted candidate.

    This is a synthetic in-memory diagnostic; never modifies the story ledger.
    """
    if sample_start < 0 or not 1 <= sample_count <= 1000:
        raise ValueError("Invalid sequential window")
    index = NoveltyIndex([])
    accepted = []
    semantic = []
    duplicate_indices = []
    for candidate_index in range(sample_start, sample_start + sample_count):
        candidate = proposal(candidate_index)
        if index.is_near_duplicate(candidate) or _semantic_match_features(
            candidate, _semantic_features(candidate), semantic, 0.72
        ) is not None:
            duplicate_indices.append(candidate_index)
        else:
            accepted.append(candidate)
            index.add(candidate)
            semantic.append((candidate, _semantic_features(candidate)))
    return {
        "sample_start": sample_start,
        "sample_count": sample_count,
        "accepted_count": len(accepted),
        "duplicate_count": len(duplicate_indices),
        "duplicate_rate": round(len(duplicate_indices) / sample_count, 4),
        "duplicate_indices": duplicate_indices,
        "publication_approved": 0,
        "history_mutated": False,
    }


def measure_sequential_rejection_reasons(sample_start=0, sample_count=200):
    """Attribute duplicate flags to conservative novelty and semantic screens.

    Flags may overlap; no thresholds or publishing decisions are changed.
    """
    if sample_start < 0 or not 1 <= sample_count <= 1000:
        raise ValueError("Invalid sequential window")
    novelty = NoveltyIndex([])
    semantic = []
    counts = {"novelty_only": 0, "semantic_only": 0, "both": 0, "accepted": 0}
    for i in range(sample_start, sample_start + sample_count):
        candidate = proposal(i)
        novelty_hit = novelty.is_near_duplicate(candidate)
        semantic_hit = _semantic_match_features(
            candidate, _semantic_features(candidate), semantic, 0.72
        ) is not None
        if novelty_hit and semantic_hit:
            counts["both"] += 1
        elif novelty_hit:
            counts["novelty_only"] += 1
        elif semantic_hit:
            counts["semantic_only"] += 1
        else:
            counts["accepted"] += 1
            novelty.add(candidate)
            semantic.append((candidate, _semantic_features(candidate)))
    return {
        "sample_start": sample_start,
        "sample_count": sample_count,
        "reason_counts": counts,
        "publication_approved": 0,
        "history_mutated": False,
    }

def diagnose_duplicate_pressure(sample_start=0, sample_count=200):
    """Read-only collision attribution by accepted-story plot and architecture.

    The same conservative screens decide acceptance; diagnostics never approve
    or write a candidate into the production ledger.
    """
    from collections import Counter
    from astra_v2.autonomous_story_proposals import PLOT_ENGINES, NARRATIVE_ARCHITECTURES
    if sample_start < 0 or not 1 <= sample_count <= 1000:
        raise ValueError("Invalid sequential window")
    novelty = NoveltyIndex([])
    semantic = []
    collisions = Counter()
    accepted = Counter()
    for i in range(sample_start, sample_start + sample_count):
        candidate = proposal(i)
        plot = (i // 11) % len(PLOT_ENGINES)
        architecture = (i // 5) % len(NARRATIVE_ARCHITECTURES)
        novelty_hit = novelty.is_near_duplicate(candidate)
        semantic_hit = _semantic_match_features(
            candidate, _semantic_features(candidate), semantic, 0.72
        ) is not None
        if novelty_hit or semantic_hit:
            collisions[(plot, architecture, "both" if novelty_hit and semantic_hit else
                        "novelty_only" if novelty_hit else "semantic_only")] += 1
        else:
            accepted[(plot, architecture)] += 1
            novelty.add(candidate)
            semantic.append((candidate, _semantic_features(candidate)))
    return {
        "sample_start": sample_start,
        "sample_count": sample_count,
        "accepted_count": sum(accepted.values()),
        "rejected_count": sum(collisions.values()),
        "collisions": [
            {"plot": p, "architecture": a, "reason": reason, "count": count}
            for (p, a, reason), count in sorted(collisions.items())
        ],
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
    print("ASTRA_MYSTERY_REJECTION_REASONS=" + json.dumps(measure_sequential_rejection_reasons(
        args.history_start, args.history_count
    ), sort_keys=True))
    print("ASTRA_MYSTERY_SEQUENTIAL_NOVELTY=" + json.dumps(measure_sequential_novelty(
        args.history_start, args.history_count
    ), sort_keys=True))
    print("ASTRA_MYSTERY_COUNTERPART_COMPARISON=" + json.dumps(compare_against_legacy_counterparts(
        args.sample_start, args.sample_count
    ), sort_keys=True))
    print("ASTRA_MYSTERY_GENERATOR_COMPARISON=" + json.dumps(compare_generators(
        args.history_start, args.history_count, args.sample_start, args.sample_count
    ), sort_keys=True))
    print("ASTRA_MYSTERY_NOVELTY_BENCHMARK=" + json.dumps(benchmark(
        args.history_start, args.history_count, args.sample_start, args.sample_count
    ), sort_keys=True))
