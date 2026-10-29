"""Offline regression for review-only scene asset conflict-recovery uploads."""
import subprocess
import tempfile
import unittest
from pathlib import Path


class SceneAssetArchiveGateTests(unittest.TestCase):
    def test_workflow_keeps_diagnostics_but_gates_bulk_asset_archive(self):
        workflow = Path(".github/workflows/astra-story-factory.yml").read_text()
        self.assertIn("id: scene_asset_delta", workflow)
        self.assertIn("git status --porcelain --untracked-files=all -- omni_assets/", workflow)
        self.assertIn("if: always() && steps.scene_asset_delta.outputs.changed == 'true'", workflow)
        self.assertIn("name: astra-story-factory-diagnostics-", workflow)
        self.assertIn("name: astra-story-factory-scene-assets-", workflow)
        self.assertIn("retention-days: 14", workflow)

    def test_git_delta_detection_is_empty_for_cached_and_nonempty_for_new_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.run(["git", *args], cwd=root, check=True,
                                      capture_output=True, text=True).stdout
            git("init", "-q")
            git("config", "user.name", "ASTRA Test")
            git("config", "user.email", "astra-test@example.invalid")
            folder = root / "omni_assets" / "sha256"
            folder.mkdir(parents=True)
            tracked = folder / "cached.png"
            tracked.write_bytes(b"existing cached image")
            git("add", "omni_assets/")
            git("commit", "-qm", "existing cached asset")
            def changed():
                return bool(git("status", "--porcelain", "--untracked-files=all",
                                "--", "omni_assets/").strip())
            self.assertFalse(changed(), "unchanged cached assets should not be reuploaded")
            (root / "unrelated.txt").write_text("not an image")
            self.assertFalse(changed(), "unrelated state changes do not need scene ZIP")
            fresh = folder / "new.png"
            fresh.write_bytes(b"new review-only image")
            self.assertTrue(changed(), "new images must retain conflict-recovery archive")
            fresh.unlink()
            tracked.write_bytes(b"changed review-only image")
            self.assertTrue(changed(), "modified images must retain conflict-recovery archive")


if __name__ == "__main__":
    unittest.main()
