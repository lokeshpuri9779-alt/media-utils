import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import remote_gpu_client as rgc


class FakeResponse:
    def __init__(self,status_code,payload=None,content=b"",headers=None,text=""):
        self.status_code=status_code
        self._payload=payload
        self.content=content
        self.headers=headers or {}
        self.text=text
    def json(self):
        return self._payload


class FakeClient:
    def __init__(self,*a,**kw):
        self.polls=0
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def post(self,url,headers=None,json=None):
        return FakeResponse(202,{"id":"job123","status":"queued"})
    def get(self,url,headers=None,timeout=None):
        if url.endswith("/video"):
            return FakeResponse(200,content=b"video-bytes",headers={"content-type":"video/mp4"})
        self.polls+=1
        if self.polls==1:
            return FakeResponse(200,{"id":"job123","status":"running"})
        return FakeResponse(200,{"id":"job123","status":"succeeded","provider":"ltx-local"})


class RemoteGPUJobProtocolTests(unittest.TestCase):
    def test_submit_poll_download(self):
        env={"ASTRA_GPU_WORKER_URL":"https://gpu.example","ASTRA_GPU_WORKER_TOKEN":"secret"}
        with patch.dict(os.environ,env,clear=True),              patch("remote_gpu_client.httpx.Client",FakeClient),              patch("remote_gpu_client.time.sleep",lambda _:None):
            with tempfile.TemporaryDirectory() as td:
                out=Path(td)/"x.mp4"
                report=rgc.generate_remote_clip({"prompt":"scene"},out,timeout_seconds=30)
                self.assertEqual(report["job_id"],"job123")
                self.assertEqual(report["worker_provider"],"ltx-local")
                self.assertEqual(out.read_bytes(),b"video-bytes")

    def test_unconfigured_worker_fails_closed(self):
        with patch.dict(os.environ,{},clear=True):
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaises(rgc.RemoteGPUUnavailable):
                    rgc.generate_remote_clip({"prompt":"scene"},Path(td)/"x.mp4")


if __name__=="__main__":
    unittest.main()
