"""CPU-first Meta ASTRA quality feasibility probe; never claims video was generated.
Run locally or on a standard GitHub runner. No network, secrets, or publisher.
"""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path


def available_memory_gib() -> float | None:
    # Prefer cgroup limits: hosted runners and containers may report host RAM
    # through /proc/meminfo even when the job has a much smaller limit.
    cgroup_limit = Path('/sys/fs/cgroup/memory.max')
    cgroup_used = Path('/sys/fs/cgroup/memory.current')
    if cgroup_limit.is_file() and cgroup_used.is_file():
        limit = cgroup_limit.read_text().strip()
        if limit.isdigit():
            remaining = max(0, int(limit) - int(cgroup_used.read_text().strip()))
            return round(remaining / (1024 ** 3), 2)
    path = Path('/proc/meminfo')
    if not path.is_file():
        return None
    for line in path.read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return round(int(line.split()[1]) / (1024 * 1024), 2)
    return None


def assess(*, disk_path: Path = Path('.'), required_ram_gib: float = 12.0,
           required_disk_gib: float = 12.0) -> dict:
    if required_ram_gib <= 0 or required_disk_gib <= 0:
        raise ValueError('Resource requirements must be positive')
    disk = round(shutil.disk_usage(disk_path).free / (1024 ** 3), 2)
    memory = available_memory_gib()
    blockers = []
    if memory is None:
        blockers.append('Available memory cannot be measured')
    elif memory < required_ram_gib:
        blockers.append(f'Insufficient RAM: {memory} GiB available; {required_ram_gib} GiB requested')
    if disk < required_disk_gib:
        blockers.append(f'Insufficient disk: {disk} GiB free; {required_disk_gib} GiB requested')
    return {
        'cpu_only': True, 'quality_priority': 'maximum', 'available_ram_gib': memory,
        'free_disk_gib': disk, 'resource_check_passed': not blockers,
        'generation_verified': False, 'blockers': blockers,
        'note': 'Passing resource checks does not prove any diffusion model can run or produce quality video',
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--disk-path', type=Path, default=Path('.'))
    parser.add_argument('--required-ram-gib', type=float, default=12)
    parser.add_argument('--required-disk-gib', type=float, default=12)
    args = parser.parse_args()
    result = assess(disk_path=args.disk_path, required_ram_gib=args.required_ram_gib,
                    required_disk_gib=args.required_disk_gib)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['resource_check_passed'] else 1)

if __name__ == '__main__':
    main()
