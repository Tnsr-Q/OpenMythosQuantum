#!/usr/bin/env python3
"""
OpenAPI Contract Validation Tests

Programmatically validates the OpenAPI specification against contract requirements:
- Schema correctness
- Idempotency key coverage
- Pagination contract
- Security schemes
- Webhook signatures
- Unique operation IDs
- Standard error responses

Usage:
    python3 tests/contract/test_openapi_contract.py

Exit code 0 on success, 1 on any validation failure.
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml is required. Install with: pip install pyyaml")
    sys.exit(1)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "openapi" / "openapi.yaml"

# Test counters
_PASSED = 0
_FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    """Record test result."""
    global _PASSED, _FAILED
    if condition:
        _PASSED += 1
        print(f"  ✓ PASS  {label}")
    else:
        _FAILED += 1
        print(f"  ✗ FAIL  {label}")
        if detail:
            print(f"          {detail}")


def section(title: str) -> None:
    """Print test section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def load_openapi() -> dict[str, Any]:
    """Load and parse the OpenAPI specification."""
    with open(OPENAPI_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# ============================================================================
# TEST-CONTRACT-001: OpenAPI Metadata Validation
# ============================================================================

def test_openapi_metadata(spec: dict[str, Any]) -> None:
    """Validate OpenAPI metadata and structure."""
    section("TEST-CONTRACT-001: OpenAPI Metadata")

    check(
        "OpenAPI version is 3.1.0",
        spec.get('openapi') == '3.1.0',
        f"Found: {spec.get('openapi')}"
    )

    check(
        "JSON Schema dialect is 2020-12",
        spec.get('jsonSchemaDialect') == 'https://json-schema.org/draft/2020-12/schema',
        f"Found: {spec.get('jsonSchemaDialect')}"
    )

    info = spec.get('info', {})
    check(
        "API title is present",
        bool(info.get('title')),
        f"Title: {info.get('title')}"
    )

    check(
        "API version is present",
        bool(info.get('version')),
        f"Version: {info.get('version')}"
    )

    check(
        "Contact information includes GitHub",
        'github.com/Tnsr-Q' in str(info.get('contact', {})),
        "Expected GitHub URL in contact"
    )

    check(
        "Servers are declared",
        len(spec.get('servers', [])) > 0,
        f"Found {len(spec.get('servers', []))} servers"
    )


# ============================================================================
# TEST-CONTRACT-002: Unique Operation IDs
# ============================================================================

def test_unique_operation_ids(spec: dict[str, Any]) -> None:
    """Validate that all operationIds are unique."""
    section("TEST-CONTRACT-002: Unique Operation IDs")

    operation_ids = []
    paths = spec.get('paths', {})

    for path, methods in paths.items():
        for method, operation in methods.items():
            if method in ['get', 'post', 'put', 'patch', 'delete']:
                if isinstance(operation, dict) and 'operationId' in operation:
                    operation_ids.append(operation['operationId'])

    check(
        f"Found {len(operation_ids)} operation IDs",
        len(operation_ids) > 0,
        "Expected at least one operation"
    )

    duplicates = [op_id for op_id in set(operation_ids) if operation_ids.count(op_id) > 1]
    check(
        "All operation IDs are unique",
        len(duplicates) == 0,
        f"Duplicates: {duplicates}" if duplicates else ""
    )


# ============================================================================
# TEST-CONTRACT-003: Idempotency Key Coverage
# ============================================================================

def test_idempotency_key_coverage(spec: dict[str, Any]) -> None:
    """Validate that all POST operations include Idempotency-Key parameter."""
    section("TEST-CONTRACT-003: Idempotency Key Coverage")

    paths = spec.get('paths', {})
    missing_idempotency = []
    total_post_ops = 0

    for path, methods in paths.items():
        if 'post' in methods:
            total_post_ops += 1
            post_op = methods['post']
            parameters = post_op.get('parameters', [])

            has_idempotency = any(
                p.get('$ref') == '#/components/parameters/IdempotencyKey'
                for p in parameters if isinstance(p, dict)
            )

            if not has_idempotency:
                missing_idempotency.append(path)

    check(
        f"Found {total_post_ops} POST operations",
        total_post_ops > 0,
        "Expected at least one POST operation"
    )

    check(
        "All POST operations include Idempotency-Key",
        len(missing_idempotency) == 0,
        f"Missing in: {missing_idempotency}" if missing_idempotency else ""
    )

    # Verify the IdempotencyKey parameter component exists
    components = spec.get('components', {})
    parameters = components.get('parameters', {})
    check(
        "IdempotencyKey parameter is defined in components",
        'IdempotencyKey' in parameters,
        "Expected #/components/parameters/IdempotencyKey"
    )


# ============================================================================
# TEST-CONTRACT-004: Pagination Contract
# ============================================================================

def test_pagination_contract(spec: dict[str, Any]) -> None:
    """Validate pagination contract on list endpoints."""
    section("TEST-CONTRACT-004: Pagination Contract")

    paths = spec.get('paths', {})

    # Check specific paginated endpoint: GET /training/jobs
    training_jobs_path = paths.get('/training/jobs', {})
    get_method = training_jobs_path.get('get', {})

    check(
        "GET /training/jobs exists",
        bool(get_method),
        "Expected GET /training/jobs endpoint"
    )

    if get_method:
        parameters = get_method.get('parameters', [])
        param_names = [
            p.get('name') for p in parameters
            if isinstance(p, dict) and 'name' in p
        ]

        # Also check for $ref parameters
        for p in parameters:
            if isinstance(p, dict) and '$ref' in p:
                ref = p['$ref']
                if ref.startswith('#/components/parameters/'):
                    param_name = ref.split('/')[-1]
                    param_names.append(param_name)

        check(
            "Has cursor parameter",
            'cursor' in param_names or 'Cursor' in param_names,
            f"Parameters: {param_names}"
        )

        check(
            "Has limit parameter",
            'limit' in param_names or 'Limit' in param_names,
            f"Parameters: {param_names}"
        )

        # Check response schema
        responses = get_method.get('responses', {})
        success_response = responses.get('200', {})
        content = success_response.get('content', {})
        json_content = content.get('application/json', {})
        schema_ref = json_content.get('schema', {})

        check(
            "Response schema is defined",
            bool(schema_ref),
            f"Schema: {schema_ref}"
        )


# ============================================================================
# TEST-CONTRACT-005: Security Schemes
# ============================================================================

def test_security_schemes(spec: dict[str, Any]) -> None:
    """Validate security scheme definitions and coverage."""
    section("TEST-CONTRACT-005: Security Schemes")

    components = spec.get('components', {})
    security_schemes = components.get('securitySchemes', {})

    check(
        "BearerAuth is defined",
        'BearerAuth' in security_schemes,
        "Expected JWT bearer authentication"
    )

    check(
        "ApiKeyAuth is defined",
        'ApiKeyAuth' in security_schemes,
        "Expected API key authentication"
    )

    check(
        "OAuth2ClientCredentials is defined",
        'OAuth2ClientCredentials' in security_schemes,
        "Expected OAuth2 client credentials"
    )

    # Check that secured endpoints declare security
    paths = spec.get('paths', {})
    unsecured_non_health = []

    for path, methods in paths.items():
        if path == '/healthz':
            continue  # Health check should be unsecured

        for method, operation in methods.items():
            if method in ['get', 'post', 'put', 'patch', 'delete']:
                if isinstance(operation, dict):
                    security = operation.get('security', spec.get('security', []))
                    if not security:
                        unsecured_non_health.append(f"{method.upper()} {path}")

    check(
        "All non-health endpoints are secured",
        len(unsecured_non_health) == 0,
        f"Unsecured: {unsecured_non_health[:5]}" if unsecured_non_health else ""
    )


# ============================================================================
# TEST-CONTRACT-006: Webhook Signatures
# ============================================================================

def test_webhook_signatures(spec: dict[str, Any]) -> None:
    """Validate webhook signature requirements."""
    section("TEST-CONTRACT-006: Webhook Signatures")

    webhooks = spec.get('webhooks', {})

    check(
        "Webhooks section exists",
        bool(webhooks),
        f"Found {len(webhooks)} webhook definitions"
    )

    if webhooks:
        for webhook_name, webhook_spec in webhooks.items():
            post_spec = webhook_spec.get('post', {})
            parameters = post_spec.get('parameters', [])

            has_signature = False
            for param in parameters:
                if isinstance(param, dict):
                    if param.get('name') == 'X-Katopu-Signature':
                        has_signature = True
                        schema = param.get('schema', {})
                        pattern = schema.get('pattern', '')

                        check(
                            f"Webhook '{webhook_name}' has signature parameter",
                            True,
                            ""
                        )

                        check(
                            f"Webhook '{webhook_name}' signature uses sha256 pattern",
                            'sha256' in pattern.lower(),
                            f"Pattern: {pattern}"
                        )
                        break

            if not has_signature:
                check(
                    f"Webhook '{webhook_name}' has signature parameter",
                    False,
                    "Missing X-Katopu-Signature"
                )


# ============================================================================
# TEST-CONTRACT-007: Schema Strictness
# ============================================================================

def test_schema_strictness(spec: dict[str, Any]) -> None:
    """Validate that schemas use additionalProperties: false appropriately."""
    section("TEST-CONTRACT-007: Schema Strictness")

    components = spec.get('components', {})
    schemas = components.get('schemas', {})

    object_schemas = []
    strict_schemas = []

    for schema_name, schema_def in schemas.items():
        if isinstance(schema_def, dict):
            if schema_def.get('type') == 'object':
                object_schemas.append(schema_name)
                if schema_def.get('additionalProperties') is False:
                    strict_schemas.append(schema_name)

    check(
        f"Found {len(object_schemas)} object schemas",
        len(object_schemas) > 0,
        "Expected multiple object schemas"
    )

    strictness_ratio = len(strict_schemas) / len(object_schemas) if object_schemas else 0
    check(
        f"{len(strict_schemas)}/{len(object_schemas)} object schemas are strict (additionalProperties: false)",
        strictness_ratio > 0.7,  # At least 70% should be strict
        f"Strictness ratio: {strictness_ratio:.1%}"
    )


# ============================================================================
# TEST-CONTRACT-008: Standard Error Responses
# ============================================================================

def test_standard_error_responses(spec: dict[str, Any]) -> None:
    """Validate standard error response definitions."""
    section("TEST-CONTRACT-008: Standard Error Responses")

    components = spec.get('components', {})
    responses = components.get('responses', {})

    expected_errors = [
        'BadRequest',
        'Unauthorized',
        'Forbidden',
        'NotFound',
        'Conflict',
        'TooManyRequests',
        'InternalServerError'
    ]

    for error_name in expected_errors:
        check(
            f"{error_name} response is defined",
            error_name in responses,
            f"Missing #/components/responses/{error_name}"
        )

    # Check ErrorResponse schema
    schemas = components.get('schemas', {})
    check(
        "ErrorResponse schema is defined",
        'ErrorResponse' in schemas,
        "Expected standard error schema"
    )


# ============================================================================
# TEST-CONTRACT-009: Freeze/Plugin Endpoints
# ============================================================================

def test_freeze_plugin_endpoints(spec: dict[str, Any]) -> None:
    """Validate freeze snapshot and plugin registry endpoints."""
    section("TEST-CONTRACT-009: Freeze & Plugin Endpoints")

    paths = spec.get('paths', {})

    # Freeze endpoints
    freeze_endpoints = [
        '/circuits/{circuitId}/freeze',
        '/training/jobs/{trainingId}/freeze'
    ]

    for endpoint in freeze_endpoints:
        path_spec = paths.get(endpoint, {})
        check(
            f"Endpoint {endpoint} exists",
            bool(path_spec),
            ""
        )

        if path_spec:
            check(
                f"Endpoint {endpoint} has POST operation",
                'post' in path_spec,
                ""
            )
            check(
                f"Endpoint {endpoint} has GET operation",
                'get' in path_spec,
                ""
            )

    # Plugin endpoints
    plugin_endpoints = [
        '/plugins',
        '/plugins/{pluginId}',
        '/plugins/capabilities/{capability}',
        '/plugins/{pluginId}/verify'
    ]

    for endpoint in plugin_endpoints:
        check(
            f"Endpoint {endpoint} exists",
            endpoint in paths,
            ""
        )

    # Check schemas
    components = spec.get('components', {})
    schemas = components.get('schemas', {})

    freeze_schemas = ['FreezeHash', 'FreezeResponse']
    for schema_name in freeze_schemas:
        check(
            f"Schema {schema_name} is defined",
            schema_name in schemas,
            ""
        )

    plugin_schemas = ['Plugin', 'PluginCapability', 'PluginLifecycle']
    for schema_name in plugin_schemas:
        check(
            f"Schema {schema_name} is defined",
            schema_name in schemas,
            ""
        )


# ============================================================================
# Main Test Runner
# ============================================================================

def main() -> int:
    """Run all contract tests."""
    print("\n" + "=" * 70)
    print("  OpenAPI Contract Validation Test Suite")
    print("=" * 70)
    print(f"  Specification: {OPENAPI_PATH}")
    print("=" * 70)

    try:
        spec = load_openapi()
    except Exception as e:
        print(f"\nERROR: Failed to load OpenAPI specification: {e}")
        return 1

    # Run all tests
    test_openapi_metadata(spec)
    test_unique_operation_ids(spec)
    test_idempotency_key_coverage(spec)
    test_pagination_contract(spec)
    test_security_schemes(spec)
    test_webhook_signatures(spec)
    test_schema_strictness(spec)
    test_standard_error_responses(spec)
    test_freeze_plugin_endpoints(spec)

    # Summary
    print("\n" + "=" * 70)
    print(f"  Results: {_PASSED} passed, {_FAILED} failed")
    print("=" * 70)

    if _FAILED == 0:
        print("\n✓ ALL CONTRACT TESTS PASSED\n")
        return 0
    else:
        print(f"\n✗ {_FAILED} CONTRACT TEST(S) FAILED\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
