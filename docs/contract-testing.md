# Contract Testing Suite Documentation

## Overview

The contract testing suite provides automated validation of the OpenAPI specification and demonstrates end-to-end workflow patterns. These tests ensure the API contract is correct, complete, and follows best practices.

## Test Suites

### 1. OpenAPI Contract Validation (`test_openapi_contract.py`)

Validates the OpenAPI specification programmatically against contract requirements.

**Tests Include:**
- OpenAPI metadata validation (version, JSON Schema dialect)
- Unique operation IDs
- Idempotency key coverage on all POST operations
- Pagination contract (cursor, limit, hasMore)
- Security scheme definitions and coverage
- Webhook signature requirements
- Schema strictness (additionalProperties: false)
- Standard error responses
- Freeze snapshot and plugin registry endpoints

**Usage:**
```bash
python3 tests/contract/test_openapi_contract.py
```

**Exit Codes:**
- `0`: All tests passed
- `1`: One or more tests failed

### 2. Integration Test Examples (`test_integration_examples.py`)

Validates end-to-end workflow patterns and demonstrates proper API usage.

**Tests Include:**
- Training job lifecycle (create → poll → results → freeze)
- Circuit optimization with freeze hash
- Webhook payload validation
- Plugin discovery and verification
- Pagination determinism

**Usage:**
```bash
# Dry-run mode (structure validation only)
python3 tests/contract/test_integration_examples.py

# Against a real API
KATOPU_API_URL=https://api.example.com python3 tests/contract/test_integration_examples.py
```

### 3. Master Test Runner (`run_all_contract_tests.py`)

Runs all contract test suites in sequence and reports aggregate results.

**Usage:**
```bash
python3 tests/contract/run_all_contract_tests.py
```

## Running Tests

### Run All Contract Tests

```bash
cd /path/to/OpenMythosQuantum
python3 tests/contract/run_all_contract_tests.py
```

### Run Individual Test Suites

```bash
# OpenAPI contract validation
python3 tests/contract/test_openapi_contract.py

# Integration test examples
python3 tests/contract/test_integration_examples.py
```

### Run Plugin Tests (for comparison)

```bash
# Freeze snapshot tests
python3 tests/plugins/run_freeze_tests.py

# Plugin registry tests
python3 tests/plugins/run_registry_tests.py

# SHA-256 webhook verifier tests
python3 tests/plugins/run_sha256_webhook_tests.py
```

## Dependencies

The contract test suite requires:
- Python 3.8+
- PyYAML (`pip install pyyaml`)

Optional for full contract validation:
- jsonschema (`pip install jsonschema`) - for complete schema validation
- httpx (`pip install httpx`) - for testing against real APIs

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Contract Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install pyyaml
      - name: Run contract tests
        run: |
          python3 tests/contract/run_all_contract_tests.py
```

## Test Coverage

### Contract Tests Cover:

✅ **API Contract Correctness**
- OpenAPI 3.1.0 compliance
- JSON Schema 2020-12 usage
- Unique operation IDs
- Security scheme definitions

✅ **Modern API Practices**
- Idempotency keys on all POST operations
- Cursor-based pagination
- Webhook signature standards (HMAC-SHA256)
- Standard error responses

✅ **Domain-Specific Features**
- Freeze snapshot endpoints and schemas
- Plugin registry endpoints and schemas
- Training job orchestration patterns
- Circuit optimization workflows

✅ **End-to-End Workflows**
- Training job lifecycle
- Circuit optimization with freeze hash
- Webhook payload structures
- Plugin discovery and verification
- Pagination determinism

## Adding New Tests

### Adding Contract Validation Tests

Edit `tests/contract/test_openapi_contract.py`:

```python
def test_my_new_validation(spec: dict[str, Any]) -> None:
    """Validate my new requirement."""
    section("TEST-CONTRACT-XXX: My New Validation")

    # Your test logic
    check(
        "My test passes",
        condition_to_check,
        "Optional detail message"
    )
```

Then add the test to the main runner:
```python
# In main()
test_my_new_validation(spec)
```

### Adding Integration Tests

Edit `tests/contract/test_integration_examples.py`:

```python
def test_my_workflow(spec: dict) -> None:
    """Test my workflow."""
    section("TEST-INT-XXX: My Workflow")

    # Your workflow simulation
    check("Step 1 succeeds", True, "")
    check("Step 2 succeeds", True, "")
```

Add to main runner:
```python
# In main()
test_my_workflow(spec)
```

## Test Fixtures

Test fixtures are stored in `tests/fixtures/`:

```
tests/fixtures/
├── webhooks/
│   ├── training.completed.json
│   └── notification.delivered.json
└── routing/
    ├── sim_alpha_cost_vs_queue.json
    ├── sim_beta_fidelity_override.json
    └── sim_gamma_topology_mismatch.json
```

### Adding New Fixtures

1. Create JSON file in appropriate subdirectory
2. Follow the existing structure and naming conventions
3. Reference in tests using `pathlib`:

```python
fixture_path = REPO_ROOT / "tests" / "fixtures" / "webhooks" / "my_fixture.json"
with open(fixture_path) as f:
    data = json.load(f)
```

## Troubleshooting

### Test Fails: "pyyaml is required"

Install PyYAML:
```bash
pip install pyyaml
```

### Test Fails: Schema Validation

The integration tests use simplified schema validation. For production use, install jsonschema:
```bash
pip install jsonschema
```

Then enhance `validate_against_schema()` to use proper JSON Schema validation.

### Test Fails: Fixture Not Found

Ensure fixtures exist in `tests/fixtures/` and paths are correct.

### Contract Validation Fails

1. Check the specific failing test
2. Review the OpenAPI spec at the reported location
3. Fix the spec or update the test if the requirement changed
4. Rerun validation: `bash scripts/validate-openapi.sh`

## Best Practices

1. **Run contract tests before committing changes to the OpenAPI spec**
2. **Add tests for new endpoints or schemas**
3. **Keep integration tests focused on workflows, not implementation details**
4. **Use fixtures for complex test data**
5. **Validate against the spec, not against hardcoded expectations**
6. **Run full test suite in CI/CD pipeline**

## Related Documentation

- [OpenAPI Specification](../../openapi/openapi.yaml)
- [Falsifiable Tests](../../FALSIFIABLE_TESTS.md)
- [Plugin Testing](../plugins/)
- [Freeze Snapshot Documentation](../../docs/freeze-snapshot.md)
- [Plugin Registry Specification](../../plugins/REGISTRY_SPEC.md)
