"""Deterministic bounded monotonic state exploration, not a breach probability model."""

from collections import deque
from itertools import combinations
from time import perf_counter
import networkx as nx
from .contracts import Inventory, Scenario, Limits, PlanRequest, now

ENGINE_VERSION = "aegis-monotonic-1.0"


def analyse(inventory: Inventory, scenario: Scenario, limits: Limits, removed=()):
    started = perf_counter()
    removed = set(removed)
    edges = {e.id: e for e in inventory.relationships if e.id not in removed}
    evidence = {e.id: e for e in inventory.evidence}
    reference_time = limits.evidence_at or now()

    def accepted(eid):
        e = evidence[eid]
        if e.collected_at > reference_time:
            return limits.evidence_policy == "optimistic"
        if e.expires_at and e.expires_at <= reference_time:
            return limits.evidence_policy == "optimistic"
        return e.confidence == "confirmed" or limits.evidence_policy == "optimistic"

    environmental = {}
    for r in scenario.rules:
        missing = sorted(set(r.relationships) - edges.keys())
        ev = set(r.evidence)
        for edge in r.relationships:
            if edge in edges:
                ev.update(edges[edge].evidence)
        rejected = sorted(e for e in ev if not accepted(e))
        environmental[r.id] = {
            "removed_relationships": missing,
            "unaccepted_evidence": rejected,
        }
    initial = frozenset(scenario.initial)
    queue = deque([(initial, [])])
    visited = {initial}
    reached = set(initial)
    witnesses = {
        t.capability: ([[]] if t.capability in initial else [])
        for t in scenario.targets
    }
    applied = set()
    truncation = set()
    max_depth_seen = 0
    while queue:
        if (perf_counter() - started) * 1000 >= limits.time_ms:
            truncation.add("time budget")
            break
        state, chain = queue.popleft()
        max_depth_seen = max(max_depth_seen, len(chain))
        for rule in sorted(scenario.rules, key=lambda r: r.id):
            env = environmental[rule.id]
            if env["removed_relationships"] or env["unaccepted_evidence"]:
                continue
            if not any(set(clause) <= state for clause in rule.requires_any):
                continue
            new_state = state | frozenset(rule.effects)
            if new_state == state:
                continue
            if len(chain) >= limits.max_depth:
                truncation.add("path depth")
                continue
            next_chain = chain + [rule.id]
            # Do not report unqueued states as exhaustively explored.
            if new_state not in visited and len(visited) >= limits.max_states:
                truncation.add("state limit")
                continue
            applied.add(rule.id)
            reached.update(new_state)
            for target in scenario.targets:
                paths = witnesses[target.capability]
                if (
                    target.capability in new_state
                    and target.capability not in state
                    and len(paths) < limits.top_k
                    and next_chain not in paths
                ):
                    paths.append(next_chain)
            if new_state not in visited:
                visited.add(new_state)
                queue.append((new_state, next_chain))
    blocked = []
    for r in scenario.rules:
        if r.id not in applied:
            blocked.append(
                {
                    "rule_id": r.id,
                    **environmental[r.id],
                    "missing_capabilities_any": [
                        sorted(set(c) - reached) for c in r.requires_any
                    ],
                    "note": "Not fired within configured search; union of reached capabilities is diagnostic only.",
                }
            )
    return {
        "engine_version": ENGINE_VERSION,
        "rule_versions": {r.id: r.version for r in scenario.rules},
        "evidence_evaluated_at": reference_time.isoformat(),
        "limits": limits.model_dump(mode="json"),
        "removed_relationships": sorted(removed),
        "reachable_capabilities": sorted(reached),
        "targets": [
            {
                "asset_id": t.asset_id,
                "capability": t.capability,
                "weight": t.weight,
                "reachable": t.capability in reached,
                "chains": witnesses[t.capability],
            }
            for t in scenario.targets
        ],
        "blocked": blocked,
        "applied_rules": sorted(applied),
        "states_explored": len(visited),
        "depth": max_depth_seen,
        "truncated": bool(truncation),
        "warnings": sorted(truncation),
        "runtime_ms": round((perf_counter() - started) * 1000, 3),
        "assumptions": scenario.assumptions,
        "limitations": "Monotonic capabilities; finite imported rules only. Chains are bounded witnesses, not all paths. Reachability is not exploitability or breach probability.",
    }


