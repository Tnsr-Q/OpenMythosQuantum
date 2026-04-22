#!/usr/bin/env bash
set -euo pipefail

SPEC_PATH="${1:-openapi/openapi.yaml}"

if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required to run validation." >&2
  exit 1
fi

npx @redocly/cli lint "$SPEC_PATH"
npx swagger-cli validate "$SPEC_PATH"

echo "OpenAPI validation passed for: $SPEC_PATH"
