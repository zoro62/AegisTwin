import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.main import app
from backend.store import Base, engine, DB, Record, Job
from backend.worker import process_one, recover


def account(email):
    client = TestClient(app)
    credentials = {"email": email, "password": "Test-password-2026!"}
    assert client.post("/api/register", json=credentials).status_code == 201
    assert client.post("/api/login", json=credentials).status_code == 200
    identity = client.get("/api/me").json()
    client.headers["x-csrf-token"] = identity["csrf"]
    return client, "/api/workspaces/" + identity["workspaces"][0]["id"]


def test_end_to_end_tenants_jobs_events_reports():
    Base.metadata.create_all(engine)
    client, base = account("analyst@example.test")
    other, _ = account("other@example.test")
    assert other.get(base + "/records").status_code == 404
    assert client.post(base + "/seed", json={}).status_code == 200
    assert not client.post(base + "/seed", json={}).json()["seeded"]
    records = client.get(base + "/records").json()
    scenario = next(r for r in records if r["kind"] == "scenario")
    snapshot = next(r for r in records if r["kind"] == "snapshot")
    status = client.get(base + "/database").json()
    assert status["counts"]["assets"] == 10
    assert status["counts"]["scenario_definitions"] == 3
    assert (
        client.get(
            base + "/snapshots/" + snapshot["id"] + "/elements?category=principals"
        ).json()["items"][0]["id"]
        == "test-user"
    )
    assert other.get(base + "/database").status_code == 404
    job = client.post(base + "/analysis", json={"scenario_id": scenario["id"]}).json()
    assert process_one()
    jobs = client.get(base + "/jobs").json()
    assert jobs[0]["status"] == "completed"
    record_id = jobs[0]["result_id"]
    report = client.get(base + "/reports/" + record_id).json()
    assert report["snapshot"]["content_hash"] == snapshot["content_hash"]
    assert report["data"]["result"]["targets"][0]["reachable"]
    html_report = client.get(base + "/reports/" + record_id + "?format=html")
    assert html_report.status_code == 200
    assert "Initial attacker assumptions" in html_report.text
    assert "Critical targets and supporting chains" in html_report.text
    assert other.get(base + "/reports/" + record_id).status_code == 404
    assert (
        client.post(
            base + "/members", json={"email": "other@example.test", "role": "viewer"}
        ).status_code
        == 200
    )
    assert other.get(base + "/records").status_code == 200
    assert other.post(base + "/seed", json={}).status_code == 403
    assert (
        client.post(
            base + "/members", json={"email": "other@example.test", "role": "analyst"}
        ).status_code
        == 200
    )
    assert (
        other.post(
            base + "/members", json={"email": "analyst@example.test", "role": "viewer"}
        ).status_code
        == 403
    )
    cancelled = client.post(
        base + "/analysis", json={"scenario_id": scenario["id"]}
    ).json()
    assert (
        client.post(base + "/jobs/" + cancelled["job_id"] + "/cancel", json={}).json()[
            "status"
        ]
        == "cancelled"
    )
    with DB() as db:
        row = db.get(Job, job["job_id"])
        row.status = "running"
        db.commit()
    recover()
    assert process_one()
    event = {
        "id": "e1",
        "source": "test",
        "source_timestamp": "2026-01-01T00:00:00Z",
        "asset_id": "api",
        "event_type": "connectivity",
        "fields": {"success": True},
        "simulation": True,
        "provenance": "synthetic test",
    }
    payload = {"snapshot_id": snapshot["id"], "events": [event, event]}
    assert client.post(base + "/events", json=payload).json() == {
        "inserted": 1,
        "duplicates": 1,
    }
    event2 = {**event, "id": "e0", "source_timestamp": "2025-01-01T00:00:00Z"}
    assert (
        client.post(
            base + "/events", json={"snapshot_id": snapshot["id"], "events": [event2]}
        ).status_code
        == 200
    )
    assert (
        client.get(base + "/events?snapshot_id=" + snapshot["id"]).json()[0]["id"]
        == "e0"
    )
    offset = {**event, "id": "offset", "source_timestamp": "2026-01-01T01:00:00+05:30"}
    assert (
        client.post(
            base + "/events", json={"snapshot_id": snapshot["id"], "events": [offset]}
        ).status_code
        == 200
    )
    assert (
        client.get(base + "/events?snapshot_id=" + snapshot["id"]).json()[1]["id"]
        == "offset"
    )
    assert (
        client.get(base + "/events?snapshot_id=" + snapshot["id"]).json()
        == client.get(base + "/events?snapshot_id=" + snapshot["id"]).json()
    )
    evaluation = client.post(
        base + "/evaluations", json={"scenario_id": scenario["id"]}
    ).json()
    assert "job_id" in evaluation
    assert process_one()
    ev_job = next(
        j for j in client.get(base + "/jobs").json() if j["id"] == evaluation["job_id"]
    )
    ev_report = client.get(base + "/reports/" + ev_job["result_id"]).json()
    assert len(ev_report["data"]["result"]["dataset"]) == 3
    event["fields"] = {"success": False}
    assert client.post(base + "/events", json=payload).status_code == 409
    saved_csrf = client.headers.pop("x-csrf-token")
    assert client.post(base + "/seed", json={}).status_code == 403
    client.headers["x-csrf-token"] = saved_csrf
    assert (
        client.post(
            base + "/snapshots", json={"url": "http://169.254.169.254"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            base + "/seed", json={}, headers={"origin": "https://evil.test"}
        ).status_code
        == 403
    )
    with DB() as db:
        record = db.scalar(select(Record).where(Record.id == snapshot["id"]))
        record.data = {"rewritten": True}
        try:
            db.commit()
            assert False, "immutable snapshot updated"
        except ValueError:
            db.rollback()


def test_manual_correction_keeps_original_snapshot_and_provenance():
    Base.metadata.create_all(engine)
    client, base = account("correction@example.test")
    assert client.post(base + "/seed", json={}).status_code == 200
    original = next(
        r for r in client.get(base + "/records").json() if r["kind"] == "snapshot"
    )
    from copy import deepcopy

    changed = deepcopy(original["data"])
    changed["relationships"][0]["essential"] = False
    response = client.post(
        base + "/snapshots/" + original["id"] + "/corrections",
        json={
            "inventory": changed,
            "reason": "Correct required-service metadata after lab review.",
        },
    )
    assert response.status_code == 201
    new = response.json()
    assert new["id"] != original["id"]
    evidence = new["data"]["evidence"][-1]
    assert evidence["method"] == "asserted" and evidence["confidence"] == "uncertain"
    assert evidence["id"] in new["data"]["relationships"][0]["evidence"]
    stored_original = next(
        r for r in client.get(base + "/records").json() if r["id"] == original["id"]
    )
    assert stored_original == original
