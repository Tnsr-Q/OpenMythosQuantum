# Katopu Plugin Registry Specification

**Status:** Active (introduced in ACT-020, API v1.3.0)
**Owner:** Tanner Jacobsen (GitHub `Tnsr-Q`, ORCID `0009-0000-7999-7242`)
**Depends on:** ACT-019 (freeze / snapshot hashing — `plugins/freeze_snapshot/`)

## 1. Purpose

The plugin registry is a capability-aware, hash-verified catalog of plugins
available to the Katopu API. It replaces ad-hoc plugin discovery with a
single mechanism that is:

- **Declarative** — every plugin ships a `plugin.json` descriptor.
- **Capability-aware** — consumers discover plugins by the *capability*
  they expose, not by name.
- **Integrity-verified** — every descriptor commits to a content hash of
  its entrypoint file(s); the registry refuses to activate a plugin whose
  on-disk bytes do not match.
- **Pragmatic** — stdlib-only implementation (no remote calls, no code
  signing yet — those are explicit future scope).

## 2. Descriptor Schema (JSON)

Formal schema: [`plugins/descriptor.schema.json`](descriptor.schema.json)
(JSON Schema Draft 2020-12, `additionalProperties: false`).

### Required fields

| Field | Type | Notes |
|---|---|---|
| `id` | string | Slug, `^[a-z][a-z0-9_]{2,63}$`. Unique across the registry. |
| `name` | string | Human-readable display name. |
| `version` | string | Semantic version `MAJOR.MINOR.PATCH`. |
| `capabilities` | array of string | At least 1. See §4. |
| `entrypoint` | object | `{ runtime, module, path }`. See §3. |
| `integrity` | object | `{ algorithm, entrypoint }`. See §5. |
| `author` | string | Name or org. |
| `license` | string | SPDX identifier (e.g. `Proprietary`, `MIT`). |
| `lifecycle` | string | One of `registered`, `active`, `deprecated`, `revoked`. See §6. |

### Optional fields

| Field | Type | Notes |
|---|---|---|
| `description` | string | Short summary. |
| `contractVersion` | string | Version of the plugin host contract this plugin targets. |
| `homepage` | string (uri) | Link to plugin documentation. |
| `replaces` | array of string | IDs of plugins this one supersedes. |

## 3. Entrypoint

```json
"entrypoint": {
  "runtime": "python3",
  "module": "entrypoint",
  "path": "entrypoint.py"
}
```

- `runtime` — currently only `python3` is supported. Future: `wasm`, `node20`.
- `module` — the importable module name inside the plugin directory.
- `path` — path to the entrypoint file **relative to `plugin.json`**.

The file referenced by `path` is the sole artifact whose bytes are
committed to by `integrity.entrypoint` (§5).

## 4. Capability Naming Convention

Capabilities are dotted namespaces with at least two segments, lowercase
ASCII:

```
<domain>.<action>[.<qualifier>]
```

### Reserved top-level domains

| Domain | Purpose |
|---|---|
| `webhook.*` | Inbound/outbound webhook primitives. |
| `hash.*` | Content hashing, canonicalization, freeze operations. |
| `circuit.*` | Quantum circuit operations (compile, optimize, simulate). |
| `training.*` | Training run orchestration primitives. |
| `observability.*` | Metrics, traces, logs. |

### Current registered capabilities

| Capability | Plugin | Description |
|---|---|---|
| `webhook.verify.sha256` | `sha256_verifier` | HMAC-SHA256 webhook signature verification. |
| `hash.canonicalize` | `freeze_snapshot` | RFC 8785–style canonical JSON bytes. |
| `hash.freeze.sha256` | `freeze_snapshot` | `freeze:<sha256>` content identity. |

A single plugin **may declare multiple capabilities** when they share the
same entrypoint (as `freeze_snapshot` does).

Capability naming rules enforced by the schema:

- Regex: `^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*){1,3}$`
- At least two segments, at most four.
- Plugins with unknown domains validate structurally but emit a warning
  during `registry.py verify`.

## 5. Integrity Model

The integrity block commits to the **on-disk bytes of the entrypoint
file**. The registry recomputes the hash at load time and refuses any
plugin whose recorded hash does not match.

