import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine,
    String,
    Text,
    JSON,
    UniqueConstraint,
    event,
    Table,
    Column,
    ForeignKeyConstraint,
    Integer,
    Boolean,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import setting


def uid():
    return str(uuid.uuid4())


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(160), unique=True)
    password: Mapped[str] = mapped_column(Text)


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160))


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True)
    role: Mapped[str] = mapped_column(String(20))


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires: Mapped[str] = mapped_column(String(40))


class Record(Base):
    """Versioned immutable domain documents; query projections in snapshot_elements."""

    __tablename__ = "records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    schema_version: Mapped[str] = mapped_column(String(10), default="1.0")
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    content_hash: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(JSON)


class Element(Base):
    __tablename__ = "snapshot_elements"
    __table_args__ = (UniqueConstraint("snapshot_id", "category", "external_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(36), index=True)
    category: Mapped[str] = mapped_column(String(24))
    external_id: Mapped[str] = mapped_column(String(96))
    data: Mapped[dict] = mapped_column(JSON)


class EventRow(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("workspace_id", "snapshot_id", "source", "external_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(36), index=True)
    source: Mapped[str] = mapped_column(String(160))
    external_id: Mapped[str] = mapped_column(String(96))
    ingested_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    data: Mapped[dict] = mapped_column(JSON)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    payload: Mapped[dict] = mapped_column(JSON)
    result_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


# Immutable, snapshot-scoped relational projections, populated transactionally with
# the canonical record. Composite keys prevent cross-workspace references.
Record.__table__.append_constraint(
    UniqueConstraint("workspace_id", "id", name="uq_records_workspace_id")
)
for model in (Membership, Record, Element, EventRow, Job):
    model.__table__.append_constraint(
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=f"fk_{model.__tablename__}_workspace",
        )
    )
for model in (Membership, Session):
    model.__table__.append_constraint(
        ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=f"fk_{model.__tablename__}_user"
        )
    )
for model in (Element, EventRow):
    model.__table__.append_constraint(
        ForeignKeyConstraint(
            ["workspace_id", "snapshot_id"],
            ["records.workspace_id", "records.id"],
            name=f"fk_{model.__tablename__}_snapshot",
        )
    )


def domain_table(name, *columns, snapshot_scoped=False):
    common = [
        Column("workspace_id", String(36), primary_key=True),
        Column("record_id", String(36), primary_key=True),
        Column("external_id", String(160), primary_key=True),
        Column("data", JSON, nullable=False),
        ForeignKeyConstraint(
            ["workspace_id", "record_id"],
            ["records.workspace_id", "records.id"],
            name=f"fk_{name}_record",
        ),
    ]
    if snapshot_scoped:
        common.extend(
            [
                Column("snapshot_id", String(36), nullable=False),
                ForeignKeyConstraint(
                    ["workspace_id", "snapshot_id"],
                    ["records.workspace_id", "records.id"],
                    name=f"fk_{name}_snapshot",
                ),
            ]
        )
    table = Table(name, Base.metadata, *common, *columns)
    if snapshot_scoped:
        Index(f"ix_{name}_snapshot", table.c.workspace_id, table.c.snapshot_id)
    return table


DOMAIN = {
    "inventory_snapshots": domain_table(
        "inventory_snapshots", Column("name", String(160), nullable=False)
    ),
    "assets": domain_table(
        "assets",
        Column("kind", String(24), nullable=False),
        Column("label", String(160), nullable=False),
        Column("segment", String(80), nullable=False),
        Column("critical", Boolean, nullable=False),
        snapshot_scoped=True,
    ),
    "services": domain_table("services", snapshot_scoped=True),
    "principals": domain_table("principals", snapshot_scoped=True),
    "permissions": domain_table(
        "permissions",
        Column("source", String(96), nullable=False),
        Column("target", String(96), nullable=False),
        snapshot_scoped=True,
    ),
    "relationships": domain_table(
        "relationships",
        Column("source", String(96), nullable=False),
        Column("target", String(96), nullable=False),
        Column("kind", String(24), nullable=False),
        Column("essential", Boolean, nullable=False),
        snapshot_scoped=True,
    ),
    "evidence_records": domain_table(
        "evidence_records",
        Column("confidence", String(24), nullable=False),
        Column("collected_at", String(40), nullable=False),
        Column("expires_at", String(40)),
        snapshot_scoped=True,
    ),
    "scenario_definitions": domain_table(
        "scenario_definitions",
        Column("name", String(160), nullable=False),
        snapshot_scoped=True,
    ),
    "initial_capabilities": domain_table("initial_capabilities", snapshot_scoped=True),
    "transition_rules": domain_table(
        "transition_rules",
        Column("version", String(16), nullable=False),
        snapshot_scoped=True,
    ),
    "critical_targets": domain_table(
        "critical_targets",
        Column("weight", Integer, nullable=False),
        snapshot_scoped=True,
    ),
    "defensive_actions": domain_table(
        "defensive_actions", Column("cost", Integer, nullable=False)
    ),
    "analysis_runs": domain_table(
        "analysis_runs",
        Column("scenario_id", String(36), nullable=False),
        snapshot_scoped=True,
    ),
    "optimisation_runs": domain_table(
        "optimisation_runs",
        Column("scenario_id", String(36), nullable=False),
        snapshot_scoped=True,
    ),
    "replay_sessions": domain_table(
        "replay_sessions",
        Column("cursor", Integer, nullable=False),
        snapshot_scoped=True,
    ),
    "evaluation_datasets": domain_table("evaluation_datasets", snapshot_scoped=True),
    "evaluation_results": domain_table(
        "evaluation_results",
        Column("scenario_id", String(36), nullable=False),
        snapshot_scoped=True,
    ),
}
Index(
    "ix_records_workspace_kind_created",
    Record.workspace_id,
    Record.kind,
    Record.created_at,
)
Index("ix_jobs_status_created", Job.status, Job.created_at)


def project_record(db, record):
    """Append queryable projections in the same transaction as the immutable record."""
    data, kind = record.data, record.kind

    def insert(table_name, external_id, value, **fields):
        values = {
            "workspace_id": record.workspace_id,
            "record_id": record.id,
            "external_id": external_id,
            "data": value,
            **fields,
        }
        if "snapshot_id" in DOMAIN[table_name].c and "snapshot_id" not in values:
            values["snapshot_id"] = (
                record.id if kind == "snapshot" else data["snapshot_id"]
            )
        db.execute(DOMAIN[table_name].insert().values(**values))

    if kind == "snapshot":
        insert(
            "inventory_snapshots",
            record.id,
            {"schema_version": data["schema_version"]},
            name=data["name"],
        )
        for asset in data["assets"]:
            insert(
                "assets",
                asset["id"],
                asset,
                **{k: asset[k] for k in ("kind", "label", "segment", "critical")},
            )
            if asset["kind"] in ("service", "admin", "database"):
                insert("services", asset["id"], asset)
            elif asset["kind"] == "principal":
                insert("principals", asset["id"], asset)
        for edge in data["relationships"]:
            insert(
                "relationships",
                edge["id"],
                edge,
                **{k: edge[k] for k in ("source", "target", "kind", "essential")},
            )
            if edge["kind"] == "permission":
                insert(
                    "permissions",
                    edge["id"],
                    edge,
                    source=edge["source"],
                    target=edge["target"],
                )
        for evidence in data["evidence"]:
            insert(
                "evidence_records",
                evidence["id"],
                evidence,
                **{
                    k: evidence[k] for k in ("confidence", "collected_at", "expires_at")
                },
            )
    elif kind == "scenario":
        insert(
            "scenario_definitions",
            record.id,
            {"assumptions": data["assumptions"]},
            name=data["name"],
        )
        for index, capability in enumerate(data["initial"]):
            insert("initial_capabilities", str(index), {"capability": capability})
        for rule in data["rules"]:
            insert("transition_rules", rule["id"], rule, version=rule["version"])
        for index, target in enumerate(data["targets"]):
            insert("critical_targets", str(index), target, weight=target["weight"])
    elif kind == "catalogue":
        for action in data["actions"]:
            insert("defensive_actions", action["id"], action, cost=action["cost"])
    elif kind in ("analysis", "optimisation", "evaluation"):
        table = {
            "analysis": "analysis_runs",
            "optimisation": "optimisation_runs",
            "evaluation": "evaluation_results",
        }[kind]
        insert(table, record.id, data["result"], scenario_id=data["scenario_id"])
        if kind == "evaluation":
            insert(
                "evaluation_datasets", record.id, {"events": data["result"]["dataset"]}
            )
    elif kind == "replay":
        insert(
            "replay_sessions",
            record.id,
            {"event_ids": data["event_ids"]},
            cursor=data["cursor"],
        )


url = setting("DATABASE_URL", "sqlite:///./aegistwin-v2.db")
engine = create_engine(
    url,
    connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    pool_pre_ping=True,
)
if url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def sqlite_settings(connection, _):
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")


DB = sessionmaker(engine, expire_on_commit=False)


@event.listens_for(Record, "before_update")
@event.listens_for(Record, "before_delete")
def immutable(*_):
    raise ValueError("historical domain records are immutable; create a new version")
