# Contributing to Katopu Quantum AGI API

Thanks for helping improve the project. This guide covers the expected workflow for API changes, plugin work, and pull requests.

## Development Setup

Use the bootstrap script:

```bash
bash scripts/setup-dev.sh
```

Or install manually:

```bash
pip install -e .[dev]
npm install
```

## How to Add a New Endpoint

1. Update `openapi/openapi.yaml`.
   - Add the new route under `paths`.
   - Add reusable schemas under `components/schemas` when needed.
   - Define auth (`security`) and errors (`4xx` / `5xx`) explicitly.
2. Validate and lint the contract:

   ```bash
   make validate
   make lint
   ```

3. Add or update contract tests in `tests/contract/`.
4. If behavior is reflected in the reference runtime, update `runtime/server.py`.
5. Regenerate docs/clients if your change affects consumers:

   ```bash
   make docs
   bash scripts/generate-clients.sh
   ```

## How to Create a Plugin

1. Create a new plugin folder:

   ```text
   plugins/<plugin_id>/
     entrypoint.py
     plugin.json
     README.md
   ```

2. Implement logic in `entrypoint.py` using helpers from `plugins/sdk` where useful.
3. Add descriptor metadata in `plugin.json` and ensure it conforms to `plugins/descriptor.schema.json`.
4. Calculate integrity hash and add it to `plugin.json`:

   ```bash
   sha256sum plugins/<plugin_id>/entrypoint.py | awk '{print "sha256:"$1}'
   ```

5. Register and verify:

   ```bash
   python3 plugins/registry.py verify --id=<plugin_id>
   python3 plugins/registry.py find --capability=<capability>
   ```

6. Update `plugins/marketplace.json` when adding distributable plugins.
7. Add or update tests under `tests/plugins/`.

For additional details, see `docs/plugin-development.md`.

## Testing Guidelines

Run the standard checks before opening a PR:

```bash
make validate
make lint
make test
python3 tests/contract/run_all_contract_tests.py
python3 tests/plugins/run_all_tests.py
```

Recommended:

- Keep fixtures in `tests/fixtures/` focused and deterministic.
- Add at least one failing test for bug fixes before implementing the fix.
- Prefer contract tests for API compatibility guarantees and plugin tests for runtime behavior.

## Code Review Checklist

- [ ] OpenAPI contract still validates and lints cleanly.
- [ ] New/updated endpoints document auth, request/response schema, and error responses.
- [ ] Tests cover happy-path and at least one failure path.
- [ ] Plugin descriptors pass registry verification.
- [ ] No secrets or production credentials were introduced.
- [ ] Documentation was updated (`README`, `docs/`, examples) when behavior changed.

## Pull Request Expectations

- Keep changes focused and atomic.
- Include a short summary, rationale, and validation steps performed.
- Link related issue(s) or audit references when applicable (for example: `AUDIT_REPORT.md §6.5`).

## Security

Please review and follow `SECURITY.md` for vulnerability reporting and security policy.
