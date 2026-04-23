# Freeze + Snapshot Pattern (Concrete Reference)

Derived from:
- `workbench_Logic.v1.txt`
- `ric.experiment_manifest.v1.json`
- `snap.boltz.json`

## 1) Canonical Freeze Hash Pattern

```python
import json, hashlib

def canonical_json_bytes(obj: dict) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

def freeze_hash_hex(manifest: dict) -> str:
    return hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
```

## 2) Run Manifest Fields Worth Keeping

```json
{
  "manifest_version": "ric.experiment_manifest.v1",
  "kernel": {
    "id": "ligo.echo_search",
    "version": "0.1.0",
    "contract_version": "ric.echo_search.v1"
  },
  "bindings": {
    "inputs": [
      {
        "name": "input_a",
        "uri": "s3://bucket/path",
        "sha256_hex": "<64-hex>"
      }
    ]
  },
  "reproducibility": {
    "seed": 42,
    "require_hash_check": true,
    "env": {
      "PYTHONHASHSEED": "0"
    }
  },
  "provenance": {
    "git_commit": "<commit>",
    "build_id": "<job-id>"
  }
}
```

## 3) Snapshot Registry Envelope Pattern

```json
{
  "snapshot_name": "Boltz_snap",
  "snapshot_version": "1",
  "snapshot_sha256_hex": "<sha256-of-snapshot-payload>",
  "registry_version": "ric.kernel_registry.v1",
  "kernels": [
    {
      "id": {
        "name": "ligo.echo_search",
        "version": "0.1.0",
        "contract_version": "ric.echo_search.v1"
      },
      "schemas": {
        "parameters_json_schema_b64": "<base64-schema>",
        "parameters_json_schema_sha256_hex": "<64-hex>",
        "ui_hints_json_schema_b64": "<base64-ui-schema>",
        "ui_hints_json_schema_sha256_hex": "<64-hex>"
      }
    }
  ]
}
```

## 4) Katopu Adaptation

- Use this pattern for **circuit manifests** and **training manifests**.
- Keep human-readable schema refs in Git for day-to-day work.
- Publish signed/hashed snapshot bundles for release or offline reproducibility.
