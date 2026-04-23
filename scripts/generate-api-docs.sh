#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_PATH="$ROOT_DIR/openapi/openapi.yaml"
OUT_PATH="$ROOT_DIR/docs/api-reference.html"

npx @redocly/cli build-docs "$SPEC_PATH" --output "$OUT_PATH"

echo "Generated API docs at $OUT_PATH"
