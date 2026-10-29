"""Real-git regression tests for fail-closed ASTRA state push reconciliation."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from astra_v2.state_push_reconcile import UnsafeStateAdvance, reconcile


class StatePushReconcileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmp.name)
        self.run_git("init", "-q")
        self.run_git("config", "user.name", "Test")
        self.run_git("config", "user.email", "test@example.invalid")
        Path("story.json").write_text("original")
        Path("journal.json").write_text("original")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "base")
        self.base = self.run_git("rev-parse", "HEAD").strip()
        self.run_git("switch", "-qc", "local")
        Path("story.json").write_text("new reviewed story")
        self.run_git("commit", "-qam", "local story batch")
        self.local = self.run_git("rev-parse", "HEAD").strip()

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def run_git(self, *args):
        return subprocess.check_output(["git", *args], text=True)

    def remote_commit(self, file, value):
        self.run_git("switch", "-qc", "other", self.base)
        Path(file).write_text(value)
        self.run_git("commit", "-qam", "concurrent writer")
        sha = self.run_git("rev-parse", "HEAD").strip()
        self.run_git("switch", "-q", "local")
        return sha

    def test_disjoint_remote_journal_is_preserved_without_force_push(self):
        remote = self.remote_commit("journal.json", "new publisher journal")
        Path("diagnostic-untracked.json").write_text("not committed")
        self.assertEqual(reconcile(self.base, remote), remote)
        self.assertEqual(Path("story.json").read_text(), "new reviewed story")
        self.assertEqual(Path("journal.json").read_text(), "new publisher journal")
        self.assertEqual(self.run_git("rev-list", "--count", remote + "..HEAD").strip(), "1")
        self.assertEqual(self.run_git("merge-base", "HEAD", remote).strip(), remote)

    def test_overlapping_remote_story_change_fails_without_rebase(self):
        remote = self.remote_commit("story.json", "concurrent story batch")
        with self.assertRaisesRegex(UnsafeStateAdvance, "overlapping_state_paths"):
            reconcile(self.base, remote)
        self.assertEqual(self.run_git("rev-parse", "HEAD").strip(), self.local)
        self.assertEqual(Path("story.json").read_text(), "new reviewed story")

    def test_uncommitted_tracked_edits_fail_closed(self):
        remote = self.remote_commit("journal.json", "new publisher journal")
        Path("journal.json").write_text("dirty local journal")
        with self.assertRaisesRegex(UnsafeStateAdvance, "dirty_tracked_state_worktree"):
            reconcile(self.base, remote)
        self.assertEqual(self.run_git("rev-parse", "HEAD").strip(), self.local)


if __name__ == "__main__":
    unittest.main()
