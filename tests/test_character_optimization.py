import os
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import agnes_free_video as agnes


class FakeAgnes:
    def __init__(self, polls=None):
        self.posts = 0
        self.gets = 0
        self.polls = list(polls or [])
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def response(self, code, **kwargs):
        return httpx.Response(code, request=httpx.Request('GET', 'https://example.test'), **kwargs)
    def post(self, *args, **kwargs):
        self.posts += 1
        return self.response(200, json={'video_id': f'job-{self.posts}'})
    def get(self, url, **kwargs):
        self.gets += 1
        if url == agnes.POLL_URL:
            if self.polls:
                return self.polls.pop(0)
            return self.response(200, json={'status': 'completed', 'video_url': 'https://example.test/clip.mp4'})
        return self.response(200, content=b'fake-video-bytes')


class CharacterOptimizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'AGNES_API_KEY': 'test-key',
            'ASTRA_CHARACTER_CACHE': str(self.root/'cache')})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.temp.cleanup)
        self.shot = {'prompt': 'one bear', 'target_seconds': 4.2}

    def test_identical_scene_uses_cache_without_any_provider_request(self):
        client = FakeAgnes()
        with patch.object(agnes.httpx, 'Client', return_value=client):
            agnes.generate_agnes_clip(self.shot, self.root/'first.mp4')
        with patch.object(agnes.httpx, 'Client', side_effect=AssertionError('cache hit must not use API')):
            report = agnes.generate_agnes_clip(self.shot, self.root/'second.mp4')
        self.assertTrue(report['cache_hit'])
        self.assertEqual((self.root/'first.mp4').read_bytes(), (self.root/'second.mp4').read_bytes())
        self.assertEqual(client.posts, 1)
        self.assertEqual(report['output_path'], str(self.root/'second.mp4'))

    def test_changed_prompt_or_reference_bytes_requires_new_scene(self):
        reference = self.root/'ref.png'
        reference.write_bytes(b'original-frame')
        shot = {**self.shot, 'reference_image_paths': [str(reference)]}
        client = FakeAgnes()
        with patch.object(agnes.httpx, 'Client', return_value=client):
            agnes.generate_agnes_clip(shot, self.root/'one.mp4')
            reference.write_bytes(b'changed-frame')
            agnes.generate_agnes_clip(shot, self.root/'two.mp4')
            agnes.generate_agnes_clip({**shot, 'prompt': 'corrected bear'}, self.root/'three.mp4')
        self.assertEqual(client.posts, 3)

    def test_rate_limited_poll_resumes_submitted_job_without_resubmitting(self):
        client = FakeAgnes()
        client.polls = [client.response(429, headers={'Retry-After': '300'})]
        with patch.object(agnes.httpx, 'Client', return_value=client):
            with self.assertRaisesRegex(agnes.AgnesFreeVideoUnavailable, 'checkpoint saved'):
                agnes.generate_agnes_clip(self.shot, self.root/'one.mp4', timeout_seconds=20)
            report = agnes.generate_agnes_clip(self.shot, self.root/'two.mp4')
        self.assertEqual(client.posts, 1)
        self.assertTrue(report['resumed_job'])

    def test_corrupt_cached_video_redownloads_existing_job(self):
        client = FakeAgnes()
        with patch.object(agnes.httpx, 'Client', return_value=client):
            agnes.generate_agnes_clip(self.shot, self.root/'one.mp4')
            next((self.root/'cache').glob('*/clip.mp4')).write_bytes(b'corrupt')
            report = agnes.generate_agnes_clip(self.shot, self.root/'two.mp4')
        self.assertEqual(client.posts, 1)
        self.assertTrue(report['resumed_job'])
        self.assertFalse(report['cache_hit'])
        self.assertEqual((self.root/'two.mp4').read_bytes(), b'fake-video-bytes')

    def test_server_cooldown_is_not_shortened_to_three_minutes(self):
        client = FakeAgnes()
        client.polls = [client.response(429, headers={'Retry-After': '300'})]
        with patch.object(agnes.httpx, 'Client', return_value=client), patch.object(agnes.time, 'sleep') as sleep:
            agnes.generate_agnes_clip(self.shot, self.root/'one.mp4', timeout_seconds=600)
        sleep.assert_called_once_with(300)

    def test_failed_provider_job_can_be_replaced(self):
        client = FakeAgnes()
        client.polls = [client.response(200, json={'status': 'failed', 'error': 'render failed'})]
        with patch.object(agnes.httpx, 'Client', return_value=client):
            with self.assertRaises(agnes.AgnesFreeVideoUnavailable):
                agnes.generate_agnes_clip(self.shot, self.root/'one.mp4')
            agnes.generate_agnes_clip(self.shot, self.root/'two.mp4')
        self.assertEqual(client.posts, 2)

    def test_cache_does_not_store_credentials(self):
        client = FakeAgnes()
        with patch.object(agnes.httpx, 'Client', return_value=client):
            agnes.generate_agnes_clip(self.shot, self.root/'one.mp4')
        state = next((self.root/'cache').glob('*/state.json')).read_text()
        self.assertNotIn('test-key', state)
        self.assertNotIn('Authorization', state)
        self.assertNotIn('https://example.test', state)

    def test_existing_upload_is_detected_before_rendering(self):
        cloud = SimpleNamespace(access_token=Mock(return_value='token'), verify_channel=Mock(),
                                live_channel_duplicate=Mock(return_value=True))
        pilot = SimpleNamespace(render=Mock())
        script = Path(__file__).resolve().parents[1]/'scripts/render_publish_character_story.py'
        with patch.dict('sys.modules', {'cloud_once': cloud, 'character_pilot': pilot}):
            with self.assertRaisesRegex(SystemExit, 'already exists'):
                runpy.run_path(str(script), run_name='__main__')
        pilot.render.assert_not_called()


if __name__ == '__main__':
    unittest.main()
