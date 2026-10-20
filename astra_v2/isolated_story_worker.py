"""Isolated deterministic ASTRA candidate generation; no shared-ledger writes.

A worker proposes candidates from a disjoint index stripe. The coordinator
must still perform global novelty checks before committing any candidates.
"""
import argparse
import json
from pathlib import Path

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.parallel_story_workers import WORKERS, STORIES_PER_RUN, worker_allocation
from astra_v2.story_batch_checkpoint import checkpoint_record, write_checkpoint


def worker_indices(start_index, worker_index, *, workers=WORKERS, total=STORIES_PER_RUN):
    if not isinstance(start_index, int) or isinstance(start_index, bool) or start_index < 0:
        raise ValueError("invalid_start_index")
    if not isinstance(worker_index, int) or isinstance(worker_index, bool) or not 0 <= worker_index < workers:
        raise ValueError("invalid_worker_index")
    count = worker_allocation(total, workers)[worker_index]
    # A fixed stripe avoids collisions even if worker completion order varies.
    return [start_index + worker_index + i * workers for i in range(count)]


def generate_worker(batch_id, worker_index, start_index, output_dir, *,
                    workers=WORKERS, total=STORIES_PER_RUN):
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("invalid_batch_id")
    stories = [proposal(index) for index in worker_indices(
        start_index, worker_index, workers=workers, total=total)]
    if any(story.get("production_ready") is not False for story in stories):
        raise ValueError("unexpected_production_ready")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    stories_path = root / "stories.json"
    checkpoint_path = root / "checkpoint.json"
    if stories_path.exists() or checkpoint_path.exists():
        raise FileExistsError("worker_output_already_exists")
    # A checkpoint is marked complete only after the story output is written.
    stories_path.write_text(json.dumps({"stories": stories}, indent=2) + "\n", encoding="utf-8")
    write_checkpoint(checkpoint_path, checkpoint_record(
        f"{batch_id}-worker-{worker_index}", "generated",
        [story["content_id"] for story in stories], complete=True))
    return len(stories)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--worker-index", type=int, required=True)
    parser.add_argument("--start-index", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    print("ASTRA_ISOLATED_UNREVIEWED_CANDIDATES=" + str(generate_worker(
        args.batch_id, args.worker_index, args.start_index, args.output_dir)))


if __name__ == "__main__":
    main()
