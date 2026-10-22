"""Opt-in PostgreSQL task ledger for independent ASTRA worker dispatch.

Not wired to live publisher. Expired claims require reconciliation, not automatic
redispatch: a worker may have performed an irreversible external action.
"""
from __future__ import annotations

import uuid
from astra_v2.adaptive_shared_queue import _identity, _lease
from astra_v2.event_task_graph import STAGES

STAGE_NAMES = frozenset(name for name, _ in STAGES)
DDL = """
CREATE TABLE IF NOT EXISTS astra_event_tasks_v1 (
 namespace TEXT NOT NULL, content_id TEXT NOT NULL, stage TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending'
   CHECK (status IN ('pending','running','succeeded','failed','quarantined')),
 attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
 lease_token TEXT, lease_until TIMESTAMPTZ,
 result_ref TEXT, error_code TEXT,
 PRIMARY KEY(namespace,content_id,stage),
 CHECK ((status='running' AND lease_token IS NOT NULL AND lease_until IS NOT NULL)
     OR (status<>'running' AND lease_token IS NULL AND lease_until IS NULL))
);
CREATE INDEX IF NOT EXISTS astra_event_tasks_pending_v1
 ON astra_event_tasks_v1(namespace,stage,content_id) WHERE status='pending';
"""


class EventLedger:
    def __init__(self, warehouse):
        self.warehouse = warehouse

    def initialize(self):
        with self.warehouse._db() as db:
            db.execute(DDL)

    def register(self, content_id):
        _identity(content_id)
        with self.warehouse._db() as db:
            for stage, _ in STAGES:
                db.execute("""INSERT INTO astra_event_tasks_v1
                    (namespace,content_id,stage) VALUES (%s,%s,%s)
                    ON CONFLICT DO NOTHING""",
                    (self.warehouse.namespace, content_id, stage))

    def claim(self, content_id, stage, *, lease_seconds=900):
        _identity(content_id)
        if stage not in STAGE_NAMES:
            raise ValueError("invalid_stage")
        _lease(lease_seconds)
        token = uuid.uuid4().hex
        deps = dict(STAGES)[stage]
        with self.warehouse._db() as db:
            # Serialize claims and prerequisite transitions for this content ID.
            rows = db.execute("""SELECT stage,status FROM astra_event_tasks_v1
                WHERE namespace=%s AND content_id=%s FOR UPDATE""",
                (self.warehouse.namespace, content_id)).fetchall()
            states = dict(rows)
            if states.get(stage) != "pending" or any(states.get(d) != "succeeded" for d in deps):
                return None
            row = db.execute("""UPDATE astra_event_tasks_v1
                SET status='running', attempts=attempts+1,lease_token=%s,
                    lease_until=clock_timestamp()+%s*INTERVAL '1 second'
                WHERE namespace=%s AND content_id=%s AND stage=%s AND status='pending'
                RETURNING attempts,lease_until""",
                (token,lease_seconds,self.warehouse.namespace,content_id,stage)).fetchone()
            return None if row is None else {"content_id":content_id,"stage":stage,
                "lease_token":token,"attempt":row[0],"lease_until":row[1].isoformat()}

    def finish(self, content_id, stage, token, *, status, result_ref=None, error_code=None):
        _identity(content_id)
        if stage not in STAGE_NAMES or status not in {"succeeded","failed","quarantined"}:
            raise ValueError("invalid_terminal_state")
        if not isinstance(token,str) or len(token)!=32 or any(c not in "0123456789abcdef" for c in token):
            raise ValueError("invalid_token")
        if result_ref is not None and (not isinstance(result_ref,str) or len(result_ref)>1024):
            raise ValueError("invalid_result_ref")
        if error_code is not None and (not isinstance(error_code,str) or len(error_code)>128):
            raise ValueError("invalid_error_code")
        with self.warehouse._db() as db:
            row=db.execute("""UPDATE astra_event_tasks_v1
                SET status=%s,lease_token=NULL,lease_until=NULL,
                    result_ref=%s,error_code=%s
                WHERE namespace=%s AND content_id=%s AND stage=%s
                    AND status='running' AND lease_token=%s
                    AND lease_until>clock_timestamp() RETURNING stage""",
                (status,result_ref,error_code,self.warehouse.namespace,content_id,stage,token)).fetchone()
            if row is None:
                raise ValueError("invalid_or_expired_task_lease")
            return True

    def states(self, content_id):
        _identity(content_id)
        with self.warehouse._db() as db:
            rows=db.execute("""SELECT stage,status FROM astra_event_tasks_v1
                WHERE namespace=%s AND content_id=%s""",
                (self.warehouse.namespace,content_id)).fetchall()
        return dict(rows)
