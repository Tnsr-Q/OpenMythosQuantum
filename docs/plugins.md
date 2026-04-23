# Plugin Registry

**Introduced:** API v1.3.0 (ACT-020)
**Spec:** [`plugins/REGISTRY_SPEC.md`](../plugins/REGISTRY_SPEC.md)
**Schema:** [`plugins/descriptor.schema.json`](../plugins/descriptor.schema.json)

## Overview

The plugin registry is a small, stdlib-only catalog of plugins available to
the Katopu API. Each plugin ships a `plugin.json` descriptor that declares:

- what it does (a set of **capabilities**),
- how to load it (an **entrypoint**),
- what it actually is on disk (an **integrity** hash of the entrypoint bytes).

The registry refuses to return plugins whose on-disk bytes do not match the
hash recorded in their descriptor.

## Authoring a Plugin

A plugin lives in its own directory under `plugins/`:

```
plugins/
  my_plugin/
    entrypoint.py       ← actual code
    plugin.json         ← descriptor
    README.md           ← (optional) docs
```

Minimal `plugin.json`:

```json
{
  "id": "my_plugin",
  "name": "My Plugin",
  "version": "0.1.0",
  "capabilities": ["circuit.optimize.passes"],
  "entrypoint": {
    "runtime": "python3",
    "module": "entrypoint",
    "path": "entrypoint.py"
  },
  "integrity": {
    "algorithm": "sha256",
    "entrypoint": "sha256:<64-hex>",
    "reference": "ACT-019 freeze_snapshot — SHA-256 primitive applied to raw entrypoint bytes"
  },
  "author": "Your Name",
  "license": "Proprietary",
  "lifecycle": "active"
}
```

Compute the integrity hash whenever the entrypoint changes:

```bash
sha256sum plugins/my_plugin/entrypoint.py | awk '{print "sha256:"$1}'
```

Paste the result into `integrity.entrypoint`, then verify:

```bash
python3 plugins/registry.py verify --id=my_plugin
```

## Capability Namespace Conventions

Capabilities are dotted names. Rules:

- 2 to 4 segments, lowercase ASCII, regex:
  `^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*){1,3}$`
- Reserved top-level domains:
  - `webhook.*` — inbound/outbound webhook primitives
  - `hash.*` — content hashing and canonicalization
  - `circuit.*` — quantum circuit operations
  - `training.*` — training run primitives
  - `observability.*` — metrics, traces, logs

Currently registered:

| Capability | Plugin |
|---|---|
| `webhook.verify.sha256` | `sha256_verifier` |
| `hash.canonicalize` | `freeze_snapshot` |
| `hash.freeze.sha256` | `freeze_snapshot` |
| `circuit.optimize.gate_reduction` | `circuit_optimizer` |
| `quantum.estimate.cost` | `cost_estimator` |
| `observability.export.prometheus` | `observability_exporter` |

A single plugin may declare multiple capabilities when they share the same
entrypoint. See `plugins/freeze_snapshot/plugin.json` for an example.

## Integrity Model

The descriptor commits to the SHA-256 of the entrypoint file. The registry
recomputes this hash at load time (and on demand via
`POST /plugins/{pluginId}/verify`).

### Cross-reference to ACT-019

[ACT-019](./freeze-snapshot.md) introduced `freeze:<sha256>` as a canonical
content identity for **JSON manifests** (circuits, training configs). The
canonicalization step (sorted keys, stripped whitespace, numeric
normalization) makes the hash stable across semantically-identical JSON
encodings.

ACT-020 extends the same underlying **SHA-256 primitive** to **plugin
entrypoint files**, with two differences:

1. Entrypoints are `.py` source, not JSON. There is no canonicalization
   step — we hash raw file bytes and use the `sha256:` prefix to make the
   distinction explicit.
