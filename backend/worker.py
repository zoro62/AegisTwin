"""Single-consumer durable database queue. Restart requeues interrupted jobs.

Run exactly one worker; multi-worker leases are intentionally not claimed.
"""

import json
import logging
import time
from sqlalchemy import select
from .store import DB, Job, EventRow, timestamp
from .contracts import Inventory, Scenario, AnalysisRequest, PlanRequest
from .main import get_record, save
from .engine import analyse, optimise
from .validation import compare_events

logging.basicConfig(level=logging.INFO, format="%(message)s")


def recover():
    with DB() as db:
        for job in db.scalars(select(Job).where(Job.status == "running")).all():
            job.status = "queued"
            job.updated_at = timestamp()
        db.commit()


def process_one():
    with DB() as db:
        job = db.scalar(
            select(Job).where(Job.status == "queued").order_by(Job.created_at).limit(1)
        )
        if job is None:
            return False
        job.status = "running"
        job.updated_at = timestamp()
        db.commit()
        jid, workspace, kind, payload = job.id, job.workspace_id, job.kind, job.payload
    try:
        with DB() as db:
            scenario_record = get_record(
                db, workspace, payload["scenario_id"], "scenario"
            )
            scenario = Scenario.model_validate(scenario_record.data)
            snap = get_record(db, workspace, scenario.snapshot_id, "snapshot")
            inventory = Inventory.model_validate(snap.data)
            snapshot_hash = snap.content_hash

        def cancelled():
            with DB() as db:
                return db.get(Job, jid).status == "cancelled"

        if kind in ("analysis", "evaluation"):
            request = AnalysisRequest.model_validate(payload)
            result = analyse(inventory, scenario, request.limits, request.removed)
            if kind == "evaluation":
                with DB() as db:
                    observations = [
                        r.data
                        for r in db.scalars(
                            select(EventRow).where(
                                EventRow.workspace_id == workspace,
                                EventRow.snapshot_id == scenario.snapshot_id,
                            )
                        ).all()
                    ]
                # Preserve the exact event dataset used; later arrivals cannot rewrite evaluation.
                observations.sort(
                    key=lambda e: (e["source_timestamp"], e["source"], e["id"])
                )
                result = {
                    "analysis": result,
                    "validation": compare_events(
                        inventory, scenario, result, observations
                    ),
                    "dataset": observations,
                }
        else:
            request = PlanRequest.model_validate(payload)
            result = optimise(inventory, scenario, request, cancelled)
        with DB() as db:
            job = db.get(Job, jid)
            if job.status != "cancelled":
                record = save(
                    db,
                    workspace,
                    kind,
                    {
                        "scenario_id": payload["scenario_id"],
                        "snapshot_id": scenario.snapshot_id,
                        "snapshot_hash": snapshot_hash,
                        "request": payload,
                        "result": result,
                    },
                )
                job.status = "completed"
                job.result_id = record.id
                job.updated_at = timestamp()
                save(
                    db,
                    workspace,
                    "audit",
                    {
                        "action": "job_completed",
                        "job_id": jid,
                        "record_id": record.id,
                        "actor": "worker",
                    },
                )
                db.commit()
        logging.info(json.dumps({"event": "job_finished", "job_id": jid, "kind": kind}))
    except Exception as exc:
        logging.exception(json.dumps({"event": "job_failed", "job_id": jid}))
        with DB() as db:
            job = db.get(Job, jid)
            if job.status != "cancelled":
                job.status = "failed"
                job.error = str(exc)[:1000]
                job.updated_at = timestamp()
                db.commit()
    return True


if __name__ == "__main__":
    recover()
    while True:
        if not process_one():
            time.sleep(0.5)
