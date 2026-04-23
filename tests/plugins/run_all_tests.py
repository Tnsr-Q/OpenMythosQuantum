#!/usr/bin/env python3
"""Run all plugin test suites."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUITES = [
    "tests/plugins/run_freeze_tests.py",
    "tests/plugins/run_registry_tests.py",
    "tests/plugins/run_sha256_webhook_tests.py",
]


def main() -> int:
    for suite in SUITES:
        print(f"[plugins] running {suite}")
        completed = subprocess.run([sys.executable, str(ROOT / suite)], check=False)
        if completed.returncode != 0:
            return completed.returncode
    print("[plugins] all plugin suites passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