def essential_connectivity(inventory, removed):
    graph = nx.DiGraph()
    graph.add_nodes_from(a.id for a in inventory.assets)
    graph.add_edges_from(
        (e.source, e.target)
        for e in inventory.relationships
        if e.kind == "network" and e.id not in removed
    )
    return [
        {"relationship": e.id, "preserved": nx.has_path(graph, e.source, e.target)}
        for e in inventory.relationships
        if e.kind == "network" and e.essential
    ]


def optimise(
    inventory: Inventory,
    scenario: Scenario,
    request: PlanRequest,
    cancelled=lambda: False,
):
    started = perf_counter()
    frozen_limits = request.limits.model_copy(
        update={"evidence_at": request.limits.evidence_at or now()}
    )
    baseline = analyse(inventory, scenario, frozen_limits)
    actions = sorted(request.actions, key=lambda a: a.id)
    if request.method == "exact" and len(actions) > 12:
        raise ValueError("exact search supports at most 12 actions; use greedy")
    edge_ids = {e.id for e in inventory.relationships}
    if any(not set(a.remove_relationships) <= edge_ids for a in actions):
        raise ValueError("action references unknown relationship")
    evaluated = 0
    interrupted = False
    any_truncated = baseline["truncated"]

    def evaluate(chosen):
        nonlocal evaluated, any_truncated
        ids = {a.id for a in chosen}
        cost = sum(a.cost for a in chosen)
        if cost > request.budget or any(ids.intersection(a.conflicts) for a in chosen):
            return None
        removed = {e for a in chosen for e in a.remove_relationships}
        connectivity = essential_connectivity(inventory, removed)
        if any(not c["preserved"] for c in connectivity):
            return None
        result = analyse(inventory, scenario, frozen_limits, removed)
        any_truncated |= result["truncated"]
        evaluated += 1
        # A truncated search cannot certify that an unobserved target is unreachable.
        score = (
            sum(
                t["weight"]
                for t, b in zip(result["targets"], baseline["targets"])
                if b["reachable"] and not t["reachable"]
            )
            if not result["truncated"]
            else 0
        )
        return {
            "selected_actions": [a.model_dump() for a in chosen],
            "cost": cost,
            "weighted_targets_blocked": score,
            "after": result,
            "connectivity": connectivity,
        }

    best = evaluate([])

    def key(value):
        return (
            value["weighted_targets_blocked"],
            -value["cost"],
            -len(value["selected_actions"]),
        )

    if request.method == "exact":
        candidates = (
            c for n in range(1, len(actions) + 1) for c in combinations(actions, n)
        )
        for chosen in candidates:
            if cancelled() or perf_counter() - started > 15:
                interrupted = True
                break
            value = evaluate(chosen)
            if value and key(value) > key(best):
                best = value
    else:
        chosen = []
        while True:
            candidates = []
            for a in actions:
                if cancelled() or perf_counter() - started > 15:
                    interrupted = True
                    break
                if a not in chosen:
                    value = evaluate(chosen + [a])
                    if (
                        value
                        and value["weighted_targets_blocked"]
                        > best["weighted_targets_blocked"]
                    ):
                        gain = (
                            value["weighted_targets_blocked"]
                            - best["weighted_targets_blocked"]
                        )
                        candidates.append((gain / max(1, a.cost), a.id, a, value))
            if interrupted or not candidates:
                break
            _, _, action, value = max(candidates, key=lambda c: (c[0], c[1]))
            chosen.append(action)
            best = value
    best.update(
        {
            "before": baseline,
            "budget": request.budget,
            "method": request.method,
            "evaluated_subsets": evaluated,
            "runtime_ms": round((perf_counter() - started) * 1000, 3),
            "optimality": "optimal for supplied catalogue and objective"
            if request.method == "exact" and not interrupted and not any_truncated
            else "bounded / no optimality certificate",
            "warnings": [
                "Search interrupted or analysis truncated; unreachable targets may be unconfirmed."
            ]
            if interrupted or any_truncated
            else [],
            "objective": "Maximise newly unreachable weighted critical targets, then minimise cost and action count. Preserve essential network connectivity.",
        }
    )
    return best
