import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import cloud_once as cloud


class PublishSelectionTests(unittest.TestCase):
    def test_live_titles_exclude_curated_candidate_before_render(self):
        ready = next(c for c in cloud.content_catalog()
                     if c.get('premium_story') and c.get('production_ready'))
        wanted = dict(ready, content_id='curated-backup',
                      title='A Different Curated Story',
                      hook='A DIFFERENT STORY')
        with patch.object(cloud, 'content_catalog', return_value=[ready, wanted]):
            selected = cloud.choose_content(
                {'videos': {}}, [],
                excluded_titles={cloud.normalize_content_text(ready['title'])},
            )
        self.assertEqual(selected['content_id'], wanted['content_id'])

    def test_old_persisted_identity_never_reenters_catalog(self):
        catalog = cloud.content_catalog()
        now = datetime.now(cloud.IST)
        data = {'videos': {'old': {'content_id': catalog[0]['content_id'],
            'published_at': (now - timedelta(days=100)).isoformat()}}}
        with patch.object(cloud, 'content_catalog', return_value=[catalog[0]]):
            with self.assertRaisesRegex(RuntimeError, 'No fresh content available'):
                cloud.choose_content(data, [], now)

    def test_live_identity_parser_handles_s_and_newlines(self):
        channel = MagicMock(status_code=200)
        channel.json.return_value = {'items': [{'contentDetails': {
            'relatedPlaylists': {'uploads': 'owned'}}}]}
        playlist = MagicMock(status_code=200)
        playlist.json.return_value = {'items': [{'snippet': {
            'title': 'A story!', 'description': 'ASTRA-ID:last-signal\nSource: example'}}]}
        with patch.object(cloud.httpx, 'Client') as client:
            client.return_value.__enter__.return_value.get.side_effect = [channel, playlist]
            titles, ids = cloud.live_channel_history('test-token')
        self.assertEqual(ids, {'last-signal'})
        self.assertEqual(titles, {'a story'})

    def _controller(self, histories, persisted_collision=False):
        stack = ExitStack()
        self.addCleanup(stack.close)
        temp = stack.enter_context(tempfile.TemporaryDirectory())
        stack.enter_context(patch.object(cloud, 'STATE_PATH', Path(temp) / 'state.json'))
        stack.enter_context(patch.object(cloud.tempfile, 'mkdtemp', return_value=temp))
        stack.enter_context(patch.object(cloud.sys, 'argv', ['cloud_once.py']))
        stack.enter_context(patch.dict(cloud.os.environ, {'ASTRA_FORCE_RUN': '0',
            'ASTRA_PROBE_ID': '', 'ASTRA_LONG_ENABLED': '0'}))
        for name in ('need', 'verify_channel', 'refresh_performance', 'refresh_research'):
            stack.enter_context(patch.object(cloud, name))
        stack.enter_context(patch.object(cloud, 'access_token', return_value='test-token'))
        stack.enter_context(patch.object(cloud, 'scheduled_attempt_due', return_value=True))
        stack.enter_context(patch.object(cloud, 'load_performance', return_value={
            'videos': {'old': {'content_id': 'persisted-id'}}}))
        stack.enter_context(patch.object(cloud, 'live_channel_history', return_value=(
            {'legacy title shorts'}, {'live-id'})))
        stack.enter_context(patch.object(cloud, 'live_channel_duplicate', side_effect=histories))
        count = [0]
        def render(path, **kwargs):
            count[0] += 1
            cloud.CONTENT_META = {'content_id': 'fresh-' + str(count[0]), 'genre': 'fiction'}
            return 'Fresh title ' + str(count[0]), 'Original story'
        render_mock = stack.enter_context(patch.object(cloud, 'make_short', side_effect=render))
        stack.enter_context(patch.object(cloud, 'content_already_published',
            side_effect=lambda cid: persisted_collision and cid != 'fresh-1'))
        stack.enter_context(patch('ypp_safety.enforce', return_value={'decision': 'allow'}))
        stack.enter_context(patch('ops_guardian.healthy'))
        record = stack.enter_context(patch.object(cloud, 'record_video'))
        upload = stack.enter_context(patch.object(cloud, 'upload', return_value=(
            'success', 'https://www.youtube.com/watch?v=new-video')))
        return render_mock, upload, record

    def test_duplicate_retry_keeps_all_exclusions_then_uploads_once(self):
        render, upload, record = self._controller([True, False, False])
        cloud.main()
        self.assertEqual(render.call_count, 2)
        exclusions = render.call_args.kwargs
        self.assertTrue({'persisted-id', 'live-id', 'fresh-1'} <= exclusions['excluded_ids'])
        self.assertIn('legacy title shorts', exclusions['excluded_titles'])
        upload.assert_called_once()
        record.assert_called_once_with('new-video', 'Fresh title 2 #Shorts')
        state = cloud.json.loads(cloud.STATE_PATH.read_text())
        self.assertEqual((state['attempts'], state['successes']), (1, 1))

    def test_final_persisted_collision_cannot_fall_through_to_upload(self):
        _, upload, _ = self._controller([True, True, True, False], persisted_collision=True)
        with self.assertRaisesRegex(RuntimeError, 'Fresh content selection exhausted'):
            cloud.main()
        upload.assert_not_called()


if __name__ == '__main__':
    unittest.main()
