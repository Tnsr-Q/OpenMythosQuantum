# API Endpoint Deprecation Policy

This document defines how API endpoints are deprecated and removed.

## Goals

- Give integrators clear and predictable migration windows.
- Prevent surprise removals.
- Align deprecations with semantic versioning and release notes.

## Deprecation Lifecycle

1. **Announcement phase**
   - Endpoint is marked deprecated in OpenAPI using `deprecated: true`.
   - Changelog and release notes include migration guidance.
   - A replacement endpoint is documented when applicable.
2. **Grace period**
   - Deprecated endpoint remains functional for at least one MINOR release.
   - Response headers should include:
     - `Deprecation: true`
     - `Sunset: <RFC 7231 date>`
     - `Link: <migration guide URL>; rel="deprecation"`
3. **Removal phase**
   - Endpoint is removed only in a MAJOR release.
   - Removal is recorded in `CHANGELOG.md` under a **Removed** section.

## Timeline Standards

- Minimum grace period: **90 days** from announcement.
- High-impact endpoints (auth, training, webhooks): target **180 days** when feasible.

## Required Documentation

Every deprecation must include:

- impacted endpoint(s)
- replacement endpoint(s)
- migration steps
- final sunset date
- owner/contact for migration support

## Exceptions

Security emergencies may require accelerated deprecation/removal. In that case:

- document the risk and rationale in release notes
- provide mitigation and migration guidance
- communicate customer-impact window explicitly
