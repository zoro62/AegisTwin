"""Strict mixed-row CSV inventory adapter. No URL fetching or implicit merges."""

import csv
import io
from .contracts import Inventory

COLUMNS = {
    "row_type",
    "id",
    "label",
    "kind",
    "segment",
    "critical",
    "source",
    "target",
    "evidence",
    "essential",
    "collected_at",
    "expires_at",
    "confidence",
    "method",
    "note",
}


def parse_inventory_csv(name, content):
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    if (
        not reader.fieldnames
        or len(set(reader.fieldnames)) != len(reader.fieldnames)
        or set(reader.fieldnames) - COLUMNS
    ):
        raise ValueError("CSV requires unique supported column headers")
    data = {"name": name, "assets": [], "relationships": [], "evidence": []}

    def boolean(value):
        if value not in ("", "false", "true"):
            raise ValueError("CSV boolean must be true or false")
        return value == "true"

    for index, raw in enumerate(reader, 2):
        if index > 15001:
            raise ValueError("CSV row limit exceeded")
        if None in raw or any(value is None for value in raw.values()):
            raise ValueError(f"CSV row {index}: mismatched column count")
        row = {key: value.strip() for key, value in raw.items()}
        category = row.get("row_type")
        try:
            if category == "asset":
                value = {k: row.get(k, "") for k in ("id", "label", "kind")}
                value.update(
                    segment=row.get("segment") or "lab",
                    critical=boolean(row.get("critical", "")),
                )
                data["assets"].append(value)
            elif category == "relationship":
                value = {k: row.get(k, "") for k in ("id", "source", "target", "kind")}
                value.update(
                    evidence=[
                        e.strip()
                        for e in row.get("evidence", "").split(";")
                        if e.strip()
                    ],
                    essential=boolean(row.get("essential", "")),
                )
                data["relationships"].append(value)
            elif category == "evidence":
                value = {
                    k: row.get(k, "")
                    for k in (
                        "id",
                        "source",
                        "collected_at",
                        "confidence",
                        "method",
                        "note",
                    )
                }
                value["expires_at"] = row.get("expires_at") or None
                data["evidence"].append(value)
            else:
                raise ValueError("row_type must be asset, relationship or evidence")
        except ValueError as exc:
            raise ValueError(f"CSV row {index}: {exc}") from exc
    return Inventory.model_validate(data)
