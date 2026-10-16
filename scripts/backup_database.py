"""Consistent local backup using SQLite backup API or PostgreSQL pg_dump."""

import argparse
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.engine import make_url
from backend.config import ROOT, setting


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    url = make_url(setting("DATABASE_URL", "sqlite:///./aegistwin-v2.db"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = args.output or ROOT / "backups" / (
        "aegistwin-"
        + stamp
        + (".db" if url.drivername.startswith("sqlite") else ".dump")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise SystemExit(
            "Backup exists; choose a new output path. Nothing overwritten."
        )
    if url.drivername.startswith("sqlite"):
        source_path = Path(url.database).resolve()
        if not source_path.is_file():
            raise SystemExit("Source database does not exist")
        with (
            sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True) as source,
            sqlite3.connect(destination) as backup,
        ):
            source.backup(backup)
            if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Backup integrity verification failed")
    else:
        executable = (
            shutil.which("pg_dump") or r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
        )
        env = {**os.environ, "PGPASSWORD": url.password or ""}
        subprocess.run(
            [
                executable,
                "-h",
                url.host or "127.0.0.1",
                "-p",
                str(url.port or 5432),
                "-U",
                url.username,
                "-d",
                url.database,
                "-Fc",
                "-f",
                str(destination),
            ],
            env=env,
            check=True,
        )
    print("Backup created: " + str(destination))
    print(
        "Contains sensitive workspace data. Store securely; backups are not encrypted by this tool."
    )


if __name__ == "__main__":
    main()
