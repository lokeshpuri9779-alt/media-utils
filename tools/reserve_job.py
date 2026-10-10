"""Fail-closed job reservations for one shared state file on one filesystem.

Cross-run GitHub Actions needs an external shared state and serialized workflow;
this local lock does NOT coordinate independent runners. No publishing here.
"""
import argparse
import json
import os
import time
from pathlib import Path
from tools.engine_lanes import eligible, load, save


def reserve(path, key, ttl=1800):
    if not 60 <= ttl <= 7200:
        raise ValueError('ttl out of range')
    lock = Path(str(path) + '.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise RuntimeError('State locked: fail closed; manual stale-lock recovery required')
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(str(os.getpid()))
        state = load(path)
        matches = [j for j in state['jobs'] if j['key'] == key]
        if len(matches) != 1 or not eligible(state, matches[0]):
            return False
        job = matches[0]
        job['status'] = 'reserved'
        job['reserved_at'] = int(time.time())
        job['reservation_expires_at'] = job['reserved_at'] + ttl
        save(path, state)
        return True
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--key', required=True)
    args = parser.parse_args()
    print(json.dumps({'reserved': reserve(args.state, args.key)}))

if __name__ == '__main__':
    main()
