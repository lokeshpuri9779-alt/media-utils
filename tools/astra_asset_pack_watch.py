"""Read-only expiry monitor for ASTRA's verified Actions visual pack.

No artwork is uploaded, promoted, published or modified by this command.
GitHub's short-lived Actions artifacts are *not* permanent production storage.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


WORKFLOWS = (
    ".github/workflows/astra-v2-publish.yml",
    ".github/workflows/astra-v2-preload.yml",
    ".github/workflows/astra-v2-longform.yml",
)
ASSET_NAME = "astra-original-visual-pack"


def pinned_run_id(root: Path) -> int:
    values = []
    for rel in WORKFLOWS:
        source = (root / rel).read_text(encoding="utf-8")
        ids = re.findall(r"(?m)^\s+run-id:\s*(\d+)\s*$", source)
        if len(ids) != 1 or "--expected 3200" not in source:
            raise ValueError(f"unverified_asset_workflow:{rel}")
        values.append(int(ids[0]))
    if len(set(values)) != 1:
        raise ValueError("artwork_pack_run_id_mismatch")
    return values[0]


def inspect_artifacts(payload: dict, *, now: datetime, warning_days: float = 7.0) -> dict:
    matches = [item for item in payload.get("artifacts", [])
               if isinstance(item, dict) and item.get("name") == ASSET_NAME]
    if len(matches) != 1:
        return {"status": "missing_or_duplicate", "matching_artifacts": len(matches)}
    item = matches[0]
    try:
        expires = datetime.fromisoformat(str(item["expires_at"]).replace("Z", "+00:00"))
        if expires.tzinfo is None:
            raise ValueError("missing_timezone")
        remaining = (expires - now).total_seconds() / 86400
        size = int(item["size_in_bytes"])
        if size <= 0:
            raise ValueError("empty_artifact")
    except (KeyError, ValueError, TypeError):
        return {"status": "invalid_metadata"}
    status = ("expired" if item.get("expired") or remaining <= 0 else
              "renewal_required" if remaining <= warning_days else "ok")
    return {"status": status, "expires_at": expires.isoformat(),
            "days_remaining": round(remaining, 2),
            "artifact_id": item.get("id"), "size_bytes": size}


def github_artifacts(repo: str, run_id: int, token: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("invalid_repository")
    if not token:
        raise ValueError("github_token_missing")
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100"
    request = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "astra-visual-pack-expiry-check",
    })
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        run_id = pinned_run_id(root)
        data = github_artifacts(os.environ.get("GITHUB_REPOSITORY", ""),
                                run_id, os.environ.get("GH_TOKEN", ""))
        result = inspect_artifacts(data, now=datetime.now(timezone.utc))
    except Exception as exc:
        # Include error type only; never print credentials or API responses.
        result = {"status": "check_failed", "error_type": type(exc).__name__}
    print("ASTRA_PACK_CONTINUITY=" + json.dumps(result, sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("## ASTRA verified artwork pack\n\n")
            out.write(f"Status: **{result['status']}**\n\n")
            out.write(f"Details: \`{json.dumps(result, sort_keys=True)}\`\n")
    if result["status"] != "ok":
        print("ASTRA_PACK_ACTION=restore approved pack to durable, licensed storage "
              "and update all pinned workflow references BEFORE expiry")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
