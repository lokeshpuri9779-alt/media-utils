"""Inspect GitHub Actions publisher/preload executions with read-only token.

Never dispatch, rerun, cancel or modify a workflow; only the workflows/run
metadata endpoint is queried. Output includes no credentials or source files.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

WORKFLOWS = {
    "publisher": "astra-v2-publish.yml",
    "preloader": "astra-v2-preload.yml",
    "gemini_batch": "astra-gemini-proposal-batch.yml",
}


def collect(repo, token, *, transport=None):
    if not isinstance(repo, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid repository identifier")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("Read-only GitHub Actions token missing")
    fetch = transport or urllib.request.urlopen
    result = {}
    for label, workflow in WORKFLOWS.items():
        url = (f"https://api.github.com/repos/{repo}/actions/workflows/"
               f"{workflow}/runs?per_page=5")
        request = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
        })
        try:
            with fetch(request, timeout=18) as response:
                payload = json.load(response)
        except (OSError, TimeoutError, ValueError) as exc:
            # Never log token, URL, raw response, or exception text.
            raise RuntimeError(
                "Workflow run metadata unavailable: " + label + " / "
                + type(exc).__name__) from None
        runs = payload.get("workflow_runs")
        if not isinstance(runs, list) or len(runs) > 5:
            raise ValueError("Invalid workflow run listing: " + label)
        records = []
        for item in runs:
            if not isinstance(item, dict) or type(item.get("id")) is not int:
                raise ValueError("Invalid run metadata: " + label)
            records.append({
                "run_id": item["id"],
                "event": str(item.get("event") or "")[:24],
                "status": str(item.get("status") or "")[:30],
                "conclusion": str(item.get("conclusion") or "")[:30],
                "created_at": str(item.get("created_at") or "")[:38],
                "updated_at": str(item.get("updated_at") or "")[:38],
                "head_sha": str(item.get("head_sha") or "")[:40],
            })
        result[label] = records
    return {
        "kind": "astra_readonly_github_actions_execution_v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "workflows": result,
        "only_metadata_accessed": True,
        "workflow_dispatched": False,
        "production_modified": False,
        "paid_provider_called": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = collect(os.getenv("GITHUB_REPOSITORY", ""),
                     os.getenv("GITHUB_TOKEN", ""))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("ASTRA_PUBLISHER_RUNS=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
