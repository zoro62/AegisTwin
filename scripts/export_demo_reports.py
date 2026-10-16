"""Export actual browser-test results for review without a test-account login."""

from pathlib import Path
from sqlalchemy import select
from backend.store import DB, Record, Membership, User
from backend.reports import render_report


def envelope(record):
    return {
        "id": record.id,
        "kind": record.kind,
        "created_at": record.created_at,
        "content_hash": record.content_hash,
        "data": record.data,
    }


def main():
    with DB() as db:
        for kind, filename in [
            ("optimisation", "sample-defence-report.html"),
            ("evaluation", "sample-lab-report.html"),
        ]:
            record = db.scalar(
                select(Record)
                .join(Membership, Membership.workspace_id == Record.workspace_id)
                .join(User, User.id == Membership.user_id)
                .where(Record.kind == kind, User.email.like("browser-%@example.test"))
                .order_by(Record.created_at.desc())
                .limit(1)
            )
            if record is None:
                continue
            scenario = db.get(Record, record.data["scenario_id"])
            snapshot = db.get(Record, scenario.data["snapshot_id"])
            assert scenario.workspace_id == snapshot.workspace_id == record.workspace_id
            content = {
                **envelope(record),
                "scenario": envelope(scenario),
                "snapshot": envelope(snapshot),
            }
            path = Path("evaluation") / filename
            path.write_text(render_report(content), encoding="utf-8")
            print(str(path))


if __name__ == "__main__":
    main()
