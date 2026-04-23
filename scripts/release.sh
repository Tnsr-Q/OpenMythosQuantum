#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") --version <X.Y.Z> [--dry-run]

Automates release tasks:
  - bump version in openapi/openapi.yaml
  - generate changelog entries from commits
  - create git tag
  - generate release artifacts in dist/
USAGE
}

VERSION=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "--version is required" >&2
  usage
  exit 1
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Version must match semantic version format: X.Y.Z" >&2
  exit 1
fi

TODAY="$(date -u +%Y-%m-%d)"
TAG="v${VERSION}"
LAST_TAG="$(git describe --tags --abbrev=0 2>/dev/null || true)"

if [[ -n "$LAST_TAG" ]]; then
  COMMIT_RANGE="${LAST_TAG}..HEAD"
else
  COMMIT_RANGE="HEAD"
fi

COMMITS="$(git log --pretty=format:'- %s (%h)' ${COMMIT_RANGE})"
if [[ -z "$COMMITS" ]]; then
  COMMITS="- No user-facing commits detected in ${COMMIT_RANGE}."
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] would update openapi/openapi.yaml version to ${VERSION}"
else
  python3 - <<PY
from pathlib import Path
import re

path = Path("openapi/openapi.yaml")
text = path.read_text(encoding="utf-8")
new_text, n = re.subn(r"(?m)^(  version:\s*)(\S+)\\s*$", rf"\\g<1>{VERSION}", text, count=1)
if n != 1:
    raise SystemExit("Unable to find info.version in openapi/openapi.yaml")
path.write_text(new_text, encoding="utf-8")
PY
fi

CHANGELOG="CHANGELOG.md"
RELEASE_HEADING="## [${VERSION}] - ${TODAY}"
if grep -qF "$RELEASE_HEADING" "$CHANGELOG"; then
  echo "Changelog already contains ${RELEASE_HEADING}; skipping changelog update"
else
  TEMP_FILE="$(mktemp)"
  {
    awk '1; /## \[Unreleased\]/{print "\n### Changed\n"}' "$CHANGELOG" | awk -v commits="$COMMITS" '
      BEGIN {printed=0}
      {
        print
        if (!printed && $0 ~ /^### Changed$/) {
          print commits
          printed=1
        }
      }
    ' > "$TEMP_FILE"

    {
      echo
      echo "$RELEASE_HEADING"
      echo
      echo "### Changed"
      echo "$COMMITS"
    } >> "$TEMP_FILE"

    mv "$TEMP_FILE" "$CHANGELOG"
  }
fi

mkdir -p dist
cp openapi/openapi.yaml "dist/openapi-${VERSION}.yaml"
sha256sum "dist/openapi-${VERSION}.yaml" > "dist/openapi-${VERSION}.yaml.sha256"
tar -czf "dist/release-${VERSION}.tar.gz" openapi/openapi.yaml docs CHANGELOG.md

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] would create tag ${TAG}"
else
  if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
    echo "Tag ${TAG} already exists; skipping tag creation"
  else
    git tag -a "$TAG" -m "Release ${TAG}"
    echo "Created tag ${TAG}"
  fi
fi

echo "Release automation complete for ${VERSION}."
