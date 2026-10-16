"""Compare imported probe observations to explicit inventory network relationships."""

import argparse
import json
from pathlib import Path
from backend.fixtures import lab_fixture


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("observations", type=Path)
    parser.add_argument("--segmented", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=Path("evaluation/lab-comparison.json")
    )
    args = parser.parse_args()
    observed = json.loads(args.observations.read_text(encoding="utf-8-sig"))
    if (
        observed.get("dimension") != "connectivity"
        or observed.get("simulation") is not False
    ):
        raise ValueError("requires real bundled connectivity observations")
    inv, _, _ = lab_fixture()
    removed = {"web-admin", "web-db"} if args.segmented else set()
    expected = {e.id for e in inv.relationships if e.kind == "network"} - removed
    allowed = {"web-api", "web-admin", "web-db"}
    rows = []
    for fact in observed["results"]:
        if fact["relationship_id"] not in allowed or type(fact["success"]) is not bool:
            raise ValueError("unknown probe relationship or invalid success field")
        predicted = fact["relationship_id"] in expected
        rows.append(
            {**fact, "predicted": predicted, "agrees": predicted == fact["success"]}
        )
    result = {
        "dimension": "connectivity",
        "observations": observed,
        "configuration": "segmented" if args.segmented else "exposed",
        "comparisons": rows,
        "discrepancies": [r for r in rows if not r["agrees"]],
        "limitations": "Validates TCP reachability only. Denial can also result from DNS or a stopped service. Permission and attack-transition validation are separate.",
    }
    args.output.parent.mkdir(exist_ok=True, parents=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps({"checks": len(rows), "discrepancies": len(result["discrepancies"])})
    )


if __name__ == "__main__":
    main()
