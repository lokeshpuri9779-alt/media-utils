"""Regression checks for decoded background cache integrity."""
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from astra_v2 import visual_artifact_backdrop as backdrop


def test_mutable_pack_does_not_use_decoded_cache(tmp_path, monkeypatch):
    root = tmp_path / "pack"
    (root / "art").mkdir(parents=True)
    (root / "art" / "manifest.json").write_text('{"assets": []}')
    monkeypatch.setenv("ASTRA_ASSET_PACK_ENABLED", "1")
    monkeypatch.delenv("ASTRA_ASSET_PACK_IMMUTABLE", raising=False)
    backdrop._cached_pack_background.cache_clear()
    shot = {"scene_environment": "railway station"}
    image = Image.new("RGB", (100, 180), (10, 20, 30))
    calls = []
    def loader(*args):
        calls.append(args)
        return None
    with patch.object(backdrop._cached_pack_background, "__wrapped__", loader):
        backdrop.apply_pack_background(image, shot, "same-identity", root=root)
        backdrop.apply_pack_background(image, shot, "same-identity", root=root)
    assert len(calls) == 2


def test_immutable_pack_uses_decoded_cache(tmp_path, monkeypatch):
    root = tmp_path / "pack"
    (root / "art").mkdir(parents=True)
    (root / "art" / "manifest.json").write_text('{"assets": []}')
    monkeypatch.setenv("ASTRA_ASSET_PACK_ENABLED", "1")
    monkeypatch.setenv("ASTRA_ASSET_PACK_IMMUTABLE", "1")
    backdrop._cached_pack_background.cache_clear()
    shot = {"scene_environment": "railway station"}
    image = Image.new("RGB", (100, 180), (10, 20, 30))
    calls = []
    def loader(*args):
        calls.append(args)
        return None
    with patch.object(backdrop, "_cached_pack_background", loader):
        backdrop.apply_pack_background(image, shot, "same-identity", root=root)
        backdrop.apply_pack_background(image, shot, "same-identity", root=root)
    assert len(calls) == 2
