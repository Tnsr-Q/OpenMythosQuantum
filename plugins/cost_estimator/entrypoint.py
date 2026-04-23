"""Quantum cost estimation plugin."""

from __future__ import annotations

from plugins.sdk import now_ms, require_fields


PRICE_PER_SHOT_USD = 0.00003
PRICE_PER_QUBIT_USD = 0.001


def estimate(payload: dict) -> dict:
    """Estimate total run cost from simple workload dimensions."""
    require_fields(payload, ["jobId", "shots", "qubits"])

    shots = int(payload["shots"])
    qubits = int(payload["qubits"])
    shot_component = shots * PRICE_PER_SHOT_USD
    qubit_component = qubits * PRICE_PER_QUBIT_USD
    total = round(shot_component + qubit_component, 6)

    return {
        "jobId": payload["jobId"],
        "capability": "quantum.estimate.cost",
        "currency": "USD",
        "costEstimate": total,
        "assumptions": {
            "pricePerShot": PRICE_PER_SHOT_USD,
            "pricePerQubit": PRICE_PER_QUBIT_USD,
        },
        "generatedAtMs": now_ms(),
    }
