"""Experimental renderer registry. Never used by the production publisher.

Promotion requires actual benchmark artifacts and an explicit separate integration.
"""
from __future__ import annotations

ENGINES = {
    'openvino_sd15': {'kind': 'keyframe', 'entrypoint': 'tools/experimental_openvino_benchmark.py', 'workflow': 'experimental-openvino.yml', 'verified': False},
    'blender_cpu': {'kind': '3d_animation', 'entrypoint': 'tools/experimental_animation_benchmark.py', 'workflow': 'experimental-animation.yml', 'verified': False},
    'godot': {'kind': '2d_animation', 'entrypoint': 'tools/experimental_godot_benchmark.py', 'workflow': 'experimental-godot.yml', 'verified': False},
}


def eligible_for_production(engine: str, report: dict | None = None) -> bool:
    """Experimental output cannot be silently routed to production."""
    if engine not in ENGINES:
        raise ValueError('Unknown engine')
    return bool(ENGINES[engine]['verified'] and report and report.get('success') and report.get('quality_pass'))


def summarize(engine: str, report: dict) -> dict:
    if engine not in ENGINES:
        raise ValueError('Unknown engine')
    return {'engine': engine, 'kind': ENGINES[engine]['kind'],
            'benchmark_success': bool(report.get('success')),
            'seconds': report.get('elapsed_seconds'),
            'production_eligible': eligible_for_production(engine, report)}
