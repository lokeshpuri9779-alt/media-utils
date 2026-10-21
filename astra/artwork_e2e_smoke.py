"""End-to-end isolated smoke test for generated artwork and renderer integration.

Uses local immutable storage only; does not approve production art or publish.
"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path

from PIL import Image, ImageChops
from astra.background_factory import generate
from astra.artwork_archive import archive
from astra.artwork_restore import restore
from astra.asset_library import draw_asset_for_scene, select_asset
from astra_v2.adaptive_artifact_store import ArtifactStore


def smoke():
    with tempfile.TemporaryDirectory(prefix="astra-art-e2e-") as folder:
        root = Path(folder)
        original = generate(root / "generated")
        store = ArtifactStore(root / "immutable")
        receipts = archive(original, store)
        assert receipts["archived"] == 12 and receipts["approved"] == 0
        receipt_path = root / "receipt.json"
        receipt_path.write_text(json.dumps(receipts), encoding="utf-8")
        restored = restore(receipt_path, root / "restored", store)
        assert len(json.loads(restored.read_text())["assets"]) == 12
        # Simulate explicit approval solely in the temporary test fixture.
        fixture = json.loads(restored.read_text())
        fixture["assets"][0]["status"] = "approved"
        fixture_path = root / "restored" / "art" / "approved-fixture.json"
        fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
        name = fixture["assets"][0]["id"]
        frame = Image.new("RGB", (540, 960), (0, 0, 0))
        before = frame.copy()
        assert select_asset({"visual_prompt": name.replace("-", " ")}, fixture_path)
        assert draw_asset_for_scene(frame, {"visual_prompt": name.replace("-", " ")},
                                    manifest_path=fixture_path)
        assert ImageChops.difference(frame, before).getbbox() is not None
        assert not select_asset({"visual_prompt": name.replace("-", " ")}, restored)
        return {"generated": 12, "archived": 12, "restored": 12,
                "rendered_frame": True, "production_approved": 0}


if __name__ == "__main__":
    print(json.dumps(smoke(), sort_keys=True))
