from datetime import datetime, timezone, timedelta
from .contracts import Inventory, Scenario, Action


def lab_fixture():
    timestamp = datetime.now(timezone.utc)
    evidence = {
        "id": "lab-design",
        "source": "bundled-lab-v2",
        "collected_at": timestamp.isoformat(),
        "expires_at": (timestamp + timedelta(days=30)).isoformat(),
        "confidence": "confirmed",
        "method": "asserted",
        "note": "Synthetic lab design assertion, not a successful connectivity probe or exploit.",
    }
    specs = [
        ("proxy", "Reverse proxy", "service", "edge"),
        ("web", "Public demo app", "service", "edge"),
        ("api", "Internal API", "service", "internal"),
        ("db", "Synthetic database", "database", "data"),
        ("admin", "Administration", "admin", "management"),
        ("test-user", "Test application identity", "principal", "identity"),
        ("canary", "Canary records", "resource", "data"),
        ("collector", "Telemetry collector", "service", "internal"),
        ("edge", "Edge segment", "segment", "edge"),
        ("internal", "Internal segment", "segment", "internal"),
    ]
    edges = [
        ("proxy-web", "proxy", "web", "network", True),
        ("web-api", "web", "api", "network", True),
        ("api-db", "api", "db", "network", True),
        ("web-admin", "web", "admin", "network", False),
        ("web-db", "web", "db", "network", False),
        ("user-auth", "test-user", "api", "authentication", False),
        ("user-read", "test-user", "canary", "permission", False),
        ("admin-data", "admin", "canary", "permission", False),
        ("db-canary", "db", "canary", "dependency", False),
        ("api-collector", "api", "collector", "communication", False),
    ]
    inventory = Inventory.model_validate(
        {
            "name": "AegisTwin isolated lab v2",
            "assets": [
                {
                    "id": i,
                    "label": label,
                    "kind": kind,
                    "segment": segment,
                    "critical": i == "canary",
                }
                for i, label, kind, segment in specs
            ],
            "evidence": [evidence],
            "relationships": [
                {
                    "id": i,
                    "source": s,
                    "target": t,
                    "kind": k,
                    "essential": required,
                    "evidence": ["lab-design"],
                }
                for i, s, t, k, required in edges
            ],
        }
    )
    rules = [
        {
            "id": "reach-api",
            "label": "Reach internal API",
            "requires_any": [["control:web"]],
            "relationships": ["web-api"],
            "effects": ["reach:api"],
        },
        {
            "id": "read-via-api",
            "label": "Read canary with overbroad test identity",
            "requires_any": [["reach:api", "identity:test-user"]],
            "relationships": ["user-auth", "user-read", "api-db", "db-canary"],
            "effects": ["read:canary"],
        },
        {
            "id": "reach-admin",
            "label": "Reach exposed admin interface",
            "requires_any": [["control:web"]],
            "relationships": ["web-admin"],
            "effects": ["reach:admin"],
        },
        {
            "id": "read-via-admin",
            "label": "Synthetic admin session accesses canary",
            "requires_any": [["reach:admin", "session:admin"]],
            "relationships": ["admin-data"],
            "effects": ["read:canary"],
        },
        {
            "id": "direct-db",
            "label": "Reach overly exposed database",
            "requires_any": [["control:web"]],
            "relationships": ["web-db"],
            "effects": ["reach:db"],
        },
    ]
    for rule in rules:
        rule.update(
            evidence=["lab-design"],
            assumptions="Initial compromise and test identity/session are explicit simulated assumptions. No vulnerability or exploit is inferred.",
        )
    scenarios = []
    for name, caps in [
        ("Excessive network exposure", ["control:web", "session:admin"]),
        ("Overbroad access permission", ["control:web", "identity:test-user"]),
        ("Segmentation blocks access", ["control:proxy", "identity:test-user"]),
    ]:
        scenarios.append(
            Scenario.model_validate(
                {
                    "name": name,
                    "snapshot_id": "pending",
                    "initial": caps,
                    "assumptions": "Authorised synthetic scenario. Compromise of the initial asset and possession of named test capabilities are assumed, not observed.",
                    "targets": [
                        {"asset_id": "canary", "capability": "read:canary", "weight": 5}
                    ],
                    "rules": rules,
                }
            )
        )
    actions = [
        Action(
            id="close-admin",
            label="Remove public app → admin exposure",
            remove_relationships=["web-admin"],
            cost=2,
            impact="Public application cannot reach administration. Required app/API/database flow remains.",
            rollback="Restore web-admin in a new snapshot.",
        ),
        Action(
            id="least-privilege",
            label="Remove excessive canary read permission",
            remove_relationships=["user-read"],
            cost=1,
            impact="Test identity loses canary read; application network paths remain.",
            rollback="Restore user-read in a new snapshot.",
        ),
        Action(
            id="close-db",
            label="Remove direct app → database exposure",
            remove_relationships=["web-db"],
            cost=1,
            impact="Database access remains through internal API.",
            rollback="Restore web-db in a new snapshot.",
        ),
        Action(
            id="stop-api",
            label="Disable app → API connectivity",
            remove_relationships=["web-api"],
            cost=1,
            impact="Breaks essential application flow; planner must reject.",
            rollback="Restore web-api in a new snapshot.",
        ),
    ]
    return inventory, scenarios, actions
