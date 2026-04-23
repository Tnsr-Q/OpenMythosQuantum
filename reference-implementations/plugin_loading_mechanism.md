# Plugin Loading Mechanism Pattern

Based on descriptor/snapshot examples in extracted infrastructure files.

## Loader Steps

1. Read registry/snapshot document.
2. Verify top-level snapshot hash (if present).
3. For each plugin/kernel entry:
   - verify schema SHA-256 digests
   - validate descriptor against `kernel_descriptor`-style schema
   - evaluate capability matrix for target runtime
4. Load entrypoint only if descriptor + integrity checks pass.

## Minimal Loader Pseudocode

```python
for plugin in registry["plugins"]:
    verify_sha256(plugin["schemas"]["parameters_json_schema_ref"], plugin["schemas"]["parameters_json_schema_sha256_hex"])
    verify_sha256(plugin["entrypoint"]["package_path"], plugin["entrypoint"]["verify_sha256_hex"])

    if plugin["capability"].get("supports_cluster_compute"):
        register_for_cluster(plugin)
```

## Why This Matters for Katopu

- cleanly extends beyond the current SHA-256 webhook verifier plugin.
- enables secure pluggable optimizers/custom gates with deterministic contracts.
- keeps runtime selection policy explicit and testable.
