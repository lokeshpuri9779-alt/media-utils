"""Measure actual GitHub runner capabilities without installing AI models or publishing.
Run: python tools/github_runner_probe.py --output artifacts/runner_capabilities.json
"""
from __future__ import annotations
import argparse
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


def _command_version(command: str, args: list[str]) -> str | None:
    executable = shutil.which(command)
    if not executable:
        return None
    try:
        result = subprocess.run([executable, *args], capture_output=True, text=True, timeout=10)
        return (result.stdout or result.stderr).splitlines()[0][:180] if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return None


def _meminfo_gib() -> float | None:
    p = Path('/proc/meminfo')
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return round(int(line.split()[1]) / 1048576, 2)
    return None


def probe() -> dict:
    disk = shutil.disk_usage('.')
    result = {
        'platform': platform.platform(),
        'runner_os': os.getenv('RUNNER_OS'),
        'runner_arch': os.getenv('RUNNER_ARCH'),
        'github_actions': os.getenv('GITHUB_ACTIONS') == 'true',
        'cpu_count_logical': os.cpu_count(),
        'mem_available_gib_host': _meminfo_gib(),
        'disk_free_gib': round(disk.free / 1073741824, 2),
        'tools': {name: _command_version(name, args) for name, args in {
            'ffmpeg': ['-version'], 'blender': ['--version'],
            'godot': ['--version'], 'python3': ['--version']}.items()},
        'published': False,
        'generation_verified': False,
        'note': 'Inventory only: does not establish model feasibility or output quality',
    }
    limit = Path('/sys/fs/cgroup/memory.max')
    used = Path('/sys/fs/cgroup/memory.current')
    if limit.is_file() and used.is_file() and limit.read_text().strip().isdigit():
        result['cgroup_memory_remaining_gib'] = round(max(0, int(limit.read_text()) - int(used.read_text())) / 1073741824, 2)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('artifacts/runner_capabilities.json'))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = probe()
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
