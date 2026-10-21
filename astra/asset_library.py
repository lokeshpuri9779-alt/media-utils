"""Local generated-art asset selection for ASTRA Shorts.

Only manifest-approved, locally present assets are eligible. Missing or invalid
assets are ignored so the existing renderer remains the safe fallback.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "art" / "manifest.json"
_WORD = re.compile(r"[a-z0-9]+")


def _tokens(value: Any) -> set[str]:
    return set(_WORD.findall(str(value or "").lower()))


def generate_semantic_assets(stories, output_root=None, limit=24):
    """Generate offline story-directed backgrounds with verified manifest."""
    import hashlib
    from PIL import ImageDraw
    root = Path(output_root or ROOT).resolve()
    folder = root / "art" / "assets" / "generated"
    folder.mkdir(parents=True, exist_ok=True)
    entries = []
    for story in list(stories)[:max(0, min(int(limit), 128))]:
        if not isinstance(story, dict):
            continue
        description = " ".join(str(story.get(k) or "") for k in (
            "story_subject", "visual", "visual_intent", "visual_prompt", "headline", "speech"))
        tags = sorted(_tokens(description))
        if not tags:
            continue
        seed = hashlib.sha256(description.encode("utf-8")).digest()
        identity = hashlib.sha256(description.encode("utf-8")).hexdigest()[:20]
        im = Image.new("RGBA", (540, 960), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im, "RGBA")
        sky = tuple(45 + seed[i] % 100 for i in range(3))
        draw.rectangle((0, 0, 540, 960), fill=(*sky, 255))
        for i in range(12):
            x = (seed[i] * 37 + i * 71) % 540
            y = (seed[(i + 8) % 32] * 11 + i * 97) % 790
            radius = 15 + seed[(i + 16) % 32] % 75
            draw.ellipse((x-radius, y-radius, x+radius, y+radius),
                         fill=(min(255, sky[0] + 25), min(255, sky[1] + 32),
                               min(255, sky[2] + 40), 70))
        draw.polygon([(0, 760), (180, 670), (380, 760), (540, 680),
                      (540, 960), (0, 960)], fill=(30, 65, 75, 255))
        destination = folder / (identity + ".png")
        im.save(destination, format="PNG", optimize=True)
        with Image.open(destination) as verified:
            verified.verify()
        entries.append({"id": "semantic-" + identity,
                        "path": destination.relative_to(root).as_posix(),
                        "category": "background", "tags": tags,
                        "status": "approved", "source": "offline-semantic-generator"})
    manifest = root / "art" / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"assets": entries}, indent=2), encoding="utf-8")
    return {"generated": len(entries), "manifest": str(manifest)}


def load_assets(manifest_path: str | Path = DEFAULT_MANIFEST) -> list[dict]:
    """Load valid, approved local assets from a JSON manifest."""
    path = Path(manifest_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    if not isinstance(data, dict) or not isinstance(data.get("assets"), list):
        return []
    root = path.parent.parent.resolve()
    assets = []
    for row in data["assets"]:
        if not isinstance(row, dict) or row.get("status") != "approved":
            continue
        rel = row.get("path")
        if not isinstance(rel, str) or not rel.strip():
            continue
        candidate = (root / rel).resolve()
        if root not in candidate.parents or not candidate.is_file():
            continue
        category = str(row.get("category") or "").lower()
        if category not in {"character", "prop", "background", "overlay"}:
            continue
        tags = row.get("tags", [])
        if not isinstance(tags, list):
            continue
        assets.append({**row, "_resolved_path": candidate, "_tags": _tokens(" ".join(map(str, tags)) + " " + str(row.get("id", "")))})
    return assets


def select_asset(scene: dict, manifest_path: str | Path = DEFAULT_MANIFEST) -> dict | None:
    """Choose a relevant approved asset; no match means normal rendering continues."""
    query = _tokens(" ".join(str(scene.get(k) or "") for k in (
        "story_subject", "visual", "visual_intent", "visual_prompt",
        "headline", "label", "speech", "action",
    )))
    if not query:
        return None
    ranked = []
    for asset in load_assets(manifest_path):
        overlap = query & asset["_tags"]
        if not overlap:
            continue
        score = len(overlap) * 10
        if asset.get("category") == "character" and scene.get("story_subject"):
            score += 8 if _tokens(scene["story_subject"]) & asset["_tags"] else 0
        ranked.append((score, str(asset.get("id") or ""), asset))
    return sorted(ranked, key=lambda item: (-item[0], item[1]))[0][2] if ranked else None


def draw_asset_for_scene(image: Image.Image, scene: dict, t: float = 0.0,
                         manifest_path: str | Path = DEFAULT_MANIFEST) -> bool:
    """Composite one validated atlas-derived asset onto a rendered frame.

    Backgrounds fill the frame. Character/prop/overlay files must contain real
    alpha transparency; this rejects checkerboard-filled atlas crops.
    """
    asset = select_asset(scene, manifest_path)
    if asset is None:
        return False
    try:
        with Image.open(asset["_resolved_path"]) as opened:
            source = opened.convert("RGBA")
    except (OSError, ValueError):
        return False

    category = str(asset.get("category") or "").lower()
    width, height = image.size
    if category == "background":
        if source.width < 540 or source.height < 960:
            return False
        fitted = ImageOps.fit(source, (width, height), method=Image.Resampling.LANCZOS)
        image.paste(fitted.convert(image.mode), (0, 0))
        return True

    alpha = source.getchannel("A")
    if alpha.getextrema() == (255, 255):
        return False
    if source.width < 256 or source.height < 256:
        return False
    if category == "character":
        max_w, max_h = int(width * 0.76), int(height * 0.55)
        center_x, center_y = width // 2, int(height * 0.48)
    elif category == "prop":
        max_w, max_h = int(width * 0.48), int(height * 0.30)
        center_x, center_y = width // 2, int(height * 0.53)
    else:
        max_w, max_h = int(width * 0.86), int(height * 0.70)
        center_x, center_y = width // 2, int(height * 0.46)
    source.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    # A restrained bob keeps the asset alive without independent flying parts.
    import math
    bob = int(4 * math.sin(float(t) * 1.8)) if category == "character" else 0
    x, y = center_x - source.width // 2, center_y - source.height // 2 + bob
    if image.mode == "RGBA":
        image.alpha_composite(source, (x, y))
    else:
        image.paste(source, (x, y), source)
    return True
