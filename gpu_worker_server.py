from __future__ import annotations

"""Minimal authenticated Astra GPU worker service.

Runs on the GPU machine. Uses only Python stdlib + Astra's existing dependencies.
Endpoints:
- GET /health
- POST /render -> returns MP4 bytes

The service binds to localhost by default. Put it behind a secure tunnel/reverse
proxy if remote access is required. Never expose it publicly without auth/TLS.
"""

import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from gpu_worker_health import worker_health
from open_source_video_engine import generate_open_source_clip


HOST=(os.environ.get("ASTRA_GPU_BIND") or "127.0.0.1").strip()
PORT=int(os.environ.get("ASTRA_GPU_PORT") or "8765")
TOKEN=(os.environ.get("ASTRA_GPU_WORKER_TOKEN") or "").strip()
MAX_BODY=64_000


def _authorized(handler: BaseHTTPRequestHandler) -> bool:
    if not TOKEN:
        return False
    return handler.headers.get("Authorization","")==f"Bearer {TOKEN}"


class Handler(BaseHTTPRequestHandler):
    server_version="AstraGPU/1.0"

    def log_message(self, format, *args):
        return

    def _json(self,status:int,payload:dict):
        data=json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path!="/health":
            self._json(404,{"error":"not found"}); return
        if not _authorized(self):
            self._json(401,{"error":"unauthorized"}); return
        h=worker_health()
        h["ready"]=bool(h.get("providers",{}).get("ready"))
        self._json(200,h)

    def do_POST(self):
        if self.path!="/render":
            self._json(404,{"error":"not found"}); return
        if not _authorized(self):
            self._json(401,{"error":"unauthorized"}); return
        try:
            length=int(self.headers.get("Content-Length") or "0")
        except ValueError:
            self._json(400,{"error":"bad content length"}); return
        if length<=0 or length>MAX_BODY:
            self._json(413,{"error":"request too large"}); return
        try:
            payload=json.loads(self.rfile.read(length).decode("utf-8"))
            prompt=str(payload.get("prompt") or "").strip()
            if not prompt:
                self._json(400,{"error":"prompt required"}); return
            shot={
                "prompt":prompt,
                "negative":str(payload.get("negative") or ""),
                "target_seconds":payload.get("target_seconds") or [1.8,3.2],
                "variant":str(payload.get("variant") or ""),
            }
            with tempfile.TemporaryDirectory(prefix="astra_gpu_http_") as td:
                out=Path(td)/"clip.mp4"
                report=generate_open_source_clip(shot,out)
                data=out.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type","video/mp4")
            self.send_header("Content-Length",str(len(data)))
            self.send_header("X-Astra-Provider",str(report.get("provider") or "open-source"))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            self._json(500,{"error":str(exc)[:500]})


def main():
    if not TOKEN:
        raise SystemExit("ASTRA_GPU_WORKER_TOKEN must be set.")
    httpd=ThreadingHTTPServer((HOST,PORT),Handler)
    print(f"Astra GPU worker listening on {HOST}:{PORT}")
    httpd.serve_forever()


if __name__=="__main__":
    main()
