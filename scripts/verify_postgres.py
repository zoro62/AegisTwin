"""Exercise PostgreSQL guards in rolled-back transactions; never retain test rows."""

import json
import uuid
from sqlalchemy import select, text
from sqlalchemy.exc import DatabaseError, IntegrityError
from backend.store import engine, Workspace, Record, DOMAIN


def main():
    if engine.dialect.name != "postgresql":
        raise SystemExit(
            "This verification requires the configured PostgreSQL database"
        )
    with engine.connect() as connection:
        role = connection.execute(
            text(
                "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user"
            )
        ).one()
        assert not any(role), "Application role must not have administrative role flags"
        connection.rollback()
        transaction = connection.begin()
        try:
            workspace, record = str(uuid.uuid4()), str(uuid.uuid4())
            connection.execute(
                Workspace.__table__.insert().values(
                    id=workspace, name="Rolled-back verification"
                )
            )
            connection.execute(
                Record.__table__.insert().values(
                    id=record,
                    workspace_id=workspace,
                    kind="audit",
                    schema_version="1.0",
                    content_hash="0" * 64,
                    data={"verification": True},
                )
            )
            history_blocked = False
            try:
                with connection.begin_nested():
                    connection.execute(
                        Record.__table__.update()
                        .where(Record.id == record)
                        .values(content_hash="1" * 64)
                    )
            except DatabaseError:
                history_blocked = True
            assert history_blocked, "PostgreSQL history update was not blocked"
            tenant_blocked = False
            try:
                with connection.begin_nested():
                    connection.execute(
                        DOMAIN["services"]
                        .insert()
                        .values(
                            workspace_id=str(uuid.uuid4()),
                            record_id=record,
                            external_id="forbidden",
                            snapshot_id=record,
                            data={},
                        )
                    )
            except IntegrityError:
                tenant_blocked = True
            assert tenant_blocked, "Cross-workspace projection was not blocked"
            assert (
                connection.scalar(
                    select(Record.content_hash).where(Record.id == record)
                )
                == "0" * 64
            )
        finally:
            transaction.rollback()
        assert (
            connection.scalar(select(Workspace.id).where(Workspace.id == workspace))
            is None
        )
    result = {
        "database": "postgresql",
        "restricted_application_role": True,
        "direct_history_update_rejected": history_blocked,
        "cross_workspace_foreign_key_rejected": tenant_blocked,
        "verification_rows_rolled_back": True,
    }
    from pathlib import Path

    Path("evaluation/postgres-verification.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
