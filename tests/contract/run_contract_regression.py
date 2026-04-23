#!/usr/bin/env python3
"""Basic contract regression checks for openapi/openapi.yaml (no third-party deps)."""

from __future__ import annotations

import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parents[2] / "openapi" / "openapi.yaml"


def main() -> int:
    text = SPEC.read_text(encoding="utf-8")
    required_paths = [
        "/healthz",
        "/orders",
        "/quantum/jobs",
        "/training/jobs",
        "/plugins/{pluginId}/verify",
    ]
    required_security = ["BearerAuth", "ApiKeyAuth", "OAuth2ClientCredentials"]

    failures: list[str] = []
    for path in required_paths:
        if f"  {path}:" not in text:
            failures.append(f"missing path: {path}")
    for scheme in required_security:
        if f"    {scheme}:" not in text:
            failures.append(f"missing security scheme: {scheme}")

    if failures:
        print("Contract regression checks failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("Contract regression checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
