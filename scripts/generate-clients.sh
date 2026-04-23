#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_PATH="$ROOT_DIR/openapi/openapi.yaml"
PYTHON_OUT="$ROOT_DIR/generated/python-client"
TS_OUT="$ROOT_DIR/generated/typescript-client"

if ! command -v openapi-generator-cli >/dev/null 2>&1; then
  echo "error: openapi-generator-cli is required. Install with npm i -g @openapitools/openapi-generator-cli" >&2
  exit 1
fi

mkdir -p "$ROOT_DIR/generated"

openapi-generator-cli generate \
  -i "$SPEC_PATH" \
  -g python \
  -o "$PYTHON_OUT" \
  --additional-properties=packageName=katopu_client

openapi-generator-cli generate \
  -i "$SPEC_PATH" \
  -g typescript-axios \
  -o "$TS_OUT"

echo "Generated clients:"
echo "  - $PYTHON_OUT"
echo "  - $TS_OUT"
