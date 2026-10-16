"""Reproducible synthetic measurements; no observations are fabricated."""

import json
import platform
import tracemalloc
from pathlib import Path
from backend.contracts import Limits, PlanRequest
from backend.fixtures import lab_fixture
from backend.engine import analyse, optimise


def main():
    inventory, scenarios, actions = lab_fixture()
    rows = []
    for scenario, truth in zip(scenarios, [True, True, False]):
        tracemalloc.start()
        analysis = analyse(inventory, scenario, Limits())
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        plans = [
            optimise(
                inventory,
                scenario,
                PlanRequest(
                    scenario_id="fixture", budget=3, actions=actions, method=method
                ),
            )
            for method in ["greedy", "exact"]
        ]
        rows.append(
            {
                "scenario": scenario.name,
                "ground_truth_reachable": truth,
                "analysis": analysis,
                "correct": analysis["targets"][0]["reachable"] == truth,
                "peak_python_bytes": peak,
                "plans": plans,
            }
        )
    result = {
        "dataset": "bundled synthetic lab v1",
        "python": platform.python_version(),
        "seed": 0,
        "measured": True,
        "rows": rows,
        "limitations": "Design assertions and synthetic ground truth only. No Docker connectivity or exploitability validation.",
    }
    Path("evaluation").mkdir(exist_ok=True)
    Path("evaluation/results.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "cases": len(rows),
                "correct": sum(r["correct"] for r in rows),
                "output": "evaluation/results.json",
            }
        )
    )


if __name__ == "__main__":
    main()
