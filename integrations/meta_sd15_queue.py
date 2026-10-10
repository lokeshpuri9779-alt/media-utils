"""Independent SD1.5 asset queue for RAYVAN ASTRA.

No publisher access. Requests are JSON files in pending/, claimed atomically by
rename into working/, and moved to done/ or failed/. One worker per queue
folder; separate GitHub runs require external serialization to avoid races.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integrations.meta_cpu_diffusion import MODELS, generate


def enqueue(root: Path, *, prompt: str, profile: str = 'quality', seed: int = 1234,
            steps: int = 30, format_name: str = 'short') -> str:
    if profile not in MODELS or not prompt.strip() or format_name not in ('short', 'long'):
        raise ValueError('Invalid asset request')
    if not 1 <= steps <= 100:
        raise ValueError('Invalid steps')
    request = {'prompt': prompt, 'profile': profile, 'seed': seed,
               'steps': steps, 'format': format_name}
    key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:24]
    for folder in ('pending', 'working', 'done', 'failed', 'images'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    if any((root / folder / (key + '.json')).exists() for folder in ('pending','working','done','failed')):
        return key
    target = root / 'pending' / (key + '.json')
    with target.open('x') as f:
        json.dump({'id': key, **request}, f, indent=2)
    return key


def work_one(root: Path, *, enable_generation: bool = False) -> dict:
    if not enable_generation:
        return {'status': 'disabled', 'reason': 'Generation requires explicit opt-in'}
    pending = root / 'pending'
    lock = root / '.worker_lock'
    try:
        lock.mkdir()
    except FileExistsError:
        return {'status': 'busy', 'reason': 'Another worker holds the queue lock'}
    try:
        return _work_claimed(root, pending)
    finally:
        lock.rmdir()


def _work_claimed(root: Path, pending: Path) -> dict:
    for job in sorted(pending.glob('*.json')) if pending.exists() else []:
        working = root / 'working' / job.name
        working.parent.mkdir(parents=True, exist_ok=True)
        try:
            job.rename(working)
        except FileNotFoundError:
            continue
        data = json.loads(working.read_text())
        output = root / 'images' / (data['id'] + '.png')
        try:
            result = generate(data['prompt'], output, enabled=True, steps=data['steps'],
                              seed=data['seed'], profile=data['profile'])
            if not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError('Missing image output')
            data['result'] = result
            data['sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
            data['status'] = 'generated_unreviewed'
            destination = root / 'done' / job.name
        except Exception as exc:
            data['status'] = 'failed'
            data['error'] = f'{type(exc).__name__}: {exc}'
            destination = root / 'failed' / job.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(data, indent=2))
        working.unlink()
        return {'id': data['id'], 'status': data['status'], 'image': str(output) if data['status'] == 'generated_unreviewed' else None}
    return {'status': 'empty'}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path('artifacts/sd15_queue'))
    sub = p.add_subparsers(dest='action', required=True)
    add = sub.add_parser('enqueue')
    add.add_argument('--prompt', required=True)
    add.add_argument('--profile', choices=sorted(MODELS), default='quality')
    add.add_argument('--seed', type=int, default=1234)
    add.add_argument('--steps', type=int, default=30)
    add.add_argument('--format', choices=['short','long'], default='short')
    run = sub.add_parser('work')
    run.add_argument('--enable-generation', action='store_true')
    args = p.parse_args()
    if args.action == 'enqueue':
        result = {'id': enqueue(args.root, prompt=args.prompt, profile=args.profile,
                                seed=args.seed, steps=args.steps, format_name=args.format)}
    else:
        result = work_one(args.root, enable_generation=args.enable_generation)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
