"""Opt-in post-publication continuity persistence, isolated from uploads."""
import json
import os
from pathlib import Path
import tempfile

from astra_v2.character_snapshot import read_snapshot
from astra_v2.verified_character_memory import update_after_verified_publication


def apply_published_episode(snapshot_path, proposal_path, episode_path, report_path):
    """Update existing snapshot only when all four artifacts are present and valid.

    No character is invented. Caller must supply a matching approved episode
    manifest and confirmed publication report. Exceptions leave snapshot intact.
    """
    snapshot_path = Path(snapshot_path)
    snapshot = read_snapshot(snapshot_path)
    with Path(proposal_path).open(encoding="utf-8") as f:
        proposal = json.load(f)
    with Path(episode_path).open(encoding="utf-8") as f:
        episode = json.load(f)
    with Path(report_path).open(encoding="utf-8") as f:
        report = json.load(f)
    updated = update_after_verified_publication(snapshot, proposal, episode, report)
    fd, tmp_name = tempfile.mkstemp(prefix=".character-verified-", dir=snapshot_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(updated, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, snapshot_path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return updated
