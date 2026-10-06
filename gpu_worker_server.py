from __future__ import annotations

"""Authenticated Astra GPU worker job service.

Endpoints:
- GET  /health
- POST /jobs
- GET  /jobs/<id>
- GET  /jobs/<id>/video

One render executes at a time per worker to avoid VRAM contention.
The service binds to localhost by default; expose it only through a secure
TLS tunnel/reverse proxy.
"""

import json
import os
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from gpu_worker_health import worker_health
from open_source_video_engine import generate_open_source_clip


HOST=(os.environ.get("ASTRA_GPU_BIND") or "127.0.0.1").strip()
PORT=int(os.environ.get("ASTRA_GPU_PORT") or "8765")
TOKEN=(os.environ.get("ASTRA_GPU_WORKER_TOKEN") or "").strip()
MAX_BODY=64_000
JOB_TTL_SECONDS=int(os.environ.get("ASTRA_GPU_JOB_TTL_SECONDS") or "3600")

_JOBS: dict[str, dict] = {}
_LOCK=threading.Lock()
_RENDER_LOCK=threading.Lock()


def _authorized(handler: BaseHTTPRequestHandler) -> bool:
    return bool(TOKEN) and handler.headers.get("Authorization","")==f"Bearer {TOKEN}"


def _prune_jobs() -> None:
    cutoff=time.time()-JOB_TTL_SECONDS
    with _LOCK:
        stale=[
            job_id for job_id,job in _JOBS.items()
            if float(job.get("updated_at") or 0)<cutoff
            and job.get("status") in {"succeeded","failed"}
        ]
        for job_id in stale:
            path=_JOBS[job_id].get("output_path")
            if path:
                try: Path(path).unlink(missing_ok=True)
                except Exception: pass
            _JOBS.pop(job_id,None)


def _job_public(job: dict) -> dict:
    return {
        "id":job["id"],
        "status":job["status"],
        "created_at":job["created_at"],
        "updated_at":job["updated_at"],
        "error":job.get("error"),
        "provider":job.get("provider"),
        "bytes":job.get("bytes"),
    }


def _render_job(job_id: str, shot: dict) -> None:
    with _RENDER_LOCK:
        with _LOCK:
            job=_JOBS[job_id]
            job["status"]="running"
            job["updated_at"]=time.time()
        try:
            root=Path(tempfile.gettempdir())/"astra_gpu_jobs"
            root.mkdir(parents=True,exist_ok=True)
            out=root/f"{job_id}.mp4"
            report=generate_open_source_clip(shot,out)
            with _LOCK:
                job=_JOBS[job_id]
                job.update(
                    status="succeeded",
                    updated_at=time.time(),
                    output_path=str(out),
                    provider=str(report.get("provider") or "open-source"),
                    bytes=out.stat().st_size,
                )
        except Exception as exc:
            with _LOCK:
                job=_JOBS[job_id]
                job.update(status="failed",updated_at=time.time(),error=str(exc)[:500])


class Handler(BaseHTTPRequestHandler):
    server_version="AstraGPU/2.0"

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
        _prune_jobs()
        if not _authorized(self):
            self._json(401,{"error":"unauthorized"}); return

        if self.path=="/health":
            h=worker_health()
            h["ready"]=bool(h.get("providers",{}).get("ready"))
            h["queue_depth"]=sum(1 for j in _JOBS.values() if j.get("status") in {"queued","running"})
            self._json(200,h); return

        parts=[p for p in self.path.split("/") if p]
        if len(parts)>=2 and parts[0]=="jobs":
            job_id=parts[1]
            with _LOCK:
                job=_JOBS.get(job_id)
                snapshot=dict(job) if job else None
            if not snapshot:
                self._json(404,{"error":"job not found"}); return
            if len(parts)==2:
                self._json(200,_job_public(snapshot)); return
            if len(parts)==3 and parts[2]=="video":
                if snapshot.get("status")!="succeeded":
                    self._json(409,{"error":"job not complete","status":snapshot.get("status")}); return
                path=Path(snapshot["output_path"])
                if not path.is_file():
                    self._json(410,{"error":"video expired"}); return
                data=path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type","video/mp4")
                self.send_header("Content-Length",str(len(data)))
                self.send_header("X-Astra-Provider",str(snapshot.get("provider") or "open-source"))
                self.end_headers()
                self.wfile.write(data)
                return

        self._json(404,{"error":"not found"})

    def do_POST(self):
        _prune_jobs()
        if not _authorized(self):
            self._json(401,{"error":"unauthorized"}); return
        if self.path!="/jobs":
            self._json(404,{"error":"not found"}); return
        try:
            length=int(self.headers.get("Content-Length") or "0")
        except ValueError:
            self._json(400,{"error":"bad content length"}); return
        if length<=0 or length>MAX_BODY:
            self._json(413,{"error":"request too large"}); return
        try:
            payload=json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._json(400,{"error":"invalid json"}); return

        prompt=str(payload.get("prompt") or "").strip()
        if not prompt:
            self._json(400,{"error":"prompt required"}); return
        shot={
            "prompt":prompt,
            "negative":str(payload.get("negative") or ""),
            "target_seconds":payload.get("target_seconds") or [1.8,3.2],
            "variant":str(payload.get("variant") or ""),
        }
        job_id=uuid.uuid4().hex
        now=time.time()
        with _LOCK:
            _JOBS[job_id]={
                "id":job_id,
                "status":"queued",
                "created_at":now,
                "updated_at":now,
            }
        threading.Thread(target=_render_job,args=(job_id,shot),daemon=True).start()
        self._json(202,{"id":job_id,"status":"queued"})


def main():
    if not TOKEN:
        raise SystemExit("ASTRA_GPU_WORKER_TOKEN must be set.")
    httpd=ThreadingHTTPServer((HOST,PORT),Handler)
    print(f"Astra GPU worker listening on {HOST}:{PORT}")
    httpd.serve_forever()


if __name__=="__main__":
    main()
