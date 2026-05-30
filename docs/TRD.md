# Technical Requirements Document

## Current Technical Scope

This repository is initialized for documentation, collaboration, and contract-first parallel delivery. The approved technical baseline is the tolerant REST contract in `contracts/openapi.yaml`, its split schemas in `contracts/schemas/`, and mock fixtures in `contracts/mocks/`.

No frontend runtime, backend runtime, database, queue, external API integration, authentication, authorization, or deployment path is approved yet.

## Technical Principles

- Keep implementation changes small, testable, and reversible.
- Prefer explicit boundaries between source connectors, classification, review workflow, audit logging, and presentation.
- Inject external collaborators into core logic instead of constructing them inside core modules.
- Keep side effects at boundary layers.
- Use behavior tests for user-observable contracts.
- Keep frontend and backend aligned through `OpenAPI-first + mock-first + vertical-slice-first`.
- Treat unknown fields and enum-like values as forward-compatible.

## Future Boundary Candidates

These are not approved implementation modules yet. They are candidate boundaries to evaluate before coding:

- Source connector boundary.
- Document extraction boundary.
- Finding classification boundary.
- Risk scoring boundary.
- Owner resolution boundary.
- Human review workflow boundary.
- Audit event boundary.
- Delta scan boundary.
- Evaluation harness boundary.
- Admin metrics boundary.
- Governance configuration boundary.
- Permission boundary boundary.
- Review support boundary.

## Contract Baseline

- Base path: `/api`.
- Envelope: `data`, `meta`, and optional `pagination`.
- Error format: `application/problem+json`.
- State machines: scan, finding review, and contract lifecycle are documented in `docs/API_CONTRACT.md` and `docs/design/frontend-backend-delivery-contract.md`.
- Mocks are contract fixtures, not production seed data.
- Governance configuration is documented in `docs/GOVERNANCE_CONFIG.md`.
- Adaptive policy and review state machines are documented in `docs/design/adaptive-governance-review-control.md`.

## External Research Required Before Implementation

Official or authoritative documentation must be reviewed before integrating:

- Microsoft Graph or any file-source API.
- GDPR deletion, retention, or audit-related workflow assumptions.
- The organizer sample repository before downloading or vendoring sample files.
- Any AI, OCR, document parsing, or classification dependency.
- Any storage, authentication, authorization, or deployment platform.

## Technical Done When

The first implementation task has:

- A narrow acceptance criterion.
- A documented impact surface.
- A state machine if it introduces workflow, permissions, asynchronous work, or external protocols.
- Targeted validation commands.
