import ast
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from astra.asset_library import select_asset, draw_asset_for_scene
from astra_v2.omniroute_image_assets import preproduce
from astra_v2.story_art_direction import illustration_requests


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
            self.assertEqual(frame.getpixel((200, 200)), (22, 66, 99))
            with self.assertRaises(RuntimeError):
                scope['draw_visual'](frame, {**shot, 'scene_id': '002', 'visual': 'bell', 'artwork_manifest_path': str(manifest)}, 0, 0, (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
