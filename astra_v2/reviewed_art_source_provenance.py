"""Fail-closed provenance check before consuming approved artwork Actions artifacts."""
import json
import re
import subprocess


def verify_source_run(repository, run_id, *, runner=None):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("invalid_source_repository")
    if not re.fullmatch(r"[0-9]{1,20}", str(run_id)):
        raise ValueError("invalid_source_run_id")
    runner = subprocess.run if runner is None else runner
    result = runner(["gh", "api", "-X", "GET",
                     f"repos/{repository}/actions/runs/{run_id}"],
                    capture_output=True, text=True, check=True)
    run = json.loads(result.stdout)
    if (run.get("id") != int(run_id)
            or run.get("repository", {}).get("full_name", "").casefold() != repository.casefold()
            or run.get("head_repository", {}).get("full_name", "").casefold() != repository.casefold()
            or run.get("head_branch") != "main"
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
            or run.get("event") not in {"workflow_dispatch", "push"}
            or not re.fullmatch(r"[a-f0-9]{40}", str(run.get("head_sha", "")))):
        raise ValueError("untrusted_approved_art_source_run")
    return run["head_sha"]
