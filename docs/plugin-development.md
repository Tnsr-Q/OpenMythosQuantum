# Plugin Development Guide

This project uses a descriptor-based plugin registry under `plugins/`.

## 1) Create a plugin directory

```text
plugins/<plugin_id>/
  entrypoint.py
  plugin.json
  README.md
```

## 2) Implement entrypoint logic

Use helpers from `plugins/sdk`:

- `require_fields(payload, [...])` to validate input.
- `now_ms()` for response metadata timestamps.

## 3) Create descriptor (`plugin.json`)

Required fields are validated by `plugins/descriptor.schema.json`.

Use capability names with dotted namespace format:

- `circuit.*`
- `quantum.*`
- `hash.*`
- `webhook.*`
- `observability.*`

## 4) Hash entrypoint for integrity

```bash
sha256sum plugins/<plugin_id>/entrypoint.py | awk '{print "sha256:"$1}'
```

Paste this value into `integrity.entrypoint`.

## 5) Verify registration

```bash
python3 plugins/registry.py verify --id=<plugin_id>
python3 plugins/registry.py find --capability=<capability>
```

## 6) Update marketplace index

Add the plugin record to `plugins/marketplace.json`.
