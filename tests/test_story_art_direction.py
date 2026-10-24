import ast
import hashlib
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from astra.asset_library import select_asset, draw_asset_for_scene
from astra_v2.omniroute_image_assets import preproduce, export_reviewed_render_manifest
from astra_v2.story_art_direction import illustration_requests, bind_reviewed_scenes


def story():
    return {"content_id": "otter-bell", "title": "The Bell",
            "visual_bible": {"characters": {"otter": "brown fur, blue scarf"},
                             "locations": {"bridge": "old wooden footbridge"},
                             "objects": {"bell": "small brass bell"}},
            "story_beats": [{"speech": "Otter finds the bell beside the bridge."},
                            {"speech": "Otter ties the bell to the bridge railing."}]}


def queue(value):
    return {"rewrites": [{"status": "awaiting_independent_editorial_approval", "story": value}]}


def png():
    data = io.BytesIO()
    im = Image.new("RGB", (540, 960))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(im)
    for y in range(960):
        draw.line((0, y, 539, y), fill=(22 + y // 32, 66 + y // 16, 99 + y // 12))
    im.save(data, format="PNG")
    return data.getvalue()


class StoryArtTests(unittest.TestCase):
    def setUp(self):
        # Only fixture tests receive a deterministic review signing key.
        # Production still requires its separately protected secret.
        signer = patch.dict(os.environ, {
            "ASTRA_ART_REVIEW_HMAC_KEY": "story-art-fixture-only-review-key-0123456789"
        })
        signer.start()
        self.addCleanup(signer.stop)

    def test_all_scenes_share_bible_but_select_distinct_actions(self):
        requests = illustration_requests(story())
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["story_visual_sha256"], requests[1]["story_visual_sha256"])
        self.assertNotEqual(requests[0]["prompt"], requests[1]["prompt"])
        for row in requests:
            self.assertIn("blue scarf", row["prompt"])
            self.assertIn("small brass bell", row["prompt"])
            self.assertEqual(row["continuity_status"], "not_verified")

    def test_budget_resumes_second_scene_and_invalidates_changed_story(self):
        calls = []
        def generate(prompt):
            calls.append(prompt)
            return png()
        with tempfile.TemporaryDirectory() as root:
            first = preproduce(queue(story()), root, generator=generate, limit=1)
            self.assertEqual([x['status'] for x in first['assets']], ['review_only', 'pending_budget'])
            second = preproduce(queue(story()), root, generator=generate, limit=1)
            self.assertEqual([x['status'] for x in second['assets']], ['cached_review_only', 'review_only'])
            third = preproduce(queue(story()), root, generator=generate, limit=1)
            self.assertEqual(third['provider_calls'], 0)
            changed = story()
            changed['visual_bible']['characters']['otter'] = 'white fur, red scarf'
            fourth = preproduce(queue(changed), root, generator=generate, limit=1)
            self.assertEqual(fourth['assets'][0]['status'], 'review_only')
            self.assertEqual(len(calls), 3)
            self.assertFalse(fourth['production_ready'])

    def test_corruption_is_reported_without_silent_reuse(self):
        with tempfile.TemporaryDirectory() as root:
            first = preproduce(queue(story()), root, generator=lambda p: png())
            (Path(root) / first['assets'][0]['path']).write_bytes(b'broken')
            result = preproduce(queue(story()), root, generator=lambda p: self.fail('must not regenerate silently'))
            self.assertEqual(result['assets'][0]['status'], 'generation_failed')

    def test_reviewed_story_preview_cli_requires_complete_inputs(self):
        # Inspect the argparse branch without importing optional Studio runtime
        # dependencies (the lightweight Fast CI lane does not install httpx).
        tree = ast.parse(Path("studio_renderer.py").read_text())
        main = next(node for node in tree.body
                    if isinstance(node, ast.If)
                    and isinstance(node.test, ast.Compare)
                    and isinstance(node.test.left, ast.Name)
                    and node.test.left.id == "__name__")
        source = ast.unparse(main)
        self.assertIn("--story-json", source)
        self.assertIn("--reviewed-art-manifest", source)
        self.assertIn("parser.error", source)
        self.assertIn("render_short", source)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools required")
    def test_studio_preview_produces_valid_vertical_mp4(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "studio-preview.mp4"
            env = {**os.environ, "ASTRA_VISUAL_ARTIFACT_BACKDROPS": "0"}
            subprocess.run([sys.executable, "studio_renderer.py", "--preview", str(output)],
                           check=True, timeout=180, env=env, capture_output=True, text=True)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1024)
            probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                    "-show_entries", "stream=width,height",
                                    "-of", "json", str(output)],
                                   check=True, capture_output=True, text=True, timeout=30)
            stream = json.loads(probe.stdout)["streams"][0]
            self.assertEqual((stream["width"], stream["height"]), (1080, 1920))

    def test_reviewed_image_exports_and_renders_exact_scene(self):
        with tempfile.TemporaryDirectory() as root:
            produced = preproduce(queue(story()), root, generator=lambda _: png(), limit=2)
            decisions = {item["request_sha256"]: {
                "approved": True, "sha256": item["sha256"],
                "semantic_match": True, "character_continuity": True}
                for item in produced["assets"]}
            manifest = Path(root) / "art" / "manifest.json"
            result = export_reviewed_render_manifest(produced, root, decisions, manifest)
            self.assertEqual(result["assets"], 2)
            asset = json.loads(manifest.read_text())["assets"][0]
            shot = {"artwork_asset_id": asset["id"], "story_content_id": "otter-bell",
                    "scene_id": "001", "artwork_manifest_path": str(manifest)}
            self.assertIsNotNone(select_asset(shot, manifest))
            frame = Image.new("RGB", (540, 960))
            self.assertTrue(draw_asset_for_scene(frame, shot, manifest_path=manifest))
            self.assertEqual(frame.getpixel((200, 200)), (28, 78, 115))
            self.assertIsNone(select_asset({**shot, "scene_id": "002"}, manifest))
            with self.assertRaises(ValueError):
                export_reviewed_render_manifest(produced, root,
                    {k: {**v, "sha256": "bad"} for k, v in decisions.items()}, manifest)

    def test_render_frame_prioritizes_approved_art_over_other_layers(self):
        tree = ast.parse(Path("studio_renderer.py").read_text())
        render = next(node for node in tree.body
                      if isinstance(node, ast.FunctionDef) and node.name == "render_frame")
        branches = [node for node in ast.walk(render) if isinstance(node, ast.If)]
        reviewed = [node for node in branches
                    if isinstance(node.test, ast.Call)
                    and isinstance(node.test.func, ast.Attribute)
                    and node.test.func.attr == "get"
                    and node.test.args and isinstance(node.test.args[0], ast.Constant)
                    and node.test.args[0].value == "artwork_asset_id"]
        self.assertTrue(reviewed, "Approved artwork must have a direct render branch")
        self.assertTrue(any(isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Name)
                            and node.func.id == "draw_visual"
                            for node in ast.walk(reviewed[0].body[0])),
                        "Approved artwork must be composited through Studio")

    def test_complete_reviewed_scene_binding_is_exact_and_atomic(self):
        with tempfile.TemporaryDirectory() as root:
            produced = preproduce(queue(story()), root, generator=lambda _: png(), limit=2)
            decisions = {row["request_sha256"]: {
                "approved": True, "sha256": row["sha256"],
                "semantic_match": True, "character_continuity": True}
                for row in produced["assets"]}
            manifest = Path(root) / "art" / "manifest.json"
            export_reviewed_render_manifest(produced, root, decisions, manifest)
            shots = [{"speech": "first"}, {"speech": "second"}]
            bound = bind_reviewed_scenes(shots, "otter-bell", manifest)
            self.assertEqual([s["scene_id"] for s in bound], ["001", "002"])
            self.assertEqual(shots, [{"speech": "first"}, {"speech": "second"}])
            for shot in bound:
                self.assertIsNotNone(select_asset(shot, manifest))
            with self.assertRaises(ValueError):
                bind_reviewed_scenes(shots, "other-story", manifest)
            with self.assertRaises(ValueError):
                bind_reviewed_scenes(shots + [{"speech": "third"}], "otter-bell", manifest)

    def test_reviewed_art_rejects_modified_bytes_at_render_time(self):
        with tempfile.TemporaryDirectory() as root:
            produced = preproduce(queue(story()), root, generator=lambda _: png(), limit=2)
            decisions = {row["request_sha256"]: {
                "approved": True, "sha256": row["sha256"],
                "semantic_match": True, "character_continuity": True}
                for row in produced["assets"]}
            manifest = Path(root) / "art" / "manifest.json"
            export_reviewed_render_manifest(produced, root, decisions, manifest)
            asset = json.loads(manifest.read_text())["assets"][0]
            scene = {"artwork_asset_id": asset["id"], "story_content_id": "otter-bell",
                     "scene_id": "001"}
            self.assertIsNotNone(select_asset(scene, manifest))
            location = Path(root) / asset["path"]
            location.write_bytes(location.read_bytes() + b"tampered")
            self.assertIsNone(select_asset(scene, manifest))
            self.assertFalse(draw_asset_for_scene(Image.new("RGB", (540, 960)),
                                                 scene, manifest_path=manifest))

    def test_explicit_binding_never_selects_another_story_or_scene(self):
        with tempfile.TemporaryDirectory() as root:
            art = Path(root) / 'art'
            art.mkdir()
            (art / 'scene.png').write_bytes(png())
            manifest = art / 'manifest.json'
            manifest.write_text(json.dumps({'assets': [{
                'id': 'scene-001', 'path': 'art/scene.png', 'category': 'background',
                'tags': ['bell'], 'status': 'approved',
                'story_content_id': 'otter-bell', 'scene_id': '001'}]}))
            shot = {'artwork_asset_id': 'scene-001', 'story_content_id': 'otter-bell', 'scene_id': '001'}
            self.assertIsNotNone(select_asset(shot, manifest))
            self.assertIsNone(select_asset({**shot, 'scene_id': '002'}, manifest))
            self.assertIsNone(select_asset({**shot, 'story_content_id': 'other'}, manifest))
            self.assertIsNone(select_asset({'visual': 'bell'}, manifest))
            # Exercise the real Studio artwork dispatch without importing voice models.
            tree = ast.parse(Path('studio_renderer.py').read_text())
            func = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'draw_visual')
            from PIL import ImageDraw
            scope = dict(ImageDraw=ImageDraw, ease=lambda x: x,
                         draw_asset_for_scene=draw_asset_for_scene, CreativeReject=RuntimeError)
            exec(compile(ast.Module(body=[func], type_ignores=[]), 'studio_renderer.py', 'exec'), scope)
            frame = Image.new('RGB', (540, 960))
            scope['draw_visual'](frame, {**shot, 'visual': 'bell', 'artwork_manifest_path': str(manifest)}, 0, 0, (0, 0, 0))
            self.assertEqual(frame.getpixel((200, 200)), (28, 78, 115))
            with self.assertRaises(RuntimeError):
                scope['draw_visual'](frame, {**shot, 'scene_id': '002', 'visual': 'bell', 'artwork_manifest_path': str(manifest)}, 0, 0, (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
