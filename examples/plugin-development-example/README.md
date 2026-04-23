# Plugin Development Example

This sample plugin demonstrates the expected shape for an OpenMythos plugin.

## Layout

```text
examples/plugin-development-example/
├── entrypoint.py
└── plugin.json
```

## Run locally

```bash
python3 examples/plugin-development-example/entrypoint.py <<'JSON'
{"circuit":{"gates":[{"type":"h"},{"type":"cnot"},{"type":"x"}]}}
JSON
```

## Validate descriptor shape

```bash
python3 plugins/registry.py verify --id=example_gate_counter
```

Note: this example is intentionally not listed in `plugins/marketplace.json`.
