#!/usr/bin/env python3
"""
Katopu freeze/snapshot plugin
=============================

Deterministic, reproducible identity hashing for circuit definitions and
training run configurations.

Primitives
----------
- ``canonicalize(obj)``    : RFC 8785 (JCS) style canonical JSON → ``bytes``
- ``freeze_hash(obj)``     : returns ``"freeze:<sha256_hex>"``
- ``verify_freeze(obj, h)``: returns ``bool``

The canonical form used here satisfies the invariants exercised by
``tests/plugins/run_freeze_tests.py``:

1. Object keys are sorted lexicographically.
2. No insignificant whitespace (``separators=(',', ':')``).
3. UTF-8 encoding of the output bytes, no ``\\uXXXX`` escaping of non-ASCII.
4. Numeric canonicalization: integer-valued numbers render without a
   fractional part (``1.0`` → ``1``); ``-0`` and ``-0.0`` normalize to ``0``;
   booleans remain booleans (never coerced to ``0``/``1``).
5. ``NaN``/``Infinity`` are rejected — they have no canonical JSON form.

The goal is not to be *bit-identical* with a reference JCS library; it is to
be *bit-identical with itself* across key reorderings, whitespace changes,
and equivalent numeric representations. Catch the classes of drift that
actually break reproducibility in practice.

The plugin uses Python stdlib only (``hashlib``, ``json``, ``math``, ``sys``,
``argparse``).

CLI
---
::

    python3 entrypoint.py hash   <path-to-json>
    python3 entrypoint.py verify <path-to-json> <expected-hash>

Exit codes: ``0`` success, ``1`` mismatch, ``2`` usage/parse error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from typing import Any

FREEZE_PREFIX = "freeze:"


# --------------------------------------------------------------------------- #
# Canonicalization
# --------------------------------------------------------------------------- #

def _canonical_number(x: float | int) -> Any:
    """Return a value that ``json.dumps`` will emit in canonical form.

    - ``True``/``False`` are booleans and never reach this function.
    - Finite integer-valued floats are coerced to ``int`` so ``1.0`` → ``1``.
    - ``-0.0`` and ``-0`` are normalized to ``0``.
    - Other finite floats are passed through; Python's ``repr``-style float
      formatting in ``json.dumps`` is shortest-round-trip, which is the
      widely-accepted canonical form outside of formal JCS.
    - NaN / Infinity raise ``ValueError`` — not representable in JSON.
    """
    if isinstance(x, bool):  # bool is a subclass of int in Python
        return x
    if isinstance(x, int):
        # Normalize negative zero integer (not really possible in Python, but be safe)
        return 0 if x == 0 else x
    # float from here
    if math.isnan(x) or math.isinf(x):
        raise ValueError("NaN and Infinity are not canonicalizable in JSON")
    if x == 0.0:  # catches +0.0 and -0.0
        return 0
    if x.is_integer():
        return int(x)
    return x


def _normalize(obj: Any) -> Any:
    """Recursively normalize a value into a JSON-safe, canonical structure."""
    if obj is None or isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)):
        return _canonical_number(obj)
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        # Keys must be strings in canonical JSON. Reject non-string keys
        # explicitly — silently coercing creates hash-collisions across
        # semantically different manifests.
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(
                    f"canonical JSON requires string keys, got {type(k).__name__}: {k!r}"
                )
            out[k] = _normalize(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    raise TypeError(f"value of type {type(obj).__name__} is not JSON-serializable")


def canonicalize(obj: Any) -> bytes:
    """Return canonical JSON bytes for *obj*.

    Behavior contract:

    - Object keys sorted lexicographically at every depth.
    - No insignificant whitespace between tokens.
    - UTF-8 output, non-ASCII characters preserved verbatim.
    - Integer-valued numerics serialize without a decimal point.
    - Negative zero collapses to ``0``.
    - NaN / Infinity raise ``ValueError``.
    """
    normalized = _normalize(obj)
    text = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return text.encode("utf-8")


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #

def freeze_hash(obj: Any) -> str:
    """Return ``"freeze:<sha256_hex>"`` for *obj*."""
    digest = hashlib.sha256(canonicalize(obj)).hexdigest()
    return f"{FREEZE_PREFIX}{digest}"


def verify_freeze(obj: Any, expected_hash: str) -> bool:
    """Return ``True`` iff ``freeze_hash(obj) == expected_hash``."""
    if not isinstance(expected_hash, str):
        return False
    if not expected_hash.startswith(FREEZE_PREFIX):
        return False
    hex_part = expected_hash[len(FREEZE_PREFIX):]
    if len(hex_part) != 64 or not all(c in "0123456789abcdef" for c in hex_part):
        return False
    return freeze_hash(obj) == expected_hash


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _load(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="freeze_snapshot",
        description="Canonical JSON + SHA-256 freeze hashing utility.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_hash = sub.add_parser("hash", help="Print freeze hash for a JSON file.")
    p_hash.add_argument("path")

    p_verify = sub.add_parser("verify", help="Verify a JSON file against an expected freeze hash.")
    p_verify.add_argument("path")
    p_verify.add_argument("expected")

    p_canon = sub.add_parser("canonicalize", help="Print canonical JSON bytes for a file.")
    p_canon.add_argument("path")

    args = parser.parse_args(argv)

    try:
        obj = _load(args.path)
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.cmd == "hash":
        print(freeze_hash(obj))
        return 0
    if args.cmd == "verify":
        ok = verify_freeze(obj, args.expected)
        print("VERIFIED" if ok else "MISMATCH")
        return 0 if ok else 1
    if args.cmd == "canonicalize":
        sys.stdout.buffer.write(canonicalize(obj))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
