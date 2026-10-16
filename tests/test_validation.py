from backend.validation import compare_events
from backend.fixtures import lab_fixture
from backend.engine import analyse
from backend.contracts import Limits


def test_dimensions_ambiguity_and_absence():
    inventory, scenarios, _ = lab_fixture()
    analysis = analyse(inventory, scenarios[0], Limits())
    empty = compare_events(inventory, scenarios[0], analysis, [])
    assert all(d["status"] == "not tested" for d in empty["dimensions"].values())
    common = {
        "source": "test",
        "id": "e1",
        "simulation": True,
        "asset_id": "admin",
        "event_type": "connectivity",
        "fields": {"relationship_id": "web-admin", "success": True},
    }
    result = compare_events(inventory, scenarios[0], analysis, [common])
    assert result["comparisons"][0]["agrees"]
    assert result["dimensions"]["connectivity"]["real_observations"] == 0
    ambiguous = {
        **common,
        "event_type": "synthetic_transition",
        "fields": {"rule_id": "reach-admin,read-via-admin", "success": True},
    }
    result = compare_events(inventory, scenarios[0], analysis, [ambiguous])
    assert result["comparisons"][0]["agrees"] is None
    assert len(result["comparisons"][0]["candidates"]) == 2
    wrong_identity = {
        **common,
        "event_type": "permission",
        "asset_id": "canary",
        "principal_id": "wrong",
        "fields": {"relationship_id": "user-read", "success": True},
    }
    assert (
        compare_events(inventory, scenarios[0], analysis, [wrong_identity])[
            "comparisons"
        ][0]["agrees"]
        is None
    )
