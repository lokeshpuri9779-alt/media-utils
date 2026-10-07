from __future__ import annotations

import json
from pathlib import Path

from channel_state import migrate_legacy
from provider_guard import write_run_diagnosis, policy_manifest


def _load(path: Path) -> dict:
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else {}
    except Exception:
        return {}


def main() -> None:
    quota=_load(Path("quota_state.json"))
    perf=_load(Path("performance.json"))
    ops_path=migrate_legacy("ops_state.json")
    ops=_load(ops_path)
    out=Path("runtime-health/run-diagnosis.json")
    write_run_diagnosis(out,quota_state=quota,ops_state=ops,performance=perf)

    data=_load(out)
    data["provider_policy"]=policy_manifest()
    out.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")

    summary=Path("runtime-health/summary.txt")
    summary.write_text(
        "\n".join([
            f"limit_hit={quota.get('limit_hit',False)}",
            f"limit_reason={quota.get('limit_reason','')}",
            f"attempts={quota.get('attempts',0)}",
            f"successes={quota.get('successes',0)}",
            f"ops_status={ops.get('status','unknown')}",
            f"human_action_required={ops.get('human_action_required') or ''}",
            f"tracked_videos={len((perf.get('videos') or {}))}",
        ])+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
