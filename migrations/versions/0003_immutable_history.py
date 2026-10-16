"""Enforce append-only evidence and historical records in both database engines."""

from alembic import op

revision = "0003"
down_revision = "0002"
TABLES = (
    "records",
    "snapshot_elements",
    "events",
    "inventory_snapshots",
    "assets",
    "services",
    "principals",
    "permissions",
    "relationships",
    "evidence_records",
    "scenario_definitions",
    "initial_capabilities",
    "transition_rules",
    "critical_targets",
    "defensive_actions",
    "analysis_runs",
    "optimisation_runs",
    "replay_sessions",
    "evaluation_datasets",
    "evaluation_results",
)


def upgrade():
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            "CREATE FUNCTION aegis_immutable_history() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'AegisTwin history is immutable; append a new version'; END; $$"
        )
        for table in TABLES:
            op.execute(
                f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION aegis_immutable_history()"
            )
    elif dialect == "sqlite":
        for table in TABLES:
            for operation in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER immutable_{table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'AegisTwin history is immutable; append a new version'); END"
                )
    else:
        raise RuntimeError("Only SQLite and PostgreSQL are supported")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table in TABLES:
            op.execute(f"DROP TRIGGER immutable_{table} ON {table}")
        op.execute("DROP FUNCTION aegis_immutable_history()")
    else:
        for table in TABLES:
            for operation in ("update", "delete"):
                op.execute(f"DROP TRIGGER immutable_{table}_{operation}")
