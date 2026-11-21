import hashlib
import json

from PIL import Image

from studio_renderer import composite_cached_asset, media_cache_key


def _fixture(tmp_path, *, query="Original scene illustration: underwater | sea door"):
    image_path = tmp_path / "scene.png"
    meta_path = tmp_path / "scene.json"
    Image.new("RGB", (24, 24), (220, 30, 40)).save(image_path)
    item = {
        "query": query,
        "kind": "editorial-illustration",
        "cache_image": str(image_path),
        "cache_meta": str(meta_path),
        "media_fit": "contain",
    }
    metadata = {
        "cache_key": media_cache_key(item),
        "query": query,
        "kind": item["kind"],
        "cache_image": str(image_path),
        "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
    }
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")
    return item, metadata, image_path, meta_path


def test_cached_illustration_requires_scene_bound_sidecar(tmp_path):
    item, _, _, meta_path = _fixture(tmp_path)
    meta_path.unlink()
    frame = Image.new("RGB", (1080, 1920), (1, 2, 3))
    result = composite_cached_asset(frame, item)
    assert result.getpixel((540, 800)) == (1, 2, 3)


def test_cached_illustration_rejects_sidecar_for_different_scene_brief(tmp_path):
    item, metadata, _, meta_path = _fixture(tmp_path)
    metadata["query"] = "Original scene illustration: observatory"
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")
    frame = Image.new("RGB", (1080, 1920), (1, 2, 3))
    result = composite_cached_asset(frame, item)
    assert result.getpixel((540, 800)) == (1, 2, 3)


def test_cached_illustration_rejects_changed_image_bytes(tmp_path):
    item, _, image_path, _ = _fixture(tmp_path)
    Image.new("RGB", (24, 24), (30, 40, 220)).save(image_path)
    frame = Image.new("RGB", (1080, 1920), (1, 2, 3))
    result = composite_cached_asset(frame, item)
    assert result.getpixel((540, 800)) == (1, 2, 3)


def test_cached_illustration_accepts_matching_scene_and_image_hash(tmp_path):
    item, _, _, _ = _fixture(tmp_path)
    frame = Image.new("RGB", (1080, 1920), (1, 2, 3))
    result = composite_cached_asset(frame, item)
    assert result.getpixel((540, 800)) != (1, 2, 3)
