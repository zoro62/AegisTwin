import pytest
from backend.lab_observations import ProbeObservations


def observations():
    return {
        "schema_version": "1.0",
        "source": "bundled-web-probe",
        "observed_at": "2026-01-01T12:00:00Z",
        "simulation": False,
        "dimension": "connectivity",
        "limitation": "TCP only",
        "results": [
            {
                "relationship_id": rid,
                "destination": destination,
                "port": 8080,
                "success": True,
                "runtime_ms": 1.0,
            }
            for rid, destination in [
                ("web-api", "api"),
                ("web-db", "database"),
                ("web-admin", "admin"),
            ]
        ],
    }


def test_probe_import_preserves_provenance_and_rejects_arbitrary_destinations():
    data = observations()
    events = ProbeObservations.model_validate(data).events()
    assert len(events) == 3
    assert all(not e.simulation for e in events)
    assert events[1].asset_id == "db"
    assert events[0].fields["relationship_id"] == "web-api"
    data["results"][0]["destination"] = "example.com"
    with pytest.raises(ValueError):
        ProbeObservations.model_validate(data)
