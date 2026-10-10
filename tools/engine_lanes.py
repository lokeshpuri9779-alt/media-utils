"""Independent production-lane coordinator. No uploads or external API calls.

Maintains distinct queues for current ASTRA and Meta ASTRA. This module does NOT
alter existing workflows. Atomic replacement prevents partial files; cross-run locking is not yet provided.
"""
import argparse
import json
import os
import tempfile
import time
from pathlib import Path

LANES = ('current', 'meta')
FORMATS = ('short', 'long')

def load(path):
    if not path.exists():
        return {'version': 1, 'jobs': [], 'published': []}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('version') != 1:
        raise ValueError('Unsupported state version')
    return data

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.astra-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def enqueue(state, lane, fmt, key, artifact):
    if lane not in LANES or fmt not in FORMATS:
        raise ValueError('Unknown lane or format')
    if not key or not artifact:
        raise ValueError('key and artifact are required')
    if any(job['key'] == key for job in state['jobs']) or any(pub['key'] == key for pub in state['published']):
        return False
    state['jobs'].append({'lane': lane, 'format': fmt, 'key': key,
                          'artifact': artifact, 'status': 'queued', 'created_at': int(time.time())})
    return True

def eligible(state, job, now=None):
    now = int(time.time()) if now is None else now
    if job['status'] != 'queued':
        return False
    if job['format'] == 'long':
        if any(other is not job and other['format'] == 'long' and other['status'] in ('reserved', 'uploading', 'awaiting_confirmation') for other in state['jobs']):
            return False
        last = max((p['confirmed_at'] for p in state['published'] if p['format'] == 'long'), default=0)
        if last and now - last < 86400:
            return False
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--state', type=Path, default=Path('state/engine_lanes.json'))
    sub = p.add_subparsers(dest='action', required=True)
    q = sub.add_parser('enqueue')
    q.add_argument('--lane', choices=LANES, required=True)
    q.add_argument('--format', choices=FORMATS, required=True)
    q.add_argument('--key', required=True)
    q.add_argument('--artifact', required=True)
    sub.add_parser('status')
    args = p.parse_args()
    state = load(args.state)
    if args.action == 'enqueue':
        print('queued' if enqueue(state, args.lane, args.format, args.key, args.artifact) else 'duplicate')
        save(args.state, state)
    else:
        print(json.dumps({'jobs': state['jobs'], 'published': state['published'],
                          'eligible_keys': [j['key'] for j in state['jobs'] if eligible(state, j)]}, indent=2))

if __name__ == '__main__':
    main()
