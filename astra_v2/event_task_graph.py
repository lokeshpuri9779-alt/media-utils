"""Deterministic event-driven task graph for ASTRA.

This is a pure planning layer, not a second publisher or queue. Durable workers
can consume its ready events through the existing transactional queue. No
editorial approval or YouTube publication is granted by graph completion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

STAGES = (
    ("story", ()),
    ("editorial", ("story",)),
    ("assets", ("editorial",)),
    ("render", ("assets",)),
    ("media_qa", ("render",)),
    ("archive", ("media_qa",)),
    ("publish", ("archive",)),
    ("verify", ("publish",)),
    ("analytics", ("verify",)),
)
TERMINAL = frozenset({"succeeded", "failed", "quarantined"})
STATUSES = frozenset({"pending", "running", "succeeded", "failed", "quarantined"})


@dataclass(frozen=True)
class TaskEvent:
    content_id: str
    stage: str
    dependencies: tuple[str, ...]
    priority: int
    idempotency_key: str


def ready_events(content_id: str, states: Mapping[str, str],
                 *, priorities: Mapping[str, int] | None = None) -> list[TaskEvent]:
    """Return dispatchable tasks without mutating queue state or granting approval.

    The caller must atomically claim each task in a durable ledger. Successful
    editorial, QA and archive states must originate from trusted workers.
    """
    if not isinstance(content_id, str) or not content_id.strip():
        raise ValueError("content_id_required")
    known = {name for name, _ in STAGES}
    if any(k not in known or v not in STATUSES for k, v in states.items()):
        raise ValueError("invalid_task_state")
    priorities = priorities or {}
    if any(k not in known or not isinstance(v, int) or isinstance(v, bool)
           for k, v in priorities.items()):
        raise ValueError("invalid_priority")
    events = []
    for name, dependencies in STAGES:
        if states.get(name, "pending") != "pending":
            continue
        if not all(states.get(dep) == "succeeded" for dep in dependencies):
            continue
        events.append(TaskEvent(content_id, name, dependencies,
                                priorities.get(name, 0), f"{content_id}:{name}"))
    return sorted(events, key=lambda event: (-event.priority, event.stage))


def blocked_stages(states: Mapping[str, str]) -> tuple[str, ...]:
    """Stages downstream of a failed/quarantined prerequisite."""
    blocked = set()
    for name, dependencies in STAGES:
        if any(states.get(dep) in {"failed", "quarantined"} or dep in blocked
               for dep in dependencies):
            blocked.add(name)
    return tuple(name for name, _ in STAGES if name in blocked)
