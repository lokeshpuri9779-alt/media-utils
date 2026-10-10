"""Benchmark Meta ASTRA's actual CPU diffusion generation, never publishing.

Usage (after installing torch, diffusers, transformers, accelerate, pillow):
  python tools/meta_cpu_benchmark.py --profile quality --output artifacts/meta_keyframe.png
Runs the real pipeline, measures elapsed time and peak process RSS, writes a JSON
report even when generation fails. No automatic fallback or synthetic replacement.
"""
from __future__ import annotations
import argparse
import json
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integrations.meta_cpu_diffusion import MODELS, generate

DEFAULT_PROMPT = ('cinematic stylized 3D animation film still, expressive small copper robot '
                  'holding a glowing golden star in a rainy magical forest, beautiful '
                  'art direction, volumetric lighting, detailed composition, no text')


def benchmark(*, profile: str, output: Path, prompt: str, steps: int = 30,
              seed: int = 1234, report: Path | None = None) -> dict:
    if profile not in MODELS:
        raise ValueError('Unknown profile')
    report = report or output.with_suffix('.benchmark.json')
    started = time.monotonic()
    result = {'profile': profile, 'model': MODELS[profile], 'cpu_only': True,
              'prompt': prompt, 'steps': steps, 'seed': seed,
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'published': False, 'success': False}
    try:
        produced = generate(prompt, output, enabled=True, steps=steps,
                            seed=seed, profile=profile)
        result['success'] = output.is_file() and output.stat().st_size > 0
        result['output'] = produced['output']
        result['bytes'] = output.stat().st_size if output.is_file() else 0
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - started, 2)
        # ru_maxrss is KiB on Linux; runner uses Ubuntu.
        result['peak_process_rss_mib_linux'] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--profile', choices=sorted(MODELS), default='quality')
    p.add_argument('--output', type=Path, default=Path('artifacts/meta_keyframe.png'))
    p.add_argument('--report', type=Path)
    p.add_argument('--prompt', default=DEFAULT_PROMPT)
    p.add_argument('--steps', type=int, default=30)
    p.add_argument('--seed', type=int, default=1234)
    args = p.parse_args()
    result = benchmark(profile=args.profile, output=args.output, prompt=args.prompt,
                       steps=args.steps, seed=args.seed, report=args.report)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['success'] else 1)

if __name__ == '__main__':
    main()
