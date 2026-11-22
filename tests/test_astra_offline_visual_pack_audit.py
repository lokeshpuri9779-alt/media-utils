"""Offline negative controls for actual archived visual-library integrity and fit."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image

from tools import astra_offline_visual_pack_audit as audit


def fixture_zip(path: Path, *, tamper_sha=False, missing=False,
                unknown_extra=False, wrong_kind=False, unsafe_path=False) -> Path:
    files = {}
    rows = []
    for name, theme, dimensions, layout in [
        ("garden-0001", "garden", (540, 960), "shorts"),
        ("harbor-0002", "harbor", (1280, 720), "long"),
    ]:
        buf = BytesIO()
        Image.new("RGB", dimensions, (60, 90, 110)).save(buf, "PNG")
        raw = buf.getvalue()
        filename = f"art/{layout}/backgrounds/{name}.png"
        row = {
            "id": f"{layout}-{name}",
            "path": filename,
            "kind": "character" if wrong_kind else "background",
            "license": "original",
            "source": "test fixture only",
            "tags": [theme, "background", layout, "environment"],
            "sha256": ("0" * 64) if tamper_sha else hashlib.sha256(raw).hexdigest(),
        }
        # Distinct hashes for the two elements with distinct dimensions.
        rows.append(row)
        if not (missing and layout == "long"):
            files[filename] = raw
    if unsafe_path:
        rows[0]["path"] = "art/../secrets.png"
    if unknown_extra:
        files["art/shorts/backgrounds/other.png"] = b"extra"
    files[audit.MANIFEST] = json.dumps({"assets": rows}).encode()
    inner = BytesIO()
    with ZipFile(inner, "w", ZIP_DEFLATED) as zipped:
        for name, content in files.items():
            zipped.writestr(name, content)
    with ZipFile(path, "w", ZIP_DEFLATED) as outer:
        outer.writestr(audit.ZIP_NAME, inner.getvalue())
    return path


class VisualPackAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.patcher = patch.dict(audit.SAMPLE_HINTS, {
            "glasshouse-sunshade": ("garden", "garden"),
            "footbridge-ducklings": ("garden", "garden"),
            "moon-mirror-garden": ("garden", "garden"),
        }, clear=True)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def _audit(self, **kwargs):
        archive = fixture_zip(self.root / "artifact.zip", **kwargs)
        return audit.audit_pack(archive, self.root / "out", expected=2)

    def test_verified_backgrounds_still_fail_story_coverage(self):
        report = self._audit()
        self.assertEqual(report["verified_asset_count"], 2)
        self.assertEqual(report["verified_unique_image_sha256_count"], 2)
        self.assertEqual(report["kinds"], {"background": 2})
        self.assertEqual(report["formats_by_orientation"], {"long": 1, "shorts": 1})
        self.assertFalse(report["asset_only_route_ready"])
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["approved"])
        self.assertFalse(report["published"])
        self.assertFalse(report["legal_rights_independently_verified"])
        self.assertEqual(len(report["storyboards"]), 3)
        for case in report["storyboards"]:
            self.assertEqual(case["planned_shots"], 4)
            self.assertEqual(case["missing_asset_types"], ["character", "prop"])
            self.assertFalse(case["asset_only_story_renderable"])
        self.assertTrue((self.root / "out/candidate-backgrounds.png").is_file())
        self.assertTrue((self.root / "out/coverage-report.json").is_file())

    def test_corrupted_digests_rejected_before_coverage_claim(self):
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            self._audit(tamper_sha=True)

    def test_missing_assets_and_unreferenced_entries_rejected(self):
        with self.assertRaisesRegex(ValueError, "manifest assets or ZIP files"):
            self._audit(missing=True)
        with self.assertRaisesRegex(ValueError, "manifest assets or ZIP files"):
            self._audit(unknown_extra=True)

    def test_unknown_asset_types_not_silently_approved(self):
        with self.assertRaisesRegex(ValueError, "unexpected asset kind"):
            self._audit(wrong_kind=True)

    def test_parent_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, "asset path"):
            self._audit(unsafe_path=True)

    def test_count_contract_is_bounded(self):
        with self.assertRaisesRegex(ValueError, "asset-count"):
            audit.audit_pack(self.root / "missing.zip", self.root / "out", expected=0)
        with self.assertRaisesRegex(ValueError, "asset-count"):
            audit.audit_pack(self.root / "missing.zip", self.root / "out", expected=9999)

    def test_artifact_zip_and_already_unwrapped_inner_zip_identical(self):
        original = fixture_zip(self.root / "artifact.zip")
        with ZipFile(original) as outer:
            (self.root / "inner.zip").write_bytes(outer.read(audit.ZIP_NAME))
        one = audit.audit_pack(original, self.root / "outer", expected=2)
        two = audit.audit_pack(self.root / "inner.zip", self.root / "inner", expected=2)
        self.assertEqual(one, two)

    def test_duplicate_ids_rejected(self):
        src = fixture_zip(self.root / "artifact.zip")
        with ZipFile(src) as wrapper:
            with ZipFile(BytesIO(wrapper.read(audit.ZIP_NAME))) as inner:
                rows = json.loads(inner.read(audit.MANIFEST))
                entries = {n: inner.read(n) for n in inner.namelist()}
        rows["assets"][1]["id"] = rows["assets"][0]["id"]
        entries[audit.MANIFEST] = json.dumps(rows).encode()
        with ZipFile(self.root / "duplicate.zip", "w", ZIP_DEFLATED) as outer:
            buf = BytesIO()
            with ZipFile(buf, "w", ZIP_DEFLATED) as w:
                for name, raw in entries.items():
                    w.writestr(name, raw)
            outer.writestr(audit.ZIP_NAME, buf.getvalue())
        with self.assertRaisesRegex(ValueError, "duplicate or missing asset id"):
            audit.audit_pack(self.root / "duplicate.zip", self.root / "out", expected=2)


if __name__ == "__main__":
    unittest.main()
