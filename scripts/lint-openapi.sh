#!/usr/bin/env bash
set -euo pipefail

SPEC_PATH="${1:-openapi/openapi.yaml}"

npx @redocly/cli lint "$SPEC_PATH"
