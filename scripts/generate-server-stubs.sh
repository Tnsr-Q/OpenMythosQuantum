#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_PATH="$ROOT_DIR/openapi/openapi.yaml"
PYTHON_OUT="$ROOT_DIR/generated/server-stubs/python-fastapi"
NODE_OUT="$ROOT_DIR/generated/server-stubs/nodejs-express"

if ! command -v openapi-generator-cli >/dev/null 2>&1; then
  echo "error: openapi-generator-cli is required. Install with npm i -g @openapitools/openapi-generator-cli" >&2
  exit 1
fi

mkdir -p "$ROOT_DIR/generated/server-stubs"

openapi-generator-cli generate \
  -i "$SPEC_PATH" \
  -g python-fastapi \
  -o "$PYTHON_OUT"

openapi-generator-cli generate \
  -i "$SPEC_PATH" \
  -g nodejs-express-server \
  -o "$NODE_OUT"

echo "Generated server stubs:"
echo "  - $PYTHON_OUT"
echo "  - $NODE_OUT"
