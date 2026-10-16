"""Safe connection/schema report. Never print a connection URL or password."""

import json
from sqlalchemy import inspect, text
from backend.store import engine


def main():
    with engine.connect() as connection:
        version = connection.scalar(text("SELECT version_num FROM alembic_version"))
        tables = inspect(connection).get_table_names()
        counts = {
            table: connection.scalar(
                text(
                    "SELECT count(*) FROM "
                    + engine.dialect.identifier_preparer.quote(table)
                )
            )
            for table in tables
        }
        print(
            json.dumps(
                {
                    "database": engine.dialect.name,
                    "migration": version,
                    "tables": counts,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
