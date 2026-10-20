"""Eight isolated generation workers, one novelty gate, one ledger writer.

Executed inside the existing serialized proposal workflow. No publishing.
"""
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from astra_v2.global_story_novelty import filter_global_novelty
from astra_v2.isolated_story_worker import generate_worker
from astra_v2.parallel_story_workers import WORKERS, STORIES_PER_RUN, combine_workers, read_worker_payload
from astra_v2.proposal_history import load_history
from astra_v2.single_writer_story_ledger import commit_screened_batch, snapshot_token


def replenish_parallel(path, *, batch_id, workers=WORKERS, total=STORIES_PER_RUN):
    target = Path(path)
    if target.exists():
        ledger = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(ledger, dict) or not isinstance(ledger.get("proposals"), list):
            raise ValueError("invalid_ledger")
    else:
        ledger = {"next_index": 0, "proposals": []}
    start = ledger.get("next_index", 0)
    if not isinstance(start, int) or isinstance(start, bool) or start < 0:
        raise ValueError("invalid_start_index")
    before = snapshot_token(target)
    with tempfile.TemporaryDirectory(prefix="astra-workers-") as root:
        def run_worker(i):
            directory = Path(root) / str(i)
            generate_worker(batch_id, i, start, directory, workers=workers, total=total)
            return read_worker_payload(directory / "checkpoint.json",
                                       directory / "stories.json",
                                       batch_id=batch_id, worker_index=i)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            outputs = list(executor.map(run_worker, range(workers)))
        combined = combine_workers(batch_id, outputs, expected_workers=workers, expected_total=total)
    screened = filter_global_novelty(combined, existing=ledger["proposals"], history=load_history())
    accepted = commit_screened_batch(target, screened, expected_snapshot=before,
                                     next_index=start + total)
    print("ASTRA_PARALLEL_WORKERS=" + str(workers))
    print("ASTRA_PARALLEL_PROPOSED=" + str(total))
    print("ASTRA_PARALLEL_ACCEPTED=" + str(accepted))
    print("ASTRA_PARALLEL_REJECTED=" + str(len(screened["rejected"])))
    print("ASTRA_PARALLEL_APPROVED=0")
    return accepted


if __name__ == "__main__":
    replenish_parallel(
        os.getenv("ASTRA_PROPOSAL_LEDGER", "runtime-health/story_proposals.json"),
        batch_id=os.environ["GITHUB_RUN_ID"] + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
