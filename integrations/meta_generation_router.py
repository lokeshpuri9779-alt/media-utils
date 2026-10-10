"""Fail-closed alternative generator routing for Meta ASTRA.

Meta ASTRA is a production lane, not a claim that every scene came from Meta AI.
No provider is treated as connected without a verified runtime.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

BACKENDS = {
    'ltx_video': {'kind': 'open_source_video', 'requires_gpu': True, 'connected': False},
    'wan': {'kind': 'open_source_video', 'requires_gpu': True, 'connected': False},
    'local_scene_import': {'kind': 'existing_licensed_video', 'requires_gpu': False, 'connected': True},
}


def choose(*, gpu_available: bool = False, prefer: str = 'ltx_video') -> dict:
    if prefer not in BACKENDS:
        raise ValueError(f'Unknown backend: {prefer}')
    backend = BACKENDS[prefer]
    if backend['requires_gpu'] and not gpu_available:
        return {'ready': False, 'backend': prefer, 'reason': 'GPU runtime unavailable; no synthetic output substituted'}
    if not backend['connected']:
        return {'ready': False, 'backend': prefer, 'reason': 'Model runtime not yet installed or verified'}
    return {'ready': True, 'backend': prefer, 'reason': 'Existing licensed clips can enter the Meta assembly pipeline'}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--backend', choices=sorted(BACKENDS), default='ltx_video')
    p.add_argument('--gpu-available', action='store_true')
    args = p.parse_args()
    result = choose(gpu_available=args.gpu_available, prefer=args.backend)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ready'] else 1)

if __name__ == '__main__':
    main()
