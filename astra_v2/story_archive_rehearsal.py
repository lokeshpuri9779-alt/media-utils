"""Offline-only ASTRA state-branch archive rehearsal.

Never writes to the live publisher state or starts an upload. Input files must
be restored from a trusted astra-state snapshot by the caller.
"""
import argparse
import json
import shutil
import tempfile
from pathlib import Path

from astra_v2.story_ledger import (
    StoryLedgerError, audit_committed_state, migrate_valid_fingerprints,
    verify_restored_archive,
)


def rehearse_state_restore(state_path, archive_path=None):
    state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    coverage = audit_committed_state(state)
    if coverage["invalid"] or coverage["conflicting"]:
        raise StoryLedgerError("story_publisher_history_untrusted")
    with tempfile.TemporaryDirectory(prefix="astra-archive-rehearsal-") as root:
        first = Path(root) / "runner-one"
        second = Path(root) / "runner-two"
        first.mkdir()
        second.mkdir()
        initial = first / "astra_story_fingerprints.json"
        if archive_path is not None:
            original = Path(archive_path)
            if not original.is_file():
                raise StoryLedgerError("story_ledger_restore_missing")
            shutil.copyfile(original, initial)
        migrated = migrate_valid_fingerprints(initial, state)
        shutil.copyfile(initial, second / initial.name)
        verified = verify_restored_archive(second / initial.name, state)
        return {
            "simulated_restart_verified": verified["verified"],
            "historical_coverage_complete": migrated["complete"],
            "coverage": coverage,
            "archived_count": verified["archived_count"],
            "live_state_modified": False,
        }


def main():
    parser = argparse.ArgumentParser(description="Read-only ASTRA archive recovery rehearsal")
    parser.add_argument("--state", required=True)
    parser.add_argument("--archive", default=None)
    args = parser.parse_args()
    print(json.dumps(rehearse_state_restore(args.state, args.archive), sort_keys=True))


if __name__ == "__main__":
    main()
