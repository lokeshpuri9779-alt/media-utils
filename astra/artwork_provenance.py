"""Audit storyboard-to-render visual provenance without granting asset approval."""
import json
from pathlib import Path
from astra.artwork_story_bridge import build_story


def audit(storyboard, render_report):
    story = build_story(storyboard)
    report = render_report if isinstance(render_report, dict) else {}
    scenes = report.get("scenes") or []
    original = json.loads(Path(storyboard).read_text(encoding="utf-8"))["scenes"]
    rows = []
    for i, requested in enumerate(original):
        rendered = scenes[i] if i < len(scenes) and isinstance(scenes[i], dict) else {}
        asset = rendered.get("resolved_asset") or {}
        requested_id = requested["background"]
        actual = str(asset.get("id") or asset.get("asset_id") or "")
        verified = actual == requested_id and str(asset.get("status")) == "approved"
        rows.append({"scene": i + 1, "requested_background": requested_id,
                     "actual_asset_id": actual or None,
                     "asset_provider": asset.get("provider"),
                     "asset_status": asset.get("status"),
                     "requested_background_verified": verified})
    return {"content_id": story["content_id"], "review_only": True,
            "requested_backgrounds_verified": bool(rows) and all(x["requested_background_verified"] for x in rows),
            "scenes": rows}


def save_audit(storyboard, render_report, output):
    result = audit(storyboard, render_report)
    Path(output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
