# Freeze / Snapshot Hashing

Deterministic, reproducible **content hashes** for Katopu circuits and
training runs. Introduced in API **v1.2.0** (ACT-019).

## Why this exists

Resource IDs (`circuitId`, `trainingId`) are *mutable pointers*: same ID, the
definition behind it might change over time. Reproducibility, audit trails,
and result caching need a *content hash* — a value that changes iff the
manifest changes.

A freeze hash delivers that. It has three useful properties:

1. **Reproducibility.** Two runs that compute the same freeze hash started
   from byte-equivalent canonical inputs. If your training job produces
   different results from the same freeze hash, the drift is somewhere
   other than the declared configuration.
2. **Audit.** Every frozen circuit / training job carries an immutable
   fingerprint you can log, co-sign, or attest to.
3. **Caching.** Freeze hash is an ideal cache key: deterministic over
   semantically equivalent inputs, unaffected by key ordering or
   whitespace drift across producers.

## How it works

1. **Canonicalize.** Serialize the manifest using a JCS-style
   (RFC 8785-aligned) algorithm:
   - Sort object keys lexicographically at every depth.
   - No insignificant whitespace.
   - UTF-8, no `\uXXXX` escaping of non-ASCII.
   - Integer-valued numerics render without a fractional part
     (`1.0` → `1`, `-0.0` → `0`).
   - `NaN` / `Infinity` are rejected.
2. **SHA-256** the canonical UTF-8 bytes.
3. **Prefix** the hex digest with `freeze:`.

Pattern: `^freeze:[a-f0-9]{64}$`.

Implementation lives in [`plugins/freeze_snapshot/`](../plugins/freeze_snapshot/).

## Freeze hashes vs. resource IDs

| Property              | Resource ID (e.g. `cir_...`) | Freeze hash (`freeze:...`) |
|-----------------------|------------------------------|----------------------------|
| Assigned by           | server on create             | computed from content       |
| Changes on edit       | no (stable pointer)          | yes (new content → new hash) |
| Suitable as cache key | no                           | yes                          |
| Suitable for routing  | yes                          | no                           |
| Suitable for audit    | weak (just a pointer)        | strong (content commitment) |

**Do not** use resource IDs where you want reproducibility. **Do not** use
freeze hashes where you want a routing handle.

## API endpoints

All four endpoints were introduced in v1.2.0 and are fully defined in
`openapi/openapi.yaml`:

| Method | Path                                           | Purpose                                        |
|--------|------------------------------------------------|------------------------------------------------|
| POST   | `/circuits/{circuitId}/freeze`                 | Compute + persist a freeze hash for a circuit  |
| GET    | `/circuits/{circuitId}/freeze`                 | Retrieve the current freeze hash               |
| POST   | `/training/jobs/{trainingId}/freeze`           | Compute + persist a freeze hash for a training job |
| GET    | `/training/jobs/{trainingId}/freeze`           | Retrieve the current freeze hash               |

All four return a `FreezeResponse`:

```json
{
  "resourceId": "cir_01HZZYH8V2DFD9M8Y4WJB9P3J4",
  "resourceKind": "circuit",
  "freezeHash": "freeze:95fcc2bdfb71b80a59ed5628871dce2fc9e9f0b857d7f6b90dfc5338c17e2f68",
  "algorithm": "jcs-canonical-json+sha256",
  "frozenAt": "2026-04-22T12:30:00Z",
  "canonicalBytes": 186
}
```

POST endpoints require the `Idempotency-Key` header (contract-wide rule) and
the `circuits.freeze` / `training.freeze` OAuth scopes.

Frozen resources surface their hash via an optional read-only `freezeHash`
field on the existing `CircuitResource`, `CircuitCreateResponse`,
`TrainingJobResponse`, and `TrainingResultsResponse` schemas.

## Integration example (Python)

```python
from plugins.freeze_snapshot.entrypoint import freeze_hash, verify_freeze

bell = {
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

h = freeze_hash(bell)
# freeze:95fcc2bdfb71b80a59ed5628871dce2fc9e9f0b857d7f6b90dfc5338c17e2f68

assert verify_freeze(bell, h)
```

## CLI

```bash
python3 plugins/freeze_snapshot/entrypoint.py hash path/to/manifest.json
python3 plugins/freeze_snapshot/entrypoint.py verify path/to/manifest.json freeze:abc...
python3 plugins/freeze_snapshot/entrypoint.py canonicalize path/to/manifest.json
```

## Test vectors

See [`plugins/freeze_snapshot/test_vectors.json`](../plugins/freeze_snapshot/test_vectors.json)
for anchor inputs and expected hashes. These are exercised by:

```bash
python3 tests/plugins/run_freeze_tests.py
```

Expected tail: `ALL FREEZE TESTS PASSED`.

## What freeze hashes do NOT do

- **Not authenticity.** A freeze hash says *what* the manifest was, not
  *who* produced it. Pair with `plugins/sha256_verifier` (HMAC-SHA256 with
  a signing secret) for authenticated webhook delivery.
- **Not encryption.** Freeze hashes are non-secret fingerprints.
- **Not canonical *across polyglot producers* in pathological cases.** The
  canonicalizer in this plugin is intentionally conservative but does not
  implement the full ECMAScript `Number.prototype.toString` algorithm for
  arbitrary floats. If your producers disagree on non-integer float
  representation, route all producers through the same reference
  canonicalizer before hashing.

## Related work

- RFC 8785 — JSON Canonicalization Scheme (JCS)
- `reference-implementations/freeze_snapshot_pattern.md` — the pattern
  synthesis that informed this plugin
- `plugins/sha256_verifier/` — companion plugin for webhook signatures
  (authenticity, not identity)
