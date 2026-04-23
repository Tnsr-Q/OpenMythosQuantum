#!/usr/bin/env python3
"""Webhook handling example with SHA-256 signature verification.

This example uses the `plugins/sha256_verifier` reference plugin logic.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = os.environ.get("WEBHOOK_HOST", "0.0.0.0")
PORT = int(os.environ.get("WEBHOOK_PORT", "8090"))
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "dev-secret")


def compute_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 (required by BaseHTTPRequestHandler)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)

        received_sig = self.headers.get("X-Katopu-Signature", "")
        expected_sig = compute_signature(body, WEBHOOK_SECRET)

        if not hmac.compare_digest(received_sig, expected_sig):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"error":"invalid signature"}')
            return

        payload = json.loads(body.decode("utf-8"))
        event_type = payload.get("type", "unknown")
        event_id = payload.get("id", "evt_unknown")

        print(f"received webhook event type={event_type} id={event_id}")

        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"accepted":true}')


def main() -> None:
    server = HTTPServer((HOST, PORT), WebhookHandler)
    print(f"Webhook receiver listening on http://{HOST}:{PORT}")
    print("Use ngrok or Cloudflare Tunnel for public delivery in local development.")
    server.serve_forever()


if __name__ == "__main__":
    main()
