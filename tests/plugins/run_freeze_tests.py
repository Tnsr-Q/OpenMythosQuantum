#!/usr/bin/env python3
"""
Deterministic runtime tests for the freeze_snapshot plugin.

Invoked as:
    python3 tests/plugins/run_freeze_tests.py

Exit code 0 on success, 1 on any assertion failure.
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "plugins" / "freeze_snapshot"
sys.path.insert(0, str(PLUGIN_DIR))

# Imported after sys.path adjustment so we load the plugin under test.
from entrypoint import canonicalize, freeze_hash, verify_freeze  # noqa: E402

# --------------------------------------------------------------------------- #
# Test harness
# --------------------------------------------------------------------------- #

_PASSED = 0
_FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global _PASSED, _FAILED
    if condition:
        _PASSED += 1
        print(f"  PASS  {label}")
    else:
        _FAILED += 1
        print(f"  FAIL  {label}  {detail}")


def section(title: str) -> None:
    print(f"\n== {title} ==")


# --------------------------------------------------------------------------- #
# TEST-FREEZE-001: canonicalization determinism across key reorderings
# --------------------------------------------------------------------------- #

def test_key_reordering() -> None:
    section("TEST-FREEZE-001  key-reordering determinism")

    a = {
        "name": "bell-state",
        "qubits": 2,
        "gates": [{"op": "h", "target": 0}, {"op": "cx", "control": 0, "target": 1}],
        "measurements": [{"qubit": 0, "classical": 0}, {"qubit": 1, "classical": 1}],
    }
    b = {
        "measurements": [{"classical": 0, "qubit": 0}, {"classical": 1, "qubit": 1}],
        "gates": [{"target": 0, "op": "h"}, {"target": 1, "control": 0, "op": "cx"}],
        "qubits": 2,
        "name": "bell-state",
    }
    check("top-level reorder yields same canonical bytes", canonicalize(a) == canonicalize(b))
    check("top-level reorder yields same freeze hash", freeze_hash(a) == freeze_hash(b))

    # Nested reorder
    c = {"outer": {"z": 1, "a": 2, "m": 3}}
    d = {"outer": {"a": 2, "m": 3, "z": 1}}
    check("nested reorder yields same hash", freeze_hash(c) == freeze_hash(d))

    # Arrays are ORDER-SENSITIVE (explicit contract)
    check(
        "array element order IS significant",
        freeze_hash([1, 2, 3]) != freeze_hash([3, 2, 1]),
    )


# --------------------------------------------------------------------------- #
# TEST-FREEZE-002: whitespace insensitivity
# --------------------------------------------------------------------------- #

def test_whitespace_insensitivity() -> None:
    section("TEST-FREEZE-002  whitespace insensitivity")

    # The canonicalizer takes Python objects, so whitespace enters only via
    # JSON round-trip. Parse two differently-formatted JSON strings into
    # objects and hash — they must agree.
    raw_compact = '{"a":1,"b":[1,2,3],"c":{"x":"y"}}'
    raw_pretty = """
    {
        "a": 1,
        "b": [
            1,
            2,
            3
        ],
        "c": { "x": "y" }
    }
    """
    obj1 = json.loads(raw_compact)
    obj2 = json.loads(raw_pretty)
    check("compact vs pretty JSON → same canonical bytes", canonicalize(obj1) == canonicalize(obj2))
    check("compact vs pretty JSON → same freeze hash", freeze_hash(obj1) == freeze_hash(obj2))


# --------------------------------------------------------------------------- #
# TEST-FREEZE-003: numeric canonicalization
# --------------------------------------------------------------------------- #

def test_numeric_canonicalization() -> None:
    section("TEST-FREEZE-003  numeric canonicalization")

    check("1 == 1.0", freeze_hash(1) == freeze_hash(1.0))
    check("0 == -0", freeze_hash(0) == freeze_hash(-0))
    check("0 == -0.0", freeze_hash(0) == freeze_hash(-0.0))
    check("0 == 0.0", freeze_hash(0) == freeze_hash(0.0))

    # Integer-valued float inside a nested structure
    a = {"lr": 1, "epochs": 10}
    b = {"lr": 1.0, "epochs": 10.0}
    check("nested int vs int-valued float match", freeze_hash(a) == freeze_hash(b))

    # Different integer-valued numerics still differ
    check("1 != 2", freeze_hash(1) != freeze_hash(2))

    # NaN / Inf rejected
    raised = False
    try:
        canonicalize(float("nan"))
    except ValueError:
        raised = True
    check("NaN raises ValueError", raised)

    raised = False
    try:
        canonicalize(float("inf"))
    except ValueError:
        raised = True
    check("Infinity raises ValueError", raised)

    # Booleans are preserved, NOT coerced to 0/1
    check("True != 1", freeze_hash(True) != freeze_hash(1))
    check("False != 0", freeze_hash(False) != freeze_hash(0))


# --------------------------------------------------------------------------- #
# TEST-FREEZE-004: full circuit freeze vector (Bell state)
# --------------------------------------------------------------------------- #

BELL_CIRCUIT = {
    "schemaVersion": "1.0",
    "name": "bell-state",
    "qubits": 2,
    "gates": [
        {"op": "h", "target": 0},
        {"op": "cx", "control": 0, "target": 1},
    ],
    "measurements": [
        {"qubit": 0, "classical": 0},
        {"qubit": 1, "classical": 1},
    ],
}
BELL_EXPECTED = "freeze:95fcc2bdfb71b80a59ed5628871dce2fc9e9f0b857d7f6b90dfc5338c17e2f68"


def test_bell_circuit_vector() -> None:
    section("TEST-FREEZE-004  Bell-state circuit anchor vector")
    h = freeze_hash(BELL_CIRCUIT)
    check(
        "Bell-state hash matches anchor",
        h == BELL_EXPECTED,
        detail=f"got {h}",
    )
    check("verify_freeze accepts the anchor", verify_freeze(BELL_CIRCUIT, BELL_EXPECTED))


# --------------------------------------------------------------------------- #
# TEST-FREEZE-005: full training job freeze vector
# --------------------------------------------------------------------------- #

TRAINING_JOB = {
    "schemaVersion": "1.0",
    "modelName": "katopu-baseline",
    "datasetId": "ds_abc123",
    "hyperparameters": {
        "learningRate": 0.001,
        "batchSize": 32,
        "epochs": 10,
    },
    "seed": 42,
}
TRAINING_EXPECTED = "freeze:2adea023c4b47899106b7aa01b52c94ebfa4985e64ecc8a1c481004fae69375f"


def test_training_job_vector() -> None:
    section("TEST-FREEZE-005  training job anchor vector")
    h = freeze_hash(TRAINING_JOB)
    check(
        "training job hash matches anchor",
        h == TRAINING_EXPECTED,
        detail=f"got {h}",
    )
    check("verify_freeze accepts the anchor", verify_freeze(TRAINING_JOB, TRAINING_EXPECTED))


# --------------------------------------------------------------------------- #
# TEST-FREEZE-006: tamper detection (single-field change → different hash)
# --------------------------------------------------------------------------- #

def test_tamper_detection() -> None:
    section("TEST-FREEZE-006  tamper detection")

    tampered_circuit = copy.deepcopy(BELL_CIRCUIT)
    tampered_circuit["gates"][0]["target"] = 1  # flip one target qubit
    check(
        "circuit: single-bit field change → different hash",
        freeze_hash(tampered_circuit) != BELL_EXPECTED,
    )
    check(
        "circuit: verify_freeze rejects tampered payload",
        verify_freeze(tampered_circuit, BELL_EXPECTED) is False,
    )

    tampered_training = copy.deepcopy(TRAINING_JOB)
    tampered_training["hyperparameters"]["learningRate"] = 0.002
    check(
        "training: single-field change → different hash",
        freeze_hash(tampered_training) != TRAINING_EXPECTED,
    )
    check(
        "training: verify_freeze rejects tampered payload",
        verify_freeze(tampered_training, TRAINING_EXPECTED) is False,
    )

    # Added field → different hash (no silent ignore)
    extended = copy.deepcopy(BELL_CIRCUIT)
    extended["comment"] = "extra metadata"
    check(
        "adding a field → different hash",
        freeze_hash(extended) != BELL_EXPECTED,
    )

    # Malformed expected hash → False (not exception)
    check("malformed hash prefix → False", verify_freeze({}, "sha256:abc") is False)
    check("malformed hash length → False", verify_freeze({}, "freeze:abc") is False)
    check("non-hex chars → False", verify_freeze({}, "freeze:" + "z" * 64) is False)


# --------------------------------------------------------------------------- #
# TEST-FREEZE-007: test_vectors.json agreement
# --------------------------------------------------------------------------- #

def test_vectors_file() -> None:
    section("TEST-FREEZE-007  test_vectors.json agreement")
    vectors_path = PLUGIN_DIR / "test_vectors.json"
    with open(vectors_path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    for v in payload["vectors"]:
        got = freeze_hash(v["input"])
        check(
            f"vector '{v['name']}' matches expected",
            got == v["expected"],
            detail=f"got {got}",
        )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    test_key_reordering()
    test_whitespace_insensitivity()
    test_numeric_canonicalization()
    test_bell_circuit_vector()
    test_training_job_vector()
    test_tamper_detection()
    test_vectors_file()

    print(f"\nResults: {_PASSED} passed, {_FAILED} failed.")
    if _FAILED:
        print("FREEZE TESTS FAILED")
        return 1
    print("ALL FREEZE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
