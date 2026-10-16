"""Fixed harmless canary endpoint. No shell, credentials, arbitrary URLs or payloads."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = json.dumps(
            {
                "service": os.environ.get("LAB_NAME", "canary"),
                "synthetic": True,
                "records": [{"id": 1, "value": "harmless-canary"}],
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)


HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
