#!/usr/bin/env python3
"""Circuit optimization workflow example.

Flow:
1) Create circuit
2) Optimize with goal + backend
3) Freeze optimized artifact
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API_URL = os.environ.get("KATOPU_API_URL", "http://localhost:8080")
API_KEY = os.environ.get("KATOPU_API_KEY", "dev-api-key")


def request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{API_URL.rstrip('/')}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url=url, data=body, method=method)
    req.add_header("X-API-Key", API_KEY)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            txt = resp.read().decode("utf-8")
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as exc:
        msg = exc.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {msg}") from exc


def main() -> None:
    created = request(
        "POST",
        "/circuits",
        {
            "name": "Bell State Circuit",
            "qubits": 2,
            "gates": [
                {"type": "h", "target": 0},
                {"type": "cnot", "control": 0, "target": 1},
            ],
            "description": "Example circuit for optimization demo",
        },
    )
    circuit_id = created.get("circuitId")
    if not circuit_id:
        raise RuntimeError("API did not return circuitId")

    optimized = request(
        "POST",
        f"/circuits/{circuit_id}/optimize",
        {
            "goal": "gate-reduction",
            "targetBackend": "ibm-quantum",
            "constraints": {"maxDepth": 16, "preserveMeasurements": True},
        },
    )

    freeze = request(
        "POST",
        f"/freeze/circuits/{circuit_id}",
        {"includeOptimizations": True},
    )

    print("Created circuit:")
    print(json.dumps(created, indent=2))
    print("Optimized circuit:")
    print(json.dumps(optimized, indent=2))
    print("Freeze manifest:")
    print(json.dumps(freeze, indent=2))


if __name__ == "__main__":
    main()
