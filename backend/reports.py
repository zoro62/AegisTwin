"""Readable, fully escaped reports backed only by immutable saved inputs."""

import html
import json


def render_report(content):
    def escape(value):
        return html.escape(str(value), quote=True)

    def table(headers, rows):
        return (
            "<table><thead><tr>"
            + "".join("<th>" + escape(h) + "</th>" for h in headers)
            + "</tr></thead><tbody>"
            + "".join(
                "<tr>" + "".join("<td>" + escape(c) + "</td>" for c in row) + "</tr>"
                for row in rows
            )
            + "</tbody></table>"
        )

    data = content["data"]
    scenario = content["scenario"]["data"]
    inventory = content["snapshot"]["data"]
    result = data["result"]
    analysis = result.get("after", result.get("analysis", result))
    sections = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>AegisTwin evidence report</title><style>body{font:15px/1.6 system-ui;margin:40px auto;max-width:1050px;padding:0 25px;color:#182b36}h1,h2{color:#174e4c}table{border-collapse:collapse;width:100%;margin:18px 0}th,td{border:1px solid #ccd5d9;padding:10px;text-align:left;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px}small{color:#52636d}@media print{details{display:block}body{margin:0}}</style></head><body><h1>AegisTwin evidence report</h1><p>Finite evidence-backed simulation. Reachability does not establish exploitability or breach probability.</p>'
    ]
    sections.append(
        table(
            ["Run", "Snapshot", "Scenario"],
            [[content["id"], content["snapshot"]["id"], content["scenario"]["id"]]],
        )
    )
    sections.append(
        "<p>Snapshot SHA-256: "
        + escape(content["snapshot"]["content_hash"])
        + "</p><h2>Initial attacker assumptions</h2><p>"
        + escape(scenario["assumptions"])
        + "</p>"
    )
    sections.append(table(["Initial capabilities"], [[c] for c in scenario["initial"]]))
    sections.append("<h2>Critical targets and supporting chains</h2>")
    sections.append(
        table(
            ["Asset", "Capability", "Reached", "Bounded witness chains"],
            [
                [
                    t["asset_id"],
                    t.get("capability", ""),
                    t["reachable"],
                    "; ".join(
                        " → ".join(c) or "Initial capability" for c in t["chains"]
                    ),
                ]
                for t in analysis["targets"]
            ],
        )
    )
    rules = {r["id"]: r for r in scenario["rules"]}
    used = sorted(
        {rid for t in analysis["targets"] for chain in t["chains"] for rid in chain}
    )
    sections.append(
        table(
            [
                "Transition / version",
                "AND/OR prerequisites",
                "Required relationships",
                "Evidence / assumptions",
            ],
            [
                [
                    rid + " / " + rules[rid]["version"],
                    " OR ".join(" AND ".join(c) for c in rules[rid]["requires_any"]),
                    ", ".join(rules[rid]["relationships"]),
                    ", ".join(rules[rid]["evidence"])
                    + " — "
                    + rules[rid]["assumptions"],
                ]
                for rid in used
            ],
        )
    )
    if "before" in result:
        sections.append("<h2>Defensive plan and before/after comparison</h2>")
        sections.append(
            table(
                ["Budget", "Selected cost", "Method", "Optimality"],
                [
                    [
                        result["budget"],
                        result["cost"],
                        result["method"],
                        result["optimality"],
                    ]
                ],
            )
        )
        sections.append(
            table(
                [
                    "Action",
                    "Removed prerequisites",
                    "Cost basis",
                    "Cost",
                    "Service impact",
                    "Rollback",
                ],
                [
                    [
                        a["label"],
                        ", ".join(a["remove_relationships"]),
                        a["cost_basis"],
                        a["cost"],
                        a["impact"],
                        a["rollback"],
                    ]
                    for a in result["selected_actions"]
                ],
            )
        )
        sections.append(
            table(
                ["Target", "Before reachable", "After reachable"],
                [
                    [a["asset_id"], b["reachable"], a["reachable"]]
                    for b, a in zip(
                        result["before"]["targets"], result["after"]["targets"]
                    )
                ],
            )
        )
        sections.append(
            table(
                ["Required connectivity", "Preserved"],
                [[c["relationship"], c["preserved"]] for c in result["connectivity"]],
            )
        )
    if "validation" in result:
        sections.append(
            "<h2>Validation dimensions</h2>"
            + table(
                [
                    "Dimension",
                    "Events",
                    "Compared",
                    "Discrepancies",
                    "Real observations",
                    "Status",
                ],
                [
                    [
                        name,
                        d["events"],
                        d["compared"],
                        d["discrepancies"],
                        d["real_observations"],
                        d["status"],
                    ]
                    for name, d in result["validation"]["dimensions"].items()
                ],
            )
        )
        sections.append("<p>" + escape(result["validation"]["limitations"]) + "</p>")
    sections.append(
        "<h2>Evidence and uncertainty</h2>"
        + table(
            [
                "Evidence",
                "Source / method",
                "Confidence",
                "Collected / expires",
                "Note",
            ],
            [
                [
                    e["id"],
                    e["source"] + " / " + e["method"],
                    e["confidence"],
                    e["collected_at"] + " / " + str(e["expires_at"]),
                    e["note"],
                ]
                for e in inventory["evidence"]
            ],
        )
    )
    sections.append(
        "<h2>Search bounds and limitations</h2><pre>"
        + escape(
            json.dumps(
                {
                    "engine": analysis["engine_version"],
                    "limits": analysis["limits"],
                    "states_explored": analysis["states_explored"],
                    "runtime_ms": analysis["runtime_ms"],
                    "truncated": analysis["truncated"],
                    "warnings": analysis["warnings"],
                    "limitations": analysis["limitations"],
                },
                indent=2,
            )
        )
        + "</pre>"
    )
    sections.append(
        "<details><summary>Complete reproducible input and result appendix</summary><pre>"
        + escape(json.dumps(content, indent=2))
        + "</pre></details></body></html>"
    )
    return "".join(sections)
