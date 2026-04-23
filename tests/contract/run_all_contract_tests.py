#!/usr/bin/env python3
"""
Master Contract Test Runner

Runs all contract tests in sequence and reports results.

Usage:
    python3 tests/contract/run_all_contract_tests.py

Exit code 0 if all tests pass, 1 if any test fails.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TEST_DIR = REPO_ROOT / "tests" / "contract"

# Test modules to run
TESTS = [
    {
        "name": "OpenAPI Contract Validation",
        "script": TEST_DIR / "test_openapi_contract.py",
        "description": "Validates OpenAPI spec against contract requirements"
    },
    {
        "name": "Integration Test Examples",
        "script": TEST_DIR / "test_integration_examples.py",
        "description": "Validates end-to-end workflow examples"
    }
]


def run_test(test_info: dict) -> bool:
    """Run a single test script and return success status."""
    print(f"\n{'=' * 70}")
    print(f"Running: {test_info['name']}")
    print(f"Description: {test_info['description']}")
    print('=' * 70)

    try:
        result = subprocess.run(
            [sys.executable, str(test_info['script'])],
            cwd=REPO_ROOT,
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"ERROR: Failed to run test: {e}")
        return False


def main() -> int:
    """Run all contract tests."""
    print("\n" + "=" * 70)
    print("  MASTER CONTRACT TEST RUNNER")
    print("  OpenMythosQuantum API Contract Test Suite")
    print("=" * 70)
    print(f"  Repository: {REPO_ROOT}")
    print(f"  Running {len(TESTS)} test suite(s)")
    print("=" * 70)

    results = []
    for test in TESTS:
        success = run_test(test)
        results.append({
            "name": test["name"],
            "passed": success
        })

    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUITE SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count

    for result in results:
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        print(f"  {status}  {result['name']}")

    print("=" * 70)
    print(f"  Total: {len(results)} test suites")
    print(f"  Passed: {passed_count}")
    print(f"  Failed: {failed_count}")
    print("=" * 70)

    if failed_count == 0:
        print("\n✓ ALL CONTRACT TEST SUITES PASSED\n")
        return 0
    else:
        print(f"\n✗ {failed_count} TEST SUITE(S) FAILED\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
