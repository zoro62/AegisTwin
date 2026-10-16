"""Fixed bundled connectivity checks. Run inside lab web, never in the application.

DNS destinations are validated at connection time against Docker lab private ranges.
No user-supplied target, URL, command, credential or redirect is accepted.
"""

import ipaddress
import json
import socket
import time
from datetime import datetime, timezone

TARGETS = (
    ("api", 8080, "web-api"),
    ("database", 8080, "web-db"),
    ("admin", 8080, "web-admin"),
)


def allowed(address):
    ip = ipaddress.ip_address(address)
    return (
        ip in ipaddress.ip_network("172.16.0.0/12")
        or ip in ipaddress.ip_network("10.0.0.0/8")
        or ip in ipaddress.ip_network("192.168.0.0/16")
    )


def probe(host, port):
    if (host, port) not in {(h, p) for h, p, _ in TARGETS}:
        raise ValueError("target not allowlisted")
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses or any(not allowed(a[4][0]) for a in addresses):
        raise ValueError("destination outside private lab ranges")
    for family, socktype, proto, _, sockaddr in addresses[:4]:
        # Connect directly to resolved and validated sockaddr; no second DNS lookup.
        with socket.socket(family, socktype, proto) as connection:
            connection.settimeout(1)
            try:
                connection.connect(sockaddr)
                return True
            except OSError:
                continue
    return False


if __name__ == "__main__":
    results = []
    for host, port, edge in TARGETS:
        started = time.perf_counter()
        error = None
        try:
            success = probe(host, port)
        except (OSError, ValueError) as exc:
            success, error = False, str(exc)
        results.append(
            {
                "relationship_id": edge,
                "destination": host,
                "port": port,
                "success": success,
                "error": error,
                "runtime_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )
        time.sleep(0.2)
    print(
        json.dumps(
            {
                "schema_version": "1.0",
                "source": "bundled-web-probe",
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "simulation": False,
                "dimension": "connectivity",
                "results": results,
                "limitation": "TCP connection only. No authentication or compromise was tested.",
            }
        )
    )
