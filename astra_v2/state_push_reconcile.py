"""Rebase ASTRA state output only when remote writes touch entirely different files.

Never force-push, auto-merge overlapping edits, or overwrite a concurrent cursor.
"""
import argparse
import subprocess


class UnsafeStateAdvance(ValueError):
    pass


def git(*args):
    return subprocess.run(["git", *args], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE).stdout


def changed_files(start, end):
    return set(git("diff", "--no-renames", "--name-only", "-z", start, end).decode().split("\0")) - {""}


def reconcile(baseline, remote):
    """Return new safe baseline; raise before rebase if histories or paths overlap."""
    if subprocess.run(["git", "diff", "--quiet"]).returncode or subprocess.run(
            ["git", "diff", "--cached", "--quiet"]).returncode:
        raise UnsafeStateAdvance("dirty_tracked_state_worktree")
    if subprocess.run(["git", "merge-base", "--is-ancestor", baseline, "HEAD"]).returncode:
        raise UnsafeStateAdvance("local_commit_not_based_on_baseline")
    if subprocess.run(["git", "merge-base", "--is-ancestor", baseline, remote]).returncode:
        raise UnsafeStateAdvance("remote_history_diverged")
    if baseline == remote:
        return baseline
    local = changed_files(baseline, "HEAD")
    other = changed_files(baseline, remote)
    if not local:
        raise UnsafeStateAdvance("missing_local_changes")
    if local & other:
        raise UnsafeStateAdvance("overlapping_state_paths:" + ",".join(sorted(local & other)))
    # Only disjoint paths are rebased. Git itself must still succeed.
    try:
        git("rebase", remote)
    except subprocess.CalledProcessError as exc:
        subprocess.run(["git", "rebase", "--abort"], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        raise UnsafeStateAdvance("safe_rebase_failed") from exc
    if changed_files(remote, "HEAD") != local:
        raise UnsafeStateAdvance("rebase_changed_unexpected_paths")
    return remote


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--remote", required=True)
    args = parser.parse_args()
    try:
        print("ASTRA_STATE_BASELINE=" + reconcile(args.baseline, args.remote))
    except (UnsafeStateAdvance, subprocess.CalledProcessError) as exc:
        parser.exit(1, "ASTRA_STATE_CONFLICT: " + str(exc) + "\n")
