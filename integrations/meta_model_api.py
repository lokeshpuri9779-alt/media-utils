"""Meta Model API Muse Image adapter, fail-closed for restricted regions.

No network calls until explicitly enabled. Never use geographic workarounds.
Meta policy (2026-09-18) restricts Muse Image access from India.
Muse Video has no verified public generation endpoint.
"""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

API_URL = 'https://api.meta.ai/v1/images/generations'
MODEL = 'muse-image-1.0'


def generate(prompt: str, output: Path, *, region: str, enabled: bool = False) -> dict:
    if not enabled:
        raise RuntimeError('Meta generation disabled until explicitly enabled and permitted')
    if region.strip().upper() in {'IN', 'IND', 'INDIA'}:
        raise PermissionError('Muse Image is unavailable in India under Meta geographic-use policy')
    if not region.strip():
        raise ValueError('An actual eligible execution region must be provided')
    key = os.environ.get('META_MODEL_API_KEY', '')
    if not key:
        raise RuntimeError('META_MODEL_API_KEY is missing')
    if not prompt.strip():
        raise ValueError('Prompt required')
    payload = json.dumps({'model': MODEL, 'prompt': prompt, 'n': 1}).encode('utf-8')
    request = Request(API_URL, data=payload, headers={
        'Authorization': f'Bearer {key}', 'Content-Type': 'application/json',
    }, method='POST')
    with urlopen(request, timeout=120) as response:
        data = json.load(response)
    image = data['data'][0]
    if 'b64_json' not in image:
        raise RuntimeError('API response did not include base64 image; signed-URL output not yet supported')
    raw = base64.b64decode(image['b64_json'], validate=True)
    if not raw.startswith(b'\\x89PNG') and not raw.startswith(b'\\xff\\xd8'):
        raise ValueError('Unrecognized image format')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {'output': str(output), 'source': 'meta-model-api', 'model': MODEL, 'published': False}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--prompt', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--region', required=True, help='Actual permitted execution region, not a proxy/VPN location')
    p.add_argument('--enable', action='store_true')
    args = p.parse_args()
    print(json.dumps(generate(args.prompt, args.output, region=args.region, enabled=args.enable), indent=2))

if __name__ == '__main__':
    main()
