# Generated Artifacts

This directory is reserved for generated outputs from the OpenAPI contract.

## Clients

Generate language SDK clients:

```bash
bash scripts/generate-clients.sh
```

- `generated/python-client/`
- `generated/typescript-client/`

## Server Stubs

Generate reference server stub implementations:

```bash
bash scripts/generate-server-stubs.sh
```

- `generated/server-stubs/python-fastapi/`
- `generated/server-stubs/nodejs-express/`

## API Reference HTML

Build Redoc HTML docs:

```bash
bash scripts/generate-api-docs.sh
```

Outputs: `docs/api-reference.html`
