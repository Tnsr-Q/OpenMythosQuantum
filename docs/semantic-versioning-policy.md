# Semantic Versioning Policy

This repository follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) for the API contract and release artifacts.

## Versioning Scope

The canonical version source of truth is `info.version` in `openapi/openapi.yaml`.

## Version Rules

- **MAJOR** (`X.0.0`): incompatible API changes.
  - Examples: removing an endpoint, changing required request fields, changing response shape in a breaking way.
- **MINOR** (`1.X.0`): backward-compatible feature additions.
  - Examples: new endpoints, optional fields, new enum values when clients are documented to ignore unknown values.
- **PATCH** (`1.4.X`): backward-compatible fixes/documentation improvements.
  - Examples: typo fixes, clarification of constraints, fixing invalid examples that do not change runtime contract behavior.

## Release Requirements

1. Update `openapi/openapi.yaml` `info.version`.
2. Add a `CHANGELOG.md` entry for the release.
3. Run contract validation and tests.
4. Tag the release as `v<version>`.
5. Publish release artifacts (OpenAPI spec snapshot + checksums).

## Compatibility Commitments

- Breaking changes only land in MAJOR releases.
- MINOR and PATCH releases must remain backward-compatible.
- Deprecated endpoints remain available for at least one MINOR release cycle before removal, per `docs/api-deprecation-policy.md`.
