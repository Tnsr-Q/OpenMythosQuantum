#!/usr/bin/env python3
"""Example plugin entrypoint.

Counts gates in a provided circuit payload.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from plugins.sdk.utils import now_ms, require_fields


def run(payload: dict) -> dict:
    require_fields(payload, ["circuit"])
    circuit = payload["circuit"]
    gates = circuit.get("gates", [])
    gate_types = [gate.get("type", "unknown") for gate in gates]

    counts: dict[str, int] = {}
    for gate_type in gate_types:
        counts[gate_type] = counts.get(gate_type, 0) + 1

    return {
        "pluginId": "example_gate_counter",
        "summary": {
            "totalGates": len(gates),
            "gateTypeCounts": counts,
        },
        "meta": {
            "ts": now_ms(),
            "version": "0.1.0",
        },
    }


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), indent=2, sort_keys=True))
