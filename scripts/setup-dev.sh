#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[setup-dev] Installing Python dev dependencies"
pip install -e .[dev]

echo "[setup-dev] Installing Node dependencies"
npm install

echo "[setup-dev] Running OpenAPI validation"
bash scripts/validate-openapi.sh

echo "[setup-dev] Running OpenAPI lint"
bash scripts/lint-openapi.sh

echo "[setup-dev] Setup complete"
