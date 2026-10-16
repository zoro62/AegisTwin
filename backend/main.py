import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from pathlib import Path
from collections import defaultdict, deque
from time import monotonic
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Query
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from .contracts import (
    Contract,
    Inventory,
    Scenario,
    AnalysisRequest,
    PlanRequest,
    Event,
    now,
    validate_scenario,
    Evidence,
)
from .store import (
    DB,
    User,
    Workspace,
    Membership,
    Session,
    Record,
    Element,
    EventRow,
    Job,
    project_record,
    DOMAIN,
)
from .fixtures import lab_fixture
from .imports import parse_inventory_csv
from .config import setting
from .reports import render_report
from .lab_observations import ProbeImport


class SnapshotCorrection(Contract):
    inventory: Inventory
    reason: str = Field(min_length=10, max_length=2000)
    confidence: str = Field(default="uncertain", pattern="^(confirmed|uncertain)$")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    )


def save(db, workspace, kind, data):
    content = json.dumps(data, sort_keys=True, separators=(",", ":"))
    record = Record(
        workspace_id=workspace, kind=kind, content_hash=digest(content), data=data
    )
    db.add(record)
    db.flush()
    project_record(db, record)
    return record


def snapshot(db, workspace, inventory):
    record = save(db, workspace, "snapshot", inventory.model_dump(mode="json"))
    for category in ("assets", "relationships", "evidence"):
        for value in record.data[category]:
            db.add(
                Element(
                    workspace_id=workspace,
                    snapshot_id=record.id,
                    category=category,
                    external_id=value["id"],
                    data=value,
                )
            )
    return record


def get_record(db, workspace, rid, kind=None):
    record = db.scalar(
        select(Record).where(Record.id == rid, Record.workspace_id == workspace)
    )
    if record is None or (kind and record.kind != kind):
        raise HTTPException(404, "Record not found")
    return record


def public_record(r):
    return {
        "id": r.id,
        "kind": r.kind,
        "created_at": r.created_at,
        "content_hash": r.content_hash,
        "data": r.data,
    }


def auth(request: Request):
    with DB() as db:
        session = db.get(Session, digest(request.cookies.get("aegis_session", "")))
        if session is None or session.expires <= now().isoformat():
            raise HTTPException(401, "Sign in required")
        if request.method not in ("GET", "HEAD", "OPTIONS") and not hmac.compare_digest(
            request.headers.get("x-csrf-token", ""), session.csrf
        ):
            raise HTTPException(403, "Invalid CSRF token")
        return {"user_id": session.user_id, "csrf": session.csrf}


def member(workspace_id: str, user=Depends(auth)):
    with DB() as db:
        membership = db.scalar(
            select(Membership).where(
                Membership.user_id == user["user_id"],
                Membership.workspace_id == workspace_id,
            )
        )
        if membership is None:
            raise HTTPException(404, "Workspace not found")
        return {**user, "workspace_id": workspace_id, "role": membership.role}


def analyst(context=Depends(member)):
    if context["role"] not in ("analyst", "administrator"):
        raise HTTPException(403, "Analyst role required")
    return context


@asynccontextmanager
async def lifespan(_):
    # Schema must be created through Alembic, never silently on application startup.
    yield


app = FastAPI(title="AegisTwin Lab v2", version="0.1.0", lifespan=lifespan)
login_attempts = defaultdict(deque)


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(
        {"detail": "Conflicting record or duplicate concurrent import"}, status_code=409
    )


@app.middleware("http")
async def boundary(request: Request, call_next):
    if request.url.path in ("/api/login", "/api/register") and request.method == "POST":
        key = (request.client.host if request.client else "local", request.url.path)
        current = monotonic()
        attempts = login_attempts[key]
        while attempts and attempts[0] < current - 60:
            attempts.popleft()
        if len(attempts) >= 20:
            return JSONResponse(
                {"detail": "Too many authentication attempts; wait one minute"},
                status_code=429,
            )
        attempts.append(current)
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return Response("Cross-origin write rejected", status_code=403)
        chunks = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 2_000_000:
                return Response("Upload limit is 2 MB", status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    )
    return response


