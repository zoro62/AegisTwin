from copy import deepcopy
from datetime import timedelta
import pytest
from backend.contracts import Limits, PlanRequest, Inventory, now, validate_scenario
from backend.fixtures import lab_fixture
from backend.engine import analyse, optimise


def test_three_ground_truth_scenarios():
    inv, scenarios, _ = lab_fixture()
    for scenario, expected in zip(scenarios, [True, True, False]):
        validate_scenario(scenario, inv)
        result = analyse(inv, scenario, Limits())
        assert result["targets"][0]["reachable"] == expected
        assert not result["truncated"]


def test_and_or_and_cycles():
    inv, scenarios, _ = lab_fixture()
    scenario = scenarios[1]
    scenario.initial = ["control:web"]
    assert not analyse(inv, scenario, Limits())["targets"][0]["reachable"]
    scenario.rules[1].requires_any.append(["reach:api", "identity:alternate"])
    scenario.initial.append("identity:alternate")
    assert analyse(inv, scenario, Limits())["targets"][0]["reachable"]
    cycle = deepcopy(scenario.rules[0])
    cycle.id = "cycle"
    cycle.requires_any = [["reach:api"]]
    cycle.effects = ["control:web"]
    scenario.rules.append(cycle)
    assert analyse(inv, scenario, Limits())["states_explored"] < 30


def test_evidence_policy_and_staleness():
    inv, scenarios, _ = lab_fixture()
    for status in ["conflicting", "uncertain", "candidate"]:
        inv.evidence[0].confidence = status
        assert not analyse(inv, scenarios[0], Limits())["targets"][0]["reachable"]
        assert analyse(inv, scenarios[0], Limits(evidence_policy="optimistic"))[
            "targets"
        ][0]["reachable"]
    inv.evidence[0].confidence = "confirmed"
    inv.evidence[0].expires_at = now() - timedelta(days=1)
    assert not analyse(inv, scenarios[0], Limits())["targets"][0]["reachable"]


def test_truncation_determinism_and_immutability():
    inv, scenarios, _ = lab_fixture()
    original = inv.model_dump_json()
    results = [analyse(inv, scenarios[0], Limits()) for _ in range(2)]
    for r in results:
        r.pop("runtime_ms")
        r.pop("evidence_evaluated_at")
    assert results[0] == results[1]
    assert analyse(inv, scenarios[0], Limits(max_states=1))["truncated"]
    assert analyse(inv, scenarios[0], Limits(max_depth=1))["truncated"]
    analyse(inv, scenarios[0], Limits(), ["web-admin"])
    assert inv.model_dump_json() == original


def test_defence_budget_constraints_and_conflicts():
    inv, scenarios, actions = lab_fixture()
    request = PlanRequest(scenario_id="test", budget=2, actions=actions)
    result = optimise(inv, scenarios[0], request)
    assert result["cost"] == 2
    assert result["selected_actions"][0]["id"] == "close-admin"
    assert not result["after"]["targets"][0]["reachable"]
    assert all(c["preserved"] for c in result["connectivity"])
    request.budget = 0
    assert not optimise(inv, scenarios[0], request)["selected_actions"]
    request.budget = 5
    actions[0].conflicts = ["least-privilege"]
    scenarios[0].initial.append("identity:test-user")
    assert optimise(inv, scenarios[0], request)["after"]["targets"][0]["reachable"]


def test_invalid_imports():
    inv, _, _ = lab_fixture()
    data = inv.model_dump()
    data["assets"].append(data["assets"][0])
    with pytest.raises(ValueError):
        Inventory.model_validate(data)


def test_reproducible_evidence_time_and_pinned_plan_comparison():
    inv, scenarios, actions = lab_fixture()
    instant = now()
    inv.evidence[0].collected_at = instant - timedelta(days=2)
    inv.evidence[0].expires_at = instant - timedelta(days=1)
    past = Limits(evidence_at=instant - timedelta(days=1, hours=12))
    assert analyse(inv, scenarios[0], past)["targets"][0]["reachable"]
    assert not analyse(inv, scenarios[0], Limits(evidence_at=instant))["targets"][0][
        "reachable"
    ]
    plan = optimise(
        inv, scenarios[0], PlanRequest(scenario_id="test", actions=actions, limits=past)
    )
    assert (
        plan["before"]["evidence_evaluated_at"]
        == plan["after"]["evidence_evaluated_at"]
    )
    data = inv.model_dump()
    data["relationships"][0]["target"] = "unknown"
    with pytest.raises(ValueError):
        Inventory.model_validate(data)
