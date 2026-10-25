"""Regression checks for verified-art inventory caching."""
import json
from pathlib import Path
from unittest.mock import patch

from astra_v2 import quality_asset_selector as selector


def test_immutable_cache_reuses_verified_inventory(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    (root / "art").mkdir()
    (root / "art" / "manifest.json").write_text(json.dumps({"assets": []}))
    calls = []
    def fake_validate(path):
        calls.append(path)
        return {"verified_files": 0, "assets": []}
    selector._verified_inventory.cache_clear()
    monkeypatch.setenv("ASTRA_ASSET_PACK_ENABLED", "1")
    monkeypatch.setenv("ASTRA_ASSET_PACK_IMMUTABLE", "1")
    with patch.object(selector, "validate_library", side_effect=fake_validate):
        assert selector.select_assets(root, kind="background") == []
        assert selector.select_assets(root, kind="background") == []
    assert len(calls) == 1
    selector._verified_inventory.cache_clear()


def test_default_revalidates_after_change(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    (root / "art").mkdir()
    manifest = root / "art" / "manifest.json"
    manifest.write_text(json.dumps({"assets": []}))
    calls = []
    def fake_validate(path):
        calls.append(path)
        if len(calls) == 2:
            raise ValueError("modified asset")
        return {"verified_files": 0, "assets": []}
    monkeypatch.delenv("ASTRA_ASSET_PACK_IMMUTABLE", raising=False)
    monkeypatch.setenv("ASTRA_ASSET_PACK_ENABLED", "1")
    with patch.object(selector, "validate_library", side_effect=fake_validate):
        assert selector.select_assets(root, kind="background") == []
        try:
            selector.select_assets(root, kind="background")
        except ValueError as exc:
            assert str(exc) == "modified asset"
        else:
            raise AssertionError("modified asset bypassed validation")
    assert len(calls) == 2
