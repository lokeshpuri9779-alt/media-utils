import copy
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch,MagicMock
import unittest
import numpy as np
import audience_research as research
import longform
import studio_renderer as studio
import cloud_once as cloud


class GrowthTests(unittest.TestCase):
    def setUp(self):self.now=datetime(2026,10,5,19,30,tzinfo=ZoneInfo('Asia/Kolkata'))

    def test_long_schedule_and_duplicate_guard(self):
        self.assertIsNone(longform.choose_episode({'videos':{}},self.now.replace(hour=18)))
        self.assertEqual(longform.choose_episode({'videos':{}},self.now),longform.EPISODE_ID)
        self.assertIsNone(longform.choose_episode({'videos':{'a':{'content_id':longform.EPISODE_ID}}},self.now))
        recent={'format':'long','published_at':(self.now-timedelta(days=6)).isoformat()}
        self.assertIsNone(longform.choose_episode({'videos':{'a':recent}},self.now))
        recent['published_at']=(self.now-timedelta(days=8)).isoformat()
        self.assertIsNotNone(longform.choose_episode({'videos':{'a':recent}},self.now))

    def test_research_runs_at_most_daily(self):
        data={'research':{'checked_at':(self.now-timedelta(hours=23)).isoformat()}}
        with patch.object(research.httpx,'Client') as client:
            self.assertFalse(research.collect('unused',data,self.now))
            client.assert_not_called()

    def test_research_failures_do_not_block_production(self):
        data={'videos':{}}
        with patch.object(research.httpx,'Client') as client:
            client.return_value.__enter__.return_value.get.side_effect=research.httpx.ConnectError('offline')
            self.assertTrue(research.collect('unused',data,self.now))
        self.assertEqual(len(data['research']['failures']),2)
        self.assertEqual(research.research_signals(data,self.now),[])

    def test_stale_research_never_looks_fresh(self):
        data={'research':{'checked_at':(self.now-timedelta(days=3)).isoformat(),'samples':[{'title':'space','genres':['space'],'region':'IN'}]}}
        self.assertEqual(research.research_signals(data,self.now),[])
        self.assertEqual(research.duration_seconds('PT3M24S'),204)
        self.assertEqual(research.duration_seconds('P1DT2H'),93600)

    def test_long_and_short_evidence_are_not_mixed(self):
        entry={'genre':'space','format':'long','published_at':(self.now-timedelta(hours=30)).isoformat(),
               'history':[{'at':self.now.isoformat(),'views':300}]}
        self.assertEqual(cloud.genre_scores({str(i):entry for i in range(3)}),{})

    def test_all_long_scenes_and_chapters(self):
        plan=longform.long_plan();cursor=0
        for s in plan:
            s.update(audio=np.ones(studio.RATE*8,dtype=np.float32)*.1,start=cursor,voice_start=cursor+.18,duration=10,end=cursor+10)
            cursor+=10
        for s in plan:
            self.assertEqual(longform.frame(plan,s['start']+1,cursor).size,(1920,1080))
        chapters=longform.chapter_lines(plan)
        self.assertEqual(len(chapters),5)
        self.assertTrue(chapters[0].startswith('0:00'))
        self.assertGreater(sum(len(s['speech'].split()) for s in plan),500)

    def test_one_end_invitation_per_short(self):
        for ch in cloud.content_catalog():
            base=studio._story_plan(ch);plan=studio.make_plan(ch)
            self.assertEqual(len(plan),len(base)+1)
            self.assertNotIn('countdown',plan[-1])

    def test_thumbnail_failure_does_not_reupload(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as td,patch.object(cloud.httpx,'Client') as client:
            p=Path(td)/'image.jpg';p.write_bytes(b'preview')
            client.return_value.__enter__.return_value.post.side_effect=cloud.httpx.ConnectError('offline')
            self.assertFalse(cloud.set_thumbnail('owned-video',p,'unused'))

if __name__=='__main__':unittest.main()