class Credentials(Contract):
    email: str = Field(
        min_length=3, max_length=160, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    password: str = Field(min_length=12, max_length=128)


@app.get("/api/health")
def health():
    with DB() as db:
        db.execute(select(Workspace.id).limit(1))
    return {"status": "ok", "mode": "simulation-first", "version": "0.1.0"}


@app.post("/api/register", status_code=201)
def register(body: Credentials):
    with DB() as db:
        email = body.email.strip().lower()
        if db.scalar(select(User).where(User.email == email)):
            raise HTTPException(409, "Account already exists")
        user = User(email=email, password=password_hash(body.password))
        workspace = Workspace(name="AegisTwin lab workspace")
        db.add_all([user, workspace])
        db.flush()
        db.add(
            Membership(user_id=user.id, workspace_id=workspace.id, role="administrator")
        )
        save(
            db,
            workspace.id,
            "audit",
            {"action": "workspace_created", "user_id": user.id},
        )
        db.commit()
    return {"registered": True}


@app.post("/api/login")
def login(body: Credentials, response: Response):
    with DB() as db:
        user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
        if user is None or not hmac.compare_digest(
            user.password, password_hash(body.password, user.password.split(":")[0])
        ):
            raise HTTPException(401, "Invalid credentials")
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db.add(
            Session(
                token_hash=digest(token),
                user_id=user.id,
                csrf=csrf,
                expires=(now() + timedelta(hours=8)).isoformat(),
            )
        )
        db.commit()
        response.set_cookie(
            "aegis_session",
            token,
            httponly=True,
            samesite="strict",
            secure=setting("SECURE_COOKIES", "false") == "true",
            max_age=28800,
            path="/",
        )
        return {"csrf": csrf}


@app.post("/api/logout")
def logout(request: Request, response: Response, user=Depends(auth)):
    with DB() as db:
        session = db.get(Session, digest(request.cookies.get("aegis_session", "")))
        db.delete(session)
        db.commit()
    response.delete_cookie("aegis_session")
    return {"logged_out": True}


@app.get("/api/me")
def me(user=Depends(auth)):
    with DB() as db:
        memberships = db.scalars(
            select(Membership).where(Membership.user_id == user["user_id"])
        ).all()
        return {
            **user,
            "workspaces": [
                {
                    "id": m.workspace_id,
                    "role": m.role,
                    "name": db.get(Workspace, m.workspace_id).name,
                }
                for m in memberships
            ],
        }


class RoleChange(Contract):
    email: str
    role: str = Field(pattern="^(viewer|analyst|administrator)$")


@app.post("/api/workspaces/{workspace_id}/members")
def add_member(workspace_id: str, body: RoleChange, context=Depends(member)):
    if context["role"] != "administrator":
        raise HTTPException(403, "Administrator required")
    with DB() as db:
        user = db.scalar(select(User).where(User.email == body.email.lower()))
        if user is None:
            raise HTTPException(404, "User must register first")
        if user.id == context["user_id"]:
            raise HTTPException(400, "Self role changes are not allowed")
        row = db.scalar(
            select(Membership).where(
                Membership.user_id == user.id, Membership.workspace_id == workspace_id
            )
        )
        if row:
            row.role = body.role
        else:
            db.add(
                Membership(user_id=user.id, workspace_id=workspace_id, role=body.role)
            )
        save(
            db,
            workspace_id,
            "audit",
            {
                "action": "membership_changed",
                "actor": context["user_id"],
                "user_id": user.id,
                "role": body.role,
            },
        )
        db.commit()
    return {"updated": True}


@app.get("/api/workspaces/{workspace_id}/records")
def records(workspace_id: str, context=Depends(member)):
    with DB() as db:
        return [
            public_record(r)
            for r in db.scalars(
                select(Record)
                .where(Record.workspace_id == workspace_id, Record.kind != "audit")
                .order_by(Record.created_at)
            ).all()
        ]


@app.get("/api/workspaces/{workspace_id}/database")
def database_status(workspace_id: str, context=Depends(member)):
    with DB() as db:
        counts = {
            name: db.scalar(
                select(func.count())
                .select_from(table)
                .where(table.c.workspace_id == workspace_id)
            )
            for name, table in DOMAIN.items()
        }
        return {
            "engine": db.bind.dialect.name,
            "counts": counts,
            "history": "append-only",
            "schema_version": "0003",
        }


@app.get("/api/workspaces/{workspace_id}/members")
def list_members(workspace_id: str, context=Depends(member)):
    with DB() as db:
        rows = db.execute(
            select(User.email, Membership.role)
            .join(Membership, User.id == Membership.user_id)
            .where(Membership.workspace_id == workspace_id)
        ).all()
        return [{"email": email, "role": role} for email, role in rows]


@app.get("/api/workspaces/{workspace_id}/audit")
def audit_history(
    workspace_id: str, limit: int = Query(50, ge=1, le=200), context=Depends(member)
):
    if context["role"] != "administrator":
        raise HTTPException(403, "Administrator required")
    with DB() as db:
        return [
            public_record(r)
            for r in db.scalars(
                select(Record)
                .where(Record.workspace_id == workspace_id, Record.kind == "audit")
                .order_by(Record.created_at.desc())
                .limit(limit)
            ).all()
        ]


@app.get("/api/workspaces/{workspace_id}/snapshots/{snapshot_id}/elements")
def query_elements(
    workspace_id: str,
    snapshot_id: str,
    category: str = "assets",
    search: str = Query("", max_length=160),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    context=Depends(member),
):
    if category not in (
        "assets",
        "services",
        "principals",
        "permissions",
        "relationships",
        "evidence_records",
    ):
        raise HTTPException(422, "Unsupported category")
    with DB() as db:
        get_record(db, workspace_id, snapshot_id, "snapshot")
        table = DOMAIN[category]
        query = select(table.c.data).where(
            table.c.workspace_id == workspace_id, table.c.snapshot_id == snapshot_id
        )
        if search:
            query = query.where(table.c.external_id.contains(search, autoescape=True))
        return {
            "items": db.scalars(
                query.order_by(table.c.external_id).offset(offset).limit(limit)
            ).all(),
            "limit": limit,
            "offset": offset,
        }


class CsvImport(Contract):
    name: str = Field(min_length=1, max_length=160)
    csv: str = Field(min_length=1, max_length=1_900_000)


@app.post("/api/workspaces/{workspace_id}/snapshots/csv", status_code=201)
def import_csv(workspace_id: str, body: CsvImport, context=Depends(analyst)):
    try:
        inventory = parse_inventory_csv(body.name, body.csv)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return import_inventory(workspace_id, inventory, context)


@app.post("/api/workspaces/{workspace_id}/snapshots", status_code=201)
def import_inventory(workspace_id: str, body: Inventory, context=Depends(analyst)):
    with DB() as db:
        record = snapshot(db, workspace_id, body)
        save(
            db,
            workspace_id,
            "audit",
            {
                "action": "snapshot_imported",
                "record_id": record.id,
                "actor": context["user_id"],
            },
        )
        db.commit()
        return public_record(record)


@app.post(
    "/api/workspaces/{workspace_id}/snapshots/{snapshot_id}/corrections",
    status_code=201,
)
def correct_snapshot(
    workspace_id: str,
    snapshot_id: str,
    body: SnapshotCorrection,
    context=Depends(analyst),
):
    with DB() as db:
        original = get_record(db, workspace_id, snapshot_id, "snapshot")
        inventory = body.inventory.model_copy(deep=True)
        evidence = Evidence(
            id="manual-" + secrets.token_hex(12),
            source="manual:user:" + context["user_id"],
            collected_at=now(),
            confidence=body.confidence,
            method="asserted",
            note="Correction to snapshot " + snapshot_id + ": " + body.reason,
        )
        inventory.evidence.append(evidence)
        old_edges = {e["id"]: e for e in original.data["relationships"]}
        for edge in inventory.relationships:
            if edge.model_dump(mode="json") != old_edges.get(edge.id):
                edge.evidence.append(evidence.id)
        record = snapshot(db, workspace_id, inventory)
        save(
            db,
            workspace_id,
            "audit",
            {
                "action": "snapshot_corrected",
                "parent_snapshot_id": snapshot_id,
                "record_id": record.id,
                "reason": body.reason,
                "confidence": body.confidence,
                "actor": context["user_id"],
            },
        )
        db.commit()
        return public_record(record)


@app.post("/api/workspaces/{workspace_id}/seed")
def seed(workspace_id: str, context=Depends(analyst)):
    with DB() as db:
        existing = db.scalar(
            select(Record).where(
                Record.workspace_id == workspace_id, Record.kind == "catalogue"
            )
        )
        if existing:
            return {
                "seeded": False,
                "message": "Lab already seeded; no duplicates created",
            }
        inventory, scenarios, actions = lab_fixture()
        record = snapshot(db, workspace_id, inventory)
        for scenario in scenarios:
            scenario.snapshot_id = record.id
            save(db, workspace_id, "scenario", scenario.model_dump(mode="json"))
        save(
            db,
            workspace_id,
            "catalogue",
            {"actions": [a.model_dump() for a in actions]},
        )
        save(
            db,
            workspace_id,
            "audit",
            {"action": "lab_seeded", "actor": context["user_id"]},
        )
        db.commit()
    return {"seeded": True}


@app.post("/api/workspaces/{workspace_id}/scenarios", status_code=201)
def create_scenario(workspace_id: str, body: Scenario, context=Depends(analyst)):
    with DB() as db:
        inventory = Inventory.model_validate(
            get_record(db, workspace_id, body.snapshot_id, "snapshot").data
        )
        try:
            validate_scenario(body, inventory)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        record = save(db, workspace_id, "scenario", body.model_dump(mode="json"))
        save(
            db,
            workspace_id,
            "audit",
            {
                "action": "scenario_created",
                "record_id": record.id,
                "actor": context["user_id"],
            },
        )
        db.commit()
        return public_record(record)


def enqueue(workspace_id, kind, body, actor):
    with DB() as db:
        scenario = get_record(db, workspace_id, body.scenario_id, "scenario")
        inventory = get_record(
            db, workspace_id, scenario.data["snapshot_id"], "snapshot"
        )
        edges = {e["id"] for e in inventory.data["relationships"]}
        if kind in ("analysis", "evaluation") and not set(body.removed) <= edges:
            raise HTTPException(422, "Unknown relationship")
        if kind == "optimisation":
            if body.method == "exact" and len(body.actions) > 12:
                raise HTTPException(422, "Exact solver limited to 12 actions")
            if any(not set(a.remove_relationships) <= edges for a in body.actions):
                raise HTTPException(422, "Unknown action relationship")
        job = Job(
            workspace_id=workspace_id, kind=kind, payload=body.model_dump(mode="json")
        )
        db.add(job)
        db.flush()
        save(
            db,
            workspace_id,
            "audit",
            {"action": "job_queued", "job_id": job.id, "kind": kind, "actor": actor},
        )
        db.commit()
        return {"job_id": job.id, "status": job.status}


@app.post("/api/workspaces/{workspace_id}/analysis", status_code=202)
def run_analysis(workspace_id: str, body: AnalysisRequest, context=Depends(analyst)):
    return enqueue(workspace_id, "analysis", body, context["user_id"])


@app.post("/api/workspaces/{workspace_id}/plans", status_code=202)
def run_plan(workspace_id: str, body: PlanRequest, context=Depends(analyst)):
    return enqueue(workspace_id, "optimisation", body, context["user_id"])


@app.post("/api/workspaces/{workspace_id}/evaluations", status_code=202)
def run_evaluation(workspace_id: str, body: AnalysisRequest, context=Depends(analyst)):
    return enqueue(workspace_id, "evaluation", body, context["user_id"])


@app.get("/api/workspaces/{workspace_id}/jobs")
def jobs(workspace_id: str, context=Depends(member)):
    with DB() as db:
        return [
            {
                "id": j.id,
                "kind": j.kind,
                "status": j.status,
                "result_id": j.result_id,
                "error": j.error,
            }
            for j in db.scalars(
                select(Job)
                .where(Job.workspace_id == workspace_id)
                .order_by(Job.created_at.desc())
            ).all()
        ]


@app.post("/api/workspaces/{workspace_id}/jobs/{job_id}/cancel")
def cancel(workspace_id: str, job_id: str, context=Depends(analyst)):
    with DB() as db:
        job = db.get(Job, job_id)
        if job is None or job.workspace_id != workspace_id:
            raise HTTPException(404, "Job not found")
        if job.status in ("queued", "running"):
            job.status = "cancelled"
            save(
                db,
                workspace_id,
                "audit",
                {
                    "action": "job_cancelled",
                    "job_id": job.id,
                    "actor": context["user_id"],
                },
            )
            db.commit()
        return {"status": job.status}


class EventsImport(Contract):
    snapshot_id: str
    events: list[Event] = Field(max_length=5000)


@app.post("/api/workspaces/{workspace_id}/events")
def events_import(workspace_id: str, body: EventsImport, context=Depends(analyst)):
    with DB() as db:
        inventory = get_record(db, workspace_id, body.snapshot_id, "snapshot").data
        assets = {a["id"] for a in inventory["assets"]}
        principals = {a["id"] for a in inventory["assets"] if a["kind"] == "principal"}
        inserted = duplicates = 0
        for event in body.events:
            if event.asset_id not in assets or (
                event.principal_id and event.principal_id not in principals
            ):
                raise HTTPException(422, "Unknown event asset or principal")
            existing = db.scalar(
                select(EventRow).where(
                    EventRow.workspace_id == workspace_id,
                    EventRow.snapshot_id == body.snapshot_id,
                    EventRow.source == event.source,
                    EventRow.external_id == event.id,
                )
            )
            data = event.model_dump(mode="json")
            if existing:
                if existing.data != data:
                    raise HTTPException(
                        409, "Event ID collision with different content"
                    )
                duplicates += 1
            else:
                db.add(
                    EventRow(
                        workspace_id=workspace_id,
                        snapshot_id=body.snapshot_id,
                        source=event.source,
                        external_id=event.id,
                        data=data,
                    )
                )
                db.flush()
                inserted += 1
        save(
            db,
            workspace_id,
            "audit",
            {
                "action": "events_imported",
                "snapshot_id": body.snapshot_id,
                "inserted": inserted,
                "duplicates": duplicates,
                "actor": context["user_id"],
            },
        )
        db.commit()
        return {"inserted": inserted, "duplicates": duplicates}


@app.get("/api/workspaces/{workspace_id}/events")
def events(workspace_id: str, snapshot_id: str, context=Depends(member)):
    with DB() as db:
        get_record(db, workspace_id, snapshot_id, "snapshot")
        rows = db.scalars(
            select(EventRow).where(
                EventRow.workspace_id == workspace_id,
                EventRow.snapshot_id == snapshot_id,
            )
        ).all()
        return sorted(
            [{"ingested_at": r.ingested_at, "record_id": r.id, **r.data} for r in rows],
            key=lambda e: (e["source_timestamp"], e["source"], e["id"]),
        )


@app.post("/api/workspaces/{workspace_id}/lab-observations")
def import_probe(workspace_id: str, body: ProbeImport, context=Depends(analyst)):
    return events_import(
        workspace_id,
        EventsImport(snapshot_id=body.snapshot_id, events=body.observations.events()),
        context,
    )


class ReplaySave(Contract):
    snapshot_id: str
    event_key_format: Literal["record-id", "source-qualified"] = "record-id"
    event_ids: list[str] = Field(max_length=5000)
    cursor: int = Field(ge=0)


@app.post("/api/workspaces/{workspace_id}/replays")
def save_replay(workspace_id: str, body: ReplaySave, context=Depends(analyst)):
    with DB() as db:
        get_record(db, workspace_id, body.snapshot_id, "snapshot")
        # Replay stores source-qualified external IDs as displayed, validated against immutable event set.
        rows = db.scalars(
            select(EventRow).where(
                EventRow.workspace_id == workspace_id,
                EventRow.snapshot_id == body.snapshot_id,
            )
        ).all()
        known = {
            r.id
            if body.event_key_format == "record-id"
            else r.source + ":" + r.external_id
            for r in rows
        }
        if (
            not set(body.event_ids) <= known
            or len(set(body.event_ids)) != len(body.event_ids)
            or body.cursor > len(body.event_ids)
        ):
            raise HTTPException(422, "Invalid replay event or cursor")
        record = save(db, workspace_id, "replay", body.model_dump())
        save(
            db,
            workspace_id,
            "audit",
            {
                "action": "replay_saved",
                "record_id": record.id,
                "actor": context["user_id"],
            },
        )
        db.commit()
        return public_record(record)


@app.get("/api/workspaces/{workspace_id}/reports/{record_id}")
def report(
    workspace_id: str, record_id: str, format: str = "json", context=Depends(member)
):
    with DB() as db:
        record = get_record(db, workspace_id, record_id)
        if record.kind not in ("analysis", "optimisation", "evaluation"):
            raise HTTPException(400, "Select a completed run")
        content = public_record(record)
        scenario = get_record(db, workspace_id, record.data["scenario_id"], "scenario")
        snap = get_record(db, workspace_id, scenario.data["snapshot_id"], "snapshot")
        content.update(scenario=public_record(scenario), snapshot=public_record(snap))
        if format == "html":
            return HTMLResponse(
                render_report(content),
                headers={
                    "Content-Disposition": f'attachment; filename="aegistwin-{record.id}.html"'
                },
            )
        return Response(
            json.dumps(content, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="aegistwin-{record.id}.json"'
            },
        )


dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
