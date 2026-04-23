"""Gate-reduction reference optimizer plugin."""

from __future__ import annotations

from plugins.sdk import now_ms, require_fields


def optimize(payload: dict) -> dict:
    """Return a deterministic gate-reduction estimate.

    Expected payload:
    {
      "circuitId": "...",
      "gateCount": 120,
      "strategy": "commutation-pass"  # optional
    }
    """
    require_fields(payload, ["circuitId", "gateCount"])
    gate_count = int(payload["gateCount"])
    reduction = max(1, int(gate_count * 0.08))
    optimized = max(1, gate_count - reduction)

    return {
        "circuitId": payload["circuitId"],
        "capability": "circuit.optimize.gate_reduction",
        "strategy": payload.get("strategy", "commutation-pass"),
        "before": gate_count,
        "after": optimized,
        "estimatedReductionPct": round(((gate_count - optimized) / gate_count) * 100, 2),
        "generatedAtMs": now_ms(),
    }
