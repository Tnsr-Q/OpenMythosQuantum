#!/usr/bin/env python3
"""Validate required security baseline environment settings."""

from __future__ import annotations

import argparse
import pathlib
import sys


REQUIRED_TLS_MIN = 1.2


def load_env(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def check_tls_version(values: dict[str, str]) -> tuple[bool, str]:
    raw = values.get("TLS_MIN_VERSION")
    if raw is None:
        return False, "TLS_MIN_VERSION is not set"

    try:
        version = float(raw)
    except ValueError:
        return False, f"TLS_MIN_VERSION must be numeric, found: {raw!r}"

    if version < REQUIRED_TLS_MIN:
        return False, f"TLS_MIN_VERSION must be >= {REQUIRED_TLS_MIN}, found: {version}"
    return True, f"TLS_MIN_VERSION={version}"


def check_secret_rotation(values: dict[str, str]) -> tuple[bool, str]:
    raw = values.get("SECRET_ROTATION_DAYS")
    if raw is None or raw == "":
        return False, "SECRET_ROTATION_DAYS is not set"

    try:
        days = int(raw)
    except ValueError:
        return False, f"SECRET_ROTATION_DAYS must be an integer, found: {raw!r}"

    if days <= 0:
        return False, f"SECRET_ROTATION_DAYS must be > 0, found: {days}"
    return True, f"SECRET_ROTATION_DAYS={days}"


def check_webhook_signature(values: dict[str, str]) -> tuple[bool, str]:
    raw = values.get("WEBHOOK_SIGNATURE_ALGORITHM")
    if raw is None or raw == "":
        return False, "WEBHOOK_SIGNATURE_ALGORITHM is not set"
    return True, f"WEBHOOK_SIGNATURE_ALGORITHM={raw}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default="config/.secrets.example",
        help="Path to env file to validate (default: config/.secrets.example)",
    )
    args = parser.parse_args()

    env_path = pathlib.Path(args.env_file)
    if not env_path.exists():
        print(f"ERROR: env file does not exist: {env_path}")
        return 1

    values = load_env(env_path)

    checks = [
        ("check_tls_version", check_tls_version),
        ("check_secret_rotation", check_secret_rotation),
        ("check_webhook_signature", check_webhook_signature),
    ]

    failed = False
    for name, check in checks:
        ok, message = check(values)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {message}")
        failed = failed or not ok

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