```json
"integrity": {
  "algorithm": "sha256",
  "entrypoint": "sha256:e8635e8a…"
}
```

### Hash formats

- `sha256:<64 hex>` — raw SHA-256 of the entrypoint file bytes. This is
  the canonical form for non-JSON artifacts.
- `freeze:<64 hex>` — reserved for when the entrypoint is itself a JSON
  manifest (rare). Uses the ACT-019 freeze_snapshot algorithm (canonical
  JSON + SHA-256) from `plugins/freeze_snapshot/entrypoint.py`.

### Relationship to ACT-019

ACT-019 standardized a `freeze:<sha256>` content identity for **JSON
manifests** (circuits, training configs). ACT-020 extends the same
SHA-256 primitive to **plugin entrypoint files**, with two differences:

1. Plugin entrypoints are `.py` source, not JSON — so we hash the raw
   file bytes (no canonicalization step) and use the `sha256:` prefix.
2. The *descriptor* itself is JSON and MAY be freeze-hashed for caching
   or supply-chain purposes (future scope). Today the descriptor's
   content commitment is by reference: whatever the registry loads is
   authoritative at that moment.

### Verification procedure

```python
# registry.verify_integrity(plugin_id)
digest = hashlib.sha256(entrypoint_bytes).hexdigest()
expected = descriptor["integrity"]["entrypoint"].removeprefix("sha256:")
return hmac.compare_digest(digest, expected)
```

Tampering with either (a) the descriptor's recorded hash, or (b) the
on-disk entrypoint file, causes `verify_integrity()` to return `False`.

## 6. Lifecycle States

| State | Meaning | Discoverable by capability? | Loadable? |
|---|---|---|---|
| `registered` | Descriptor valid, not yet activated. | yes | yes |
| `active` | In use; default for newly registered plugins. | yes | yes |
| `deprecated` | Still loadable for backward compat. | yes | yes |
| `revoked` | Forbidden. Registry refuses to load. | **no** | **no** |

### Allowed transitions

```
registered ─► active ─► deprecated ─► revoked
              ▲           │
              └───────────┘   (re-activate from deprecated is allowed)

registered ─► revoked      (pre-activation revocation also allowed)
```

Any transition that does not appear above is rejected by the registry.
Transitions are advisory at this stage — they are enforced in the
in-memory `Registry` object; persistence is future scope.

## 7. Discovery Mechanism

The registry discovers plugins by scanning the `plugins/` directory for
any subdirectory that contains both `plugin.json` and the file referenced
by its `entrypoint.path`. Subdirectories without a `plugin.json` are
silently ignored (non-plugin assets, e.g. `REGISTRY_SPEC.md`).

Discovery is the **only** mechanism today. Future scope: signed remote
registries (see §9).

## 8. CLI

`plugins/registry.py` ships with a CLI that mirrors the registry's
in-process API:

```bash
python3 plugins/registry.py list                          # all descriptors
python3 plugins/registry.py list --lifecycle=active
python3 plugins/registry.py find --capability=hash.freeze.sha256
python3 plugins/registry.py verify                        # verify all plugins
python3 plugins/registry.py verify --id=sha256_verifier   # verify one
python3 plugins/registry.py show --id=freeze_snapshot     # dump descriptor
```

Exit codes: `0` success, `1` verification failure, `2` usage / parse error.

## 9. Security Considerations & Future Scope

- **No signing (yet).** Integrity today means "the file on disk matches
  the hash declared in `plugin.json`". It does **not** prove who wrote
  the descriptor. A malicious actor with write access to the plugin
  directory can update both the file and the hash in lockstep.
  Future scope: signed descriptors (detached signatures, Sigstore, etc.).
- **No remote registries (yet).** All plugins live under `plugins/` in
  the repository. Future scope: pull signed descriptor bundles from a
  remote index.
- **No runtime sandboxing.** Python entrypoints execute in the host
  process. Future scope: wasm runtime with resource limits.

Ask the question: **"What class of drift does this integrity model
actually catch today?"** — silent local edits, botched merges,
half-applied patches, accidentally uploading a different version of the
entrypoint. That is the blast radius this registry is designed for.
Anything stronger (supply-chain attacks, compromised maintainers) needs
signing and is explicitly out of scope for ACT-020.