2. If a plugin entrypoint is itself JSON (rare), the `freeze:` prefix and
   the `freeze_snapshot` canonicalizer MAY be used instead. The schema
   currently enforces `sha256:` only; a future revision will add
   `freeze:<hex>` as an allowed format.

### What this catches

- Silent local edits to an entrypoint (e.g. a debug `print` left in).
- Half-applied patches where the descriptor updates but the file doesn't
  (or vice versa).
- Accidental deploy of the wrong plugin version.

### What this does NOT catch (yet)

- **Supply-chain attacks.** A malicious actor with write access to the
  plugin directory can update both the file and the hash in lockstep.
- **Compromised maintainers.** No signature is checked today.

Signing is explicit future scope (see [§ Security considerations](#security-considerations)).

## Lifecycle Management

Plugins have four lifecycle states:

| State | Discoverable? | Loadable? |
|---|---|---|
| `registered` | yes | yes |
| `active` | yes (default) | yes |
| `deprecated` | yes | yes |
| `revoked` | **no** | **no** |

Allowed transitions:

```
registered ─► active ─► deprecated ─► revoked
              ▲           │
              └───────────┘
registered ─► revoked
```

`revoked` is terminal. Any transition not shown above is rejected by
`Registry.set_lifecycle`.

Transitions are currently in-memory only; persisting lifecycle changes
(e.g. via an admin API) is future scope.

## CLI & API Surface

### CLI

```bash
python3 plugins/registry.py list
python3 plugins/registry.py list --lifecycle=active
python3 plugins/registry.py find --capability=hash.freeze.sha256
python3 plugins/registry.py verify
python3 plugins/registry.py verify --id=sha256_verifier
python3 plugins/registry.py show --id=freeze_snapshot
```

### HTTP (OpenAPI v1.3.0)

| Method | Path | Scope |
|---|---|---|
| GET  | `/plugins`                                | `plugins.read`   |
| GET  | `/plugins/{pluginId}`                     | `plugins.read`   |
| GET  | `/plugins/capabilities/{capability}`      | `plugins.read`   |
| POST | `/plugins/{pluginId}/verify`              | `plugins.verify` |

All GETs support standard rate-limit headers; the POST supports
`Idempotency-Key`.

## Security Considerations

**Today:** integrity means "the file on disk matches the hash declared in
`plugin.json`". That is sufficient to catch drift, botched merges, and
accidental version mismatches — the failure modes that actually occur in
normal operation.

**Not yet covered:**

- **Signed descriptors.** A future revision will add detached signatures
  (Sigstore/cosign or similar) so that descriptors themselves can be
  authenticated, not just compared against their own recorded hashes.
- **Remote registries.** All plugins currently live under `plugins/` in
  the repository. Pulling signed descriptor bundles from a remote index
  is future scope.
- **Runtime sandboxing.** Python entrypoints execute in the host process.
  A WASM runtime with resource limits is on the roadmap but explicitly
  out of scope for ACT-020.

When you read "integrity" in the current spec, read it as **content
integrity**, not **authenticity**. The difference matters: authenticity
requires signing.

## References

- [`plugins/REGISTRY_SPEC.md`](../plugins/REGISTRY_SPEC.md) — full specification
- [`plugins/descriptor.schema.json`](../plugins/descriptor.schema.json) — JSON Schema
- [`docs/freeze-snapshot.md`](./freeze-snapshot.md) — ACT-019 (JSON freeze hashing)
- [`tests/plugins/run_registry_tests.py`](../tests/plugins/run_registry_tests.py) — deterministic tests


## Plugin SDK

Shared authoring helpers are available in [`plugins/sdk`](../plugins/sdk/README.md).
Use this for base interfaces and payload-validation utilities when creating
new plugins.

## Marketplace Manifest

A machine-readable plugin index is maintained at
[`plugins/marketplace.json`](../plugins/marketplace.json).

See [`docs/plugin-development.md`](./plugin-development.md) for the complete
authoring workflow.
