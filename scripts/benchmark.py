"""Seeded synthetic branching sweep and permission/missing-evidence ablations."""

import json
import random
import tracemalloc
from copy import deepcopy
from pathlib import Path
from backend.contracts import Entity, Rule, Limits
from backend.fixtures import lab_fixture
from backend.engine import analyse


def main():
    rows = []
    for size in [4, 8, 12]:
        for branching in [1, 2]:
            randomizer = random.Random(17)
            inv, scenarios, _ = lab_fixture()
            scenario = scenarios[0]
            scenario.initial = ["control:seed"]
            scenario.rules = []
            for i in range(size):
                inv.assets.append(
                    Entity(
                        id=f"synthetic-{i}",
                        label=f"Synthetic node {i}",
                        kind="host",
                        segment="synthetic",
                    )
                )
                parents = (
                    ["control:seed"]
                    if i == 0
                    else [
                        f"control:n{p}"
                        for p in sorted(randomizer.sample(range(i), min(branching, i)))
                    ]
                )
                scenario.rules.append(
                    Rule(
                        id=f"r{i:02}",
                        label=f"Synthetic transition {i}",
                        requires_any=[[p] for p in parents],
                        effects=[f"control:n{i}"],
                        evidence=["lab-design"],
                        assumptions="Seeded synthetic scalability case; not collected inventory.",
                    )
                )
            scenario.targets[0].capability = f"control:n{size - 1}"
            tracemalloc.start()
            result = analyse(inv, scenario, Limits(max_states=5000))
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            rows.append(
                {
                    "size": size,
                    "branching": branching,
                    "seed": 17,
                    "peak_python_bytes": peak,
                    "result": result,
                }
            )
    inv, scenarios, _ = lab_fixture()
    scenario = scenarios[1]
    scenario.initial = ["control:web"]
    full = analyse(inv, scenario, Limits())
    topology_only = deepcopy(scenario)
    topology_only.rules[1].requires_any = [["reach:api"]]
    topology_only.rules[1].relationships = ["web-api", "api-db", "db-canary"]
    approximate = analyse(inv, topology_only, Limits())
    missing = deepcopy(inv)
    missing.evidence[0].confidence = "uncertain"
    result = {
        "dataset": "seeded synthetic only",
        "sweep": rows,
        "ablations": {
            "without_possessed_test_identity": full,
            "topology_only_ignoring_identity_and_permission": approximate,
            "missing_evidence_strict": analyse(missing, scenarios[1], Limits()),
            "missing_evidence_optimistic": analyse(
                missing, scenarios[1], Limits(evidence_policy="optimistic")
            ),
        },
        "limitations": "Topology-only deliberately removes required identity/permission modelling and is an ablation, not the production engine. Timings include Python tracemalloc overhead. Not representative real network performance.",
    }
    Path("evaluation/benchmark.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "sweep_cases": len(rows),
                "truncated": sum(r["result"]["truncated"] for r in rows),
                "output": "evaluation/benchmark.json",
            }
        )
    )


if __name__ == "__main__":
    main()
