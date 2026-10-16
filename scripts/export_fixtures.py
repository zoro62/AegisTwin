"""Export canonical import examples; no installation-specific IDs or credentials."""

import json
from pathlib import Path
from backend.fixtures import lab_fixture

inventory, scenarios, actions = lab_fixture()
destination = Path("fixtures")
destination.mkdir(exist_ok=True)
for filename, data in [
    ("inventory.json", inventory.model_dump(mode="json")),
    ("scenarios.json", [s.model_dump(mode="json") for s in scenarios]),
    ("actions.json", [a.model_dump(mode="json") for a in actions]),
]:
    (destination / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")
