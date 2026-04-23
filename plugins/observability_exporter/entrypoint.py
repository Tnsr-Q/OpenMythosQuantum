"""Prometheus observability exporter plugin."""

from __future__ import annotations

from plugins.sdk import now_ms, require_fields


def export(payload: dict) -> dict:
    """Convert a metrics payload to Prometheus exposition text."""
    require_fields(payload, ["service", "metrics"])

    service = payload["service"]
    metrics = payload["metrics"]
    lines: list[str] = []

    for metric_name, metric_value in metrics.items():
        safe_name = str(metric_name).replace("-", "_")
        lines.append(f"openmythos_{safe_name}{{service=\"{service}\"}} {metric_value}")

    return {
        "capability": "observability.export.prometheus",
        "service": service,
        "format": "text/plain; version=0.0.4",
        "payload": "\n".join(lines),
        "generatedAtMs": now_ms(),
    }
