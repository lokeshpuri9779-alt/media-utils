"""Discover an immutable approved-art index from trusted completed producer runs.

Never trusts arbitrary workflow artifacts or pull-request branches.
"""
import json
import re
import subprocess
from pathlib import Path


def select_producer_run(runs, *, workflow="astra-reviewed-art-producer.yml"):
    if not isinstance(runs, list):
        raise ValueError("invalid_producer_run_listing")
    for run in sorted(runs, key=lambda x: x.get("run_number", 0), reverse=True):
        if (run.get("path", "").split("@")[0].endswith("/" + workflow)
                and run.get("event") == "workflow_dispatch"
                and run.get("head_branch") == "main"
                and run.get("status") == "completed"
                and run.get("conclusion") == "success"
                and isinstance(run.get("id"), int)):
            return run["id"]
    raise ValueError("no_trusted_approved_art_producer_run")


def discover_index(repository, destination, *, runner=None):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("invalid_repository")
    runner = subprocess.run if runner is None else runner
    result = runner(["gh", "api", "--paginate", "-X", "GET",
                     f"repos/{repository}/actions/workflows/astra-reviewed-art-producer.yml/runs",
                     "-f", "branch=main", "-f", "status=completed", "-f", "per_page=50",
                     "--jq", ".workflow_runs[] | @json"],
                    capture_output=True, text=True, check=True)
    runs = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    run_id = select_producer_run(runs)
    target = Path(destination)
    if target.exists():
        raise ValueError("art_receipt_destination_exists")
    target.mkdir(parents=True)
    try:
        runner(["gh", "run", "download", str(run_id), "--repo", repository,
                "--name", f"astra-approved-art-index-{run_id}", "--dir", str(target)],
               capture_output=True, text=True, check=True)
        receipt = target / "reviewed-art-index-receipt.json"
        if receipt.is_symlink() or not receipt.is_file() or receipt.stat().st_size > 4096:
            raise ValueError("invalid_discovered_art_receipt")
        return receipt
    except Exception:
        import shutil
        shutil.rmtree(target)
        raise
