import json
import os
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch

import numpy as np
import studio_renderer as studio
import cloud_once as cloud


class StudioTests(unittest.TestCase):
    def prepared(self,ch):
        plan=studio.make_plan(ch)
        cursor=0
        for s in plan:
            s.update(audio=np.ones(studio.RATE*2,dtype=np.float32)*.1,start=cursor,
                     voice_start=cursor+.18,duration=3.0,end=cursor+3)
            cursor+=3
        return plan,cursor

    def test_all_catalog_scenes_render_without_overflow(self):
        for ch in cloud.content_catalog():
            plan,duration=self.prepared(ch)
            for s in plan:
                with self.subTest(topic=ch['content_id'],scene=s['headline']):
                    frame=studio.render_frame(plan,s['start']+1,ch['genre'],duration)
                    self.assertEqual(frame.size,(1080,1920))

    def test_current_trend_format_renders(self):
        trend={'title':'Major Topic','region':'US','traffic':'200K+',
               'news':[{'title':'A sourced angle','url':'https://example.com/story','source':'Example News'}]}
        ch=cloud.trend_candidates([trend])[0]
        plan,duration=self.prepared(ch)
        for s in plan:
            frame=studio.render_frame(plan,s['start']+1,'current',duration)
            self.assertEqual(frame.size,(1080,1920))

    def test_memory_numbers_hidden_during_countdown(self):
        ch=dict(genre='challenge',kind='memory',content_id='memory-test',hook='MEMORIZE THIS',question='1  7  3  9  2',prompt='What was number #2?',answer='7')
        p=studio.make_plan(ch)
        self.assertIn('1  7',p[0]['label'])
        self.assertEqual(p[1]['label'],'?')
        self.assertEqual(p[2]['label'],'7')
        self.assertGreaterEqual(p[1]['min_duration'],5)

    def test_all_challenge_formats_render(self):
        for _ in range(35):
            ch=cloud._challenge();ch['genre']='challenge'
            plan,duration=self.prepared(ch)
            for s in plan:
                studio.render_frame(plan,s['start']+1,'challenge',duration)

    def test_sound_mix_not_clipped_and_stereo(self):
        plan,duration=self.prepared(cloud.content_catalog()[3])
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'mix.wav';report=studio.score_audio(plan,duration,'space',p)
            self.assertLess(report['peak_dbfs'],0)
            with wave.open(str(p)) as f:
                self.assertEqual(f.getnchannels(),2)
                self.assertEqual(f.getframerate(),24000)
                self.assertEqual(f.getnframes(),int(duration*24000))
                samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2')
                self.assertLess(np.abs(samples.astype(np.int32)).max(),32767)

    def test_narration_failure_does_not_publish_silent_fallback(self):
        plan=studio.make_plan(cloud.content_catalog()[0])
        with patch.object(studio,'voice_engine') as engine:
            engine.return_value.create.return_value=(np.array([],dtype=np.float32),24000)
            with self.assertRaises(RuntimeError): studio.voice_plan(plan,'tech')

    def test_telemetry_disabled_before_runtime_initialization(self):
        self.assertEqual(os.environ.get('ORT_DISABLE_TELEMETRY'),'1')


    def test_procedural_assets_never_get_unrelated_external_overlays(self):
        items=[
            {'strategy':'original-procedural','status':'ready','license':'original-generated-by-astra'},
            {'strategy':'original-illustration','status':'ready','license':'original-generated-by-astra'},
            {'strategy':'source-derived','status':'ready','license':'original-abstraction-no-source-media-copied'},
        ]
        with patch.object(studio,'provider_adapter') as provider:
            out=studio.acquire_story_media(items)
        provider.assert_not_called()
        self.assertEqual(out,items)

    def test_premium_story_uses_explicit_verified_media_requests(self):
        premium=next(x for x in cloud.content_catalog() if x.get('premium_story'))
        plan=studio.make_plan(premium)
        self.assertEqual(len(plan),len(premium['story_beats']))
        self.assertFalse(any(x.get('story_beat')=='cta' for x in plan))
        manifest=studio.asset_manifest(premium,plan)
        self.assertTrue(all(x.get('strategy')=='external-verified' for x in manifest))
        self.assertTrue(all(x.get('query') for x in manifest))


if __name__=='__main__':
    unittest.main()
