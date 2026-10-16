"""Provision a dedicated local PostgreSQL database; never alter unrelated databases."""

import getpass
import secrets
from pathlib import Path
from urllib.parse import quote_plus
import psycopg
from psycopg import sql


def main():
    destination = Path(__file__).resolve().parent.parent / ".env.local"
    if destination.exists():
        raise SystemExit(
            ".env.local already exists; preserving it. Run python -m scripts.check_database to verify."
        )
    username = (
        input("Local PostgreSQL administrator name [postgres]: ").strip() or "postgres"
    )
    password = getpass.getpass(
        "PostgreSQL administrator password (hidden, never saved): "
    )
    role, database = "aegistwin_v2_app", "aegistwin_v2"
    app_password = secrets.token_urlsafe(32)
    with psycopg.connect(
        host="127.0.0.1",
        port=5432,
        user=username,
        password=password,
        dbname="postgres",
        autocommit=True,
        connect_timeout=5,
    ) as connection:
        if (
            connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)
            ).fetchone()
            or connection.execute(
                "SELECT 1 FROM pg_database WHERE datname=%s", (database,)
            ).fetchone()
        ):
            raise SystemExit(
                "Dedicated role/database already exists. Nothing changed; use its existing configuration."
            )
        connection.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}"
            ).format(sql.Identifier(role), sql.Literal(app_password))
        )
        try:
            connection.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(database), sql.Identifier(role)
                )
            )
        except Exception:
            connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
            raise
        connection.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(
                sql.Identifier(database)
            )
        )
    url = f"postgresql+psycopg://{role}:{quote_plus(app_password)}@127.0.0.1:5432/{database}"
    destination.write_text(
        "DATABASE_URL=" + url + "\nSECURE_COOKIES=false\n", encoding="utf-8"
    )
    print(
        "Dedicated database created. Application credentials saved only in ignored .env.local."
    )
    print("Next: .venv\\Scripts\\python.exe -m alembic upgrade head")


if __name__ == "__main__":
    main()
