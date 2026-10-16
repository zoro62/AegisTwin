"""Dimension-separated comparison of explicit observations; absence is never a negative."""

from .contracts import Inventory, Scenario


def compare_events(
    inventory: Inventory, scenario: Scenario, analysis: dict, events: list[dict]
):
    relationships = {e.id: e for e in inventory.relationships}
    applied = set(analysis["applied_rules"])
    rows = []
    for event in events:
        fields = event["fields"]
        candidates = []
        predicted = None
        if event["event_type"] == "connectivity":
            rid = fields.get("relationship_id")
            edge = relationships.get(rid)
            if edge and edge.kind == "network":
                candidates = [rid]
                predicted = rid not in analysis["removed_relationships"]
        elif event["event_type"] == "permission":
            rid = fields.get("relationship_id")
            edge = relationships.get(rid)
            if (
                edge
                and edge.kind == "permission"
                and edge.source == event.get("principal_id")
                and edge.target == event["asset_id"]
            ):
                candidates = [rid]
                predicted = rid not in analysis["removed_relationships"]
        elif event["event_type"] == "synthetic_transition":
            rule_ids = fields.get("rule_id")
            if isinstance(rule_ids, str):
                candidates = [
                    r.id for r in scenario.rules if r.id in rule_ids.split(",")
                ]
            if len(candidates) == 1:
                predicted = candidates[0] in applied
                if analysis["truncated"] and not predicted:
                    predicted = None
        observed = fields.get("success")
        if type(observed) is not bool:
            observed = None
        comparable = predicted is not None and observed is not None
        rows.append(
            {
                "event_id": event["source"] + ":" + event["id"],
                "dimension": event["event_type"],
                "simulation": event["simulation"],
                "candidates": candidates,
                "predicted": predicted,
                "observed": observed,
                "agrees": predicted == observed if comparable else None,
                "status": "compared" if comparable else "ambiguous or unmapped",
            }
        )
    dimensions = {}
    for dimension in ["connectivity", "permission", "synthetic_transition", "canary"]:
        facts = [r for r in rows if r["dimension"] == dimension]
        dimensions[dimension] = {
            "events": len(facts),
            "compared": sum(r["agrees"] is not None for r in facts),
            "discrepancies": sum(r["agrees"] is False for r in facts),
            "real_observations": sum(not r["simulation"] for r in facts),
            "status": "observations available" if facts else "not tested",
        }
    return {
        "dimensions": dimensions,
        "comparisons": rows,
        "limitations": "Only explicitly mapped observations are compared. Ambiguity is preserved. Missing events prove nothing. Failed attempts may reflect unavailable services or instrumentation limits; TCP agreement does not validate compromise. Synthetic transitions remain separate from real observations.",
    }
