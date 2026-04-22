#!/usr/bin/env python3
"""Deterministic runtime checks for sha256_verifier plugin using realistic webhook payloads."""

import hashlib
import hmac
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "sha256_verifier" / "entrypoint.py"
FIXTURES = ROOT / "tests" / "fixtures" / "webhooks"
SECRET = "week1-realistic-secret"


def sign(secret: str, payload: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def run_plugin(secret: str, signature: str, payload_file: Path):
    return subprocess.run(
        [
            sys.executable,
            str(PLUGIN),
            "--secret",
            secret,
            "--signature",
            signature,
            "--payload-file",
            str(payload_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def assert_case(label: str, secret: str, signature: str, payload_file: Path, expected_code: int, expected_stdout: str):
    result = run_plugin(secret, signature, payload_file)
    actual_stdout = result.stdout.strip()
    if result.returncode != expected_code or actual_stdout != expected_stdout:
        raise AssertionError(
            f"{label} failed: code={result.returncode}, stdout={actual_stdout!r}, stderr={result.stderr!r}"
        )
    print(f"PASS: {label}")


def main() -> int:
    training_payload = FIXTURES / "training.completed.json"
    notification_payload = FIXTURES / "notification.delivered.json"

    training_bytes = training_payload.read_bytes()
    notification_bytes = notification_payload.read_bytes()

    training_sig = sign(SECRET, training_bytes)
    notification_sig = sign(SECRET, notification_bytes)

    # Positive checks with realistic payload shapes
    assert_case(
        "training.completed valid signature",
        SECRET,
        training_sig,
        training_payload,
        0,
        "VERIFIED",
    )
    assert_case(
        "notification.delivered valid signature",
        SECRET,
        notification_sig,
        notification_payload,
        0,
        "VERIFIED",
    )

    # Negative checks
    assert_case(
        "training.completed tampered payload",
        SECRET,
        training_sig,
        notification_payload,
        1,
        "INVALID",
    )
    assert_case(
        "notification.delivered wrong secret",
        "wrong-secret",
        notification_sig,
        notification_payload,
        1,
        "INVALID",
    )

    print("All SHA-256 webhook verifier checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
