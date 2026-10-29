"""Read-only CPU environment probe for ASTRA experimental image benchmarks.

No model downloads, inference, image approval, production fallback, or publishing.
"""
import json
import os
from pathlib import Path
import platform
import time


def read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return None


def cpu_model():
    data = read("/proc/cpuinfo") or ""
    for line in data.splitlines():
        if line.lower().startswith("model name") and ":" in line:
            return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"



def effective_cpu_quota(v2, v1_quota, v1_period):
    """Return a numeric CPU ceiling, or None when unlimited/unavailable."""
    try:
        if v2:
            quota, period = v2.split()
            if quota == "max":
                return None
            quota, period = int(quota), int(period)
        else:
            quota, period = int(v1_quota), int(v1_period)
        return round(quota / period, 3) if quota > 0 and period > 0 else None
    except (ValueError, TypeError):
        return None


def collect():
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    quota = read("/sys/fs/cgroup/cpu.max")
    cpu_period = read("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    cpu_quota = read("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    return {
        "diagnostic_only": True,
        "approved": False,
        "production_ready": False,
        "published": False,
        "images_generated": 0,
        "timestamp_unix": time.time(),
        "cpu_model": cpu_model(),
        "logical_cpu_count": os.cpu_count(),
        "affinity_cpu_ids": affinity,
        "affinity_cpu_count": len(affinity) if affinity is not None else None,
        "cgroup_v2_cpu_max": quota,
        "cgroup_v1_cpu_quota_us": cpu_quota,
        "cgroup_v1_cpu_period_us": cpu_period,
        "effective_cgroup_cpu_quota": effective_cpu_quota(quota, cpu_quota, cpu_period),
        "openvino_env": {k: v for k, v in os.environ.items()
                         if k in ("OMP_NUM_THREADS", "OPENVINO_NUM_THREADS", "OV_NUM_THREADS",
                                  "KMP_AFFINITY", "KMP_BLOCKTIME", "OMP_PROC_BIND")},
        "mem_available_kib": next((line.split()[1] for line in
                                    (read("/proc/meminfo") or "").splitlines()
                                    if line.startswith("MemAvailable:")), None),
        "cgroup_v2_memory_max": read("/sys/fs/cgroup/memory.max"),
    }


def main():
    output = Path("artifacts/experimental-openvino/cpu-runtime-probe.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = collect()
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
