import json, tempfile, unittest
from pathlib import Path
import backup_state

class BackupTests(unittest.TestCase):
    def test_secret_safe_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            old_root,old_backups=backup_state.ROOT,backup_state.BACKUPS
            try:
                backup_state.ROOT=Path(d); backup_state.BACKUPS=Path(d)/"backups"
                (Path(d)/"performance.json").write_text("{}")
                out=backup_state.snapshot("test")
                m=json.loads((out/"manifest.json").read_text())
                self.assertFalse(m["secrets_included"])
                self.assertNotIn(".env",m["files"])
            finally:
                backup_state.ROOT,backup_state.BACKUPS=old_root,old_backups

if __name__=="__main__": unittest.main()
