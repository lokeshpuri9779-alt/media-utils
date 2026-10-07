"""Content-addressed Agnes checkpoints; contains no API keys or download URLs."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


class RenderCache:
    def __init__(self, payload: dict, account: str):
        root = os.environ.get('ASTRA_CHARACTER_CACHE', '').strip()
        # Include account identity, exact provider request and reference-image bytes.
        identity = {'schema': 1, 'account': hashlib.sha256(account.encode()).hexdigest(),
                    'request': payload}
        self.key = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.directory = Path(root).expanduser()/self.key if root else None
        self.state = {}
        if self.directory:
            try:
                state = json.loads((self.directory/'state.json').read_text())
                if isinstance(state, dict) and state.get('key') == self.key:
                    self.state = state
            except (OSError, ValueError):
                pass

    def _write(self):
        if not self.directory:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.directory/'state.json.tmp'
        temporary.write_text(json.dumps({'key': self.key, **self.state}, indent=2))
        temporary.replace(self.directory/'state.json')

    def completed(self, output: Path) -> dict | None:
        if not self.directory or self.state.get('status') != 'completed':
            return None
        cached = self.directory/'clip.mp4'
        try:
            digest = hashlib.sha256(cached.read_bytes()).hexdigest()
            if cached.stat().st_size == 0 or digest != self.state.get('video_sha256'):
                return None
            report = self.state['report']
            if not isinstance(report, dict):
                return None
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cached, output)
            self.directory.touch()
            return {**report, 'output_path': str(output), 'cache_hit': True}
        except (OSError, KeyError):
            return None

    def pending_job(self) -> str | None:
        # A corrupt/missing completed clip can be redownloaded from the same job.
        if self.state.get('status') in {'submitted', 'completed'}:
            job = self.state.get('video_id')
            if isinstance(job, str) and 0 < len(job) <= 256:
                return job
        return None

    def submitted(self, video_id: str):
        self.state = {'status': 'submitted', 'video_id': str(video_id)}
        self._write()

    def failed(self):
        self.state['status'] = 'failed'
        self._write()

    def finish(self, output: Path, report: dict):
        if not self.directory:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.directory/'clip.mp4.tmp'
        shutil.copyfile(output, temporary)
        temporary.replace(self.directory/'clip.mp4')
        self.state = {'status': 'completed', 'video_id': report['video_id'],
                      'video_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                      'report': {k: v for k, v in report.items() if k != 'output_path'}}
        self._write()
        # Bound each cloud cache snapshot while retaining several recent stories.
        directories = sorted((p for p in self.directory.parent.iterdir() if p.is_dir()),
                             key=lambda p: p.stat().st_mtime, reverse=True)
        for old in directories[32:]:
            if len(old.name) == 64 and all(c in '0123456789abcdef' for c in old.name):
                shutil.rmtree(old)
