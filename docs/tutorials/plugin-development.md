# Plugin Development Tutorial

This tutorial shows how to build a plugin compatible with the repository's plugin registry conventions.

## Related docs

- `docs/plugin-development.md`
- `plugins/descriptor.schema.json`
- `plugins/registry.py`

## 1) Inspect the example plugin

```bash
tree examples/plugin-development-example
```

Or open files directly:

- `examples/plugin-development-example/entrypoint.py`
- `examples/plugin-development-example/plugin.json`

## 2) Execute the example plugin

```bash
python3 examples/plugin-development-example/entrypoint.py <<'JSON'
{"circuit":{"gates":[{"type":"h"},{"type":"cnot"},{"type":"x"},{"type":"x"}]}}
JSON
```

## 3) Generate integrity hash

```bash
sha256sum examples/plugin-development-example/entrypoint.py | awk '{print "sha256:"$1}'
```

Copy this hash into `integrity.entrypoint` in `plugin.json`.

## 4) Validate plugin registration behavior

Use registry checks against production plugins:

```bash
python3 plugins/registry.py verify --id=sha256_verifier
python3 plugins/registry.py find --capability=webhook.verify
```

## 5) Adapt for your plugin

- Change `id`, `name`, and `capabilities`.
- Keep deterministic output format and include metadata timestamps.
- Use `plugins/sdk/utils.py` helpers for field validation and timestamps.
