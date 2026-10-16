"""Migrate and exercise real database constraints, not only ORM metadata."""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text, inspect, event
from sqlalchemy.exc import IntegrityError, DatabaseError


def test_migrations_backfill_foreign_keys_and_sql_immutability(tmp_path):
    url = os.environ.get(
        "TEST_DATABASE_URL", "sqlite:///" + str(tmp_path / "migrated.db")
    )
    env = {**os.environ, "DATABASE_URL": url}
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    # A dedicated test database is required; never clear an existing database.
    assert not inspect(engine).has_table("alembic_version"), (
        "TEST_DATABASE_URL must point to a fresh disposable database"
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "0001"],
        env=env,
        check=True,
        capture_output=True,
    )
    workspace, record = str(uuid.uuid4()), str(uuid.uuid4())
    from backend.fixtures import lab_fixture

    inventory = lab_fixture()[0].model_dump(mode="json")
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO workspaces (id,name) VALUES (:id,:name)"),
            {"id": workspace, "name": "Migration preservation test"},
        )
        connection.execute(
            text(
                "INSERT INTO records (id,workspace_id,kind,schema_version,created_at,content_hash,data) VALUES (:id,:workspace,:kind,:version,:created,:hash,:data)"
            ),
            {
                "id": record,
                "workspace": workspace,
                "kind": "snapshot",
                "version": "1.0",
                "created": "2026-01-01T00:00:00+00:00",
                "hash": "0" * 64,
                "data": json.dumps(inventory),
            },
        )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env,
        check=True,
        capture_output=True,
    )
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM assets")) == 10
        assert connection.scalar(text("SELECT count(*) FROM permissions")) == 2
        assert connection.scalar(text("SELECT count(*) FROM principals")) == 1
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
        )
    with pytest.raises(DatabaseError):
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE records SET content_hash='rewritten' WHERE id=:id"),
                {"id": record},
            )
    with pytest.raises(DatabaseError):
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM assets WHERE record_id=:id"), {"id": record}
            )
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO services (workspace_id,record_id,external_id,data,snapshot_id) VALUES (:workspace,:record,:external,:data,:snapshot)"
                ),
                {
                    "workspace": str(uuid.uuid4()),
                    "record": record,
                    "external": "forbidden",
                    "data": "{}",
                    "snapshot": record,
                },
            )
    engine.dispose()


def test_migration_files_are_frozen():
    for path in Path("migrations/versions").glob("*.py"):
        assert "from backend.store" not in path.read_text(encoding="utf-8")
