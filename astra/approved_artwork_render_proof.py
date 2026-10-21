"""Review-only end-to-end test with generated artwork explicitly approved as test fixtures.

Never alters the production manifest or uploads to YouTube.
"""
import json
from pathlib import Path
from astra.background_factory import generate
from astra.artwork_story_bridge import render_review, build_story
from astra.asset_library import load_assets


def prepare_fixture(root, storyboard):
    root = Path(root).resolve()
    manifest = generate(root)
    payload = json.loads(manifest.read_text())
    requested = {x["background"] for x in json.loads(Path(storyboard).read_text())["scenes"]}
    for asset in payload["assets"]:
        if asset["id"] in requested:
            asset["status"] = "approved"
            asset["review_scope"] = "isolated_ci_fixture_only"
    manifest.write_text(json.dumps(payload, indent=2) + "\n")
    story = build_story(storyboard, artwork_manifest=manifest)
    if len([x for x in load_assets(manifest) if x["id"] in requested]) != len(requested):
        raise ValueError("approved_fixture_incomplete")
    return manifest, story


def render_fixture(root, storyboard, output):
    manifest, story = prepare_fixture(root, storyboard)
    result = render_review(storyboard, output, artwork_manifest=manifest)
    report = {"content_id": story["content_id"], "review_only": True,
              "test_fixture_approval_only": True, "manifest": str(manifest),
              "requested_backgrounds": [x["background"] for x in json.loads(Path(storyboard).read_text())["scenes"]],
              "studio_render_result": str(result)}
    Path(output).with_suffix(".artwork.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
