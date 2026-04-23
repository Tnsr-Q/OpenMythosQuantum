# freeze_snapshot plugin

Deterministic, reproducible identity hashing for Katopu circuit definitions
and training run configurations.

A freeze hash is a **content hash** — two semantically equivalent manifests
(same keys, same values, different key order or whitespace) produce the same
hash. Two manifests that differ in even a single field produce different
hashes.

## Algorithm

1. **Canonical JSON** (JCS-style):
   - Object keys sorted lexicographically at every depth.
   - No insignificant whitespace (`separators=(',', ':')`).
   - UTF-8 output, non-ASCII preserved verbatim (no `\uXXXX` escaping).
   - Integer-valued numerics render without a fractional part (`1.0` → `1`).
   - `-0.0` collapses to `0`.
   - `NaN` / `Infinity` are rejected — not canonically representable in JSON.
2. **SHA-256** of the canonical UTF-8 bytes.
3. **Prefix** the hex digest with `freeze:` to produce the opaque identifier.

Pattern: `^freeze:[a-f0-9]{64}$`

## Python API

```python
from plugins.freeze_snapshot.entrypoint import (
    canonicalize, freeze_hash, verify_freeze,
)

canonicalize({"b": 1, "a": 2})
# b'{"a":2,"b":1}'

freeze_hash({"name": "bell-state", "qubits": 2})
# 'freeze:<64-hex>'

verify_freeze({"name": "bell-state", "qubits": 2}, "freeze:abc...")
# True / False
```

## CLI

```bash
# Hash a JSON file
python3 plugins/freeze_snapshot/entrypoint.py hash path/to/manifest.json

# Verify against an expected hash
python3 plugins/freeze_snapshot/entrypoint.py verify path/to/manifest.json freeze:abc...

# Dump canonical JSON bytes (useful for debugging drift)
python3 plugins/freeze_snapshot/entrypoint.py canonicalize path/to/manifest.json
```

Exit codes: `0` success, `1` mismatch, `2` usage or parse error.

## Test vectors

See [`test_vectors.json`](./test_vectors.json) for anchor inputs and their
expected freeze hashes. These cover:

- Empty object / array
- Primitive types (`null`, `true`, integers, floats, strings, Unicode)
- Numeric canonicalization (`1.0 == 1`, `-0.0 == 0`)
- A canonical 2-qubit Bell-state circuit
- A minimal training job configuration

Regenerate with:

```bash
python3 plugins/freeze_snapshot/entrypoint.py hash <input.json>
```

## Integration with the Katopu API

See [`docs/freeze-snapshot.md`](../../docs/freeze-snapshot.md) for the full
contract. Summary:

- `POST /circuits/{circuitId}/freeze` — compute and persist the freeze hash
  for a circuit definition.
- `GET  /circuits/{circuitId}/freeze` — retrieve the current freeze hash.
- `POST /training/jobs/{trainingId}/freeze` — freeze a training job config.
- `GET  /training/jobs/{trainingId}/freeze` — retrieve the current freeze
  hash for a training job.

Resources gain an optional read-only `freezeHash` field that reflects the
last-computed value.

## Running the tests

```bash
python3 tests/plugins/run_freeze_tests.py
```

Expected output ends with `ALL FREEZE TESTS PASSED`.

## Why not just `json.dumps(..., sort_keys=True)`?

That gets you most of the way — but it emits `1.0` and `1` as different
strings, escapes non-ASCII to `\uXXXX` by default, and treats `-0.0` as
distinct from `0`. Those differences silently break reproducibility when
manifests round-trip through different serializers (JavaScript clients, Go
services, YAML → JSON converters). The canonicalizer here is intentionally
conservative about these classes of drift.

## Non-goals

- **Not** a full RFC 8785 implementation. We do not attempt the complete
  ECMAScript `Number.prototype.toString` algorithm for non-integer floats;
  Python's shortest-round-trip `repr` is used instead. If you need strict
  JCS parity across polyglot producers, feed all producers through the same
  reference JCS library before hashing.
- **Not** a signature scheme. Freeze hashes are identity, not authenticity.
  Pair with `plugins/sha256_verifier` (HMAC) for signed webhook delivery.
