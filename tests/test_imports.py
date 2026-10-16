import csv
import io
import pytest
from backend.imports import COLUMNS, parse_inventory_csv
from backend.fixtures import lab_fixture


def make_csv():
    inventory = lab_fixture()[0]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=sorted(COLUMNS))
    writer.writeheader()
    for category, items in [
        ("asset", inventory.assets),
        ("evidence", inventory.evidence),
        ("relationship", inventory.relationships),
    ]:
        for item in items:
            value = item.model_dump(mode="json")
            for key in ("critical", "essential"):
                if key in value:
                    value[key] = str(value[key]).lower()
            if "evidence" in value:
                value["evidence"] = ";".join(value["evidence"])
            writer.writerow({"row_type": category, **value})
    return stream.getvalue()


def test_csv_import_validation():
    content = make_csv()
    inventory = parse_inventory_csv("CSV fixture", content)
    assert len(inventory.assets) == 10
    assert len(inventory.relationships) == 10
    assert inventory.relationships[0].essential
    with pytest.raises(ValueError):
        parse_inventory_csv("bad", content.replace("confirmed", "invented"))
    with pytest.raises(ValueError):
        parse_inventory_csv("bad", "row_type,id,unexpected\nasset,a,x")
    with pytest.raises(ValueError):
        parse_inventory_csv("bad", content.replace("true", "yes"))
